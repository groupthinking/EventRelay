import { describe, it, expect, afterEach, vi } from 'vitest';
import { ApiClient } from '@/lib/api-client';

function jsonResponse(
  data: unknown,
  ok = true,
  status = 200,
  statusText = 'OK',
): Response {
  return {
    ok,
    status,
    statusText,
    json: async () => data,
  } as unknown as Response;
}

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
  vi.useRealTimers();
});

describe('ApiClient', () => {
  it('returns the parsed body on a successful GET', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        jsonResponse({ status: 'success', data: { hello: 'world' }, timestamp: 't', request_id: 'r' }),
      ),
    );
    const client = new ApiClient('http://backend');
    const res = await client.get<{ hello: string }>('/thing');
    expect(res.status).toBe('success');
    expect(res.data).toEqual({ hello: 'world' });
  });

  it('maps a non-ok response to a structured error using the body detail', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(jsonResponse({ detail: 'nope' }, false, 422, 'Unprocessable')),
    );
    const client = new ApiClient('http://backend');
    const res = await client.get('/thing');
    expect(res.status).toBe('error');
    expect(res.error).toBe('nope');
    expect(res.detail).toBe('nope');
  });

  it('falls back to statusText when an error body is not JSON', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: false,
        status: 500,
        statusText: 'Server Error',
        json: async () => {
          throw new Error('not json');
        },
      } as unknown as Response),
    );
    const client = new ApiClient('http://backend');
    const res = await client.get('/thing');
    expect(res.status).toBe('error');
    expect(res.error).toBe('Server Error');
  });

  it('does not retry and returns an error when maxRetries is 0', async () => {
    const fetchMock = vi.fn().mockRejectedValue(new TypeError('network down'));
    vi.stubGlobal('fetch', fetchMock);
    const client = new ApiClient('http://backend', 0);
    const res = await client.get('/thing');
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(res.status).toBe('error');
    expect(res.error).toBe('network down');
  });

  it('retries after a network error and then succeeds', async () => {
    vi.useFakeTimers();
    const fetchMock = vi
      .fn()
      .mockRejectedValueOnce(new TypeError('flaky'))
      .mockResolvedValueOnce(
        jsonResponse({ status: 'success', data: { ok: true }, timestamp: 't', request_id: 'r' }),
      );
    vi.stubGlobal('fetch', fetchMock);

    const client = new ApiClient('http://backend'); // default maxRetries = 2
    const promise = client.post('/thing', { a: 1 });
    await vi.runAllTimersAsync();
    const res = await promise;

    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(res.status).toBe('success');
  });
});
