import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

/**
 * SSRF gate on `POST /api/workflows/video-to-actions`.
 *
 * The route originally inlined its own hostname list. That list enumerated
 * `localhost`, `127.0.0.1`, `0.0.0.0`, `::1`, `.local` and `.internal` — so it
 * allowed every RFC1918 literal, 169.254.169.254, and (because `URL.hostname`
 * keeps the brackets on an IPv6 literal) `http://[::1]/` as well, since
 * `'[::1]' === '::1'` is false. These cases pin the delegation to the shared
 * guard, which is what closes all of them at once.
 *
 * `start` is mocked so a reachable URL does not require a workflow world; the
 * assertion that matters is whether the guard ran *before* it.
 */

const { lookup } = vi.hoisted(() => ({ lookup: vi.fn() }));
vi.mock('node:dns/promises', () => ({ lookup }));

const { start } = vi.hoisted(() => ({ start: vi.fn() }));
vi.mock('workflow/api', () => ({ start, getRun: vi.fn() }));

vi.mock('@/workflows/video-to-actions', () => ({ videoToActionsWorkflow: () => undefined }));

import { POST } from '@/app/api/workflows/video-to-actions/route';

function post(url: unknown): Request {
  return new Request('http://test.local/api/workflows/video-to-actions', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ url }),
  });
}

let errorSpy: ReturnType<typeof vi.spyOn>;

beforeEach(() => {
  lookup.mockReset();
  start.mockReset();
  start.mockResolvedValue({ runId: 'wrun_test' });
  errorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
});

afterEach(() => {
  errorSpy.mockRestore();
});

describe('POST /api/workflows/video-to-actions — SSRF gate', () => {
  it.each([
    ['http://169.254.169.254/', 'cloud metadata'],
    ['http://10.0.0.1/', 'RFC1918 10/8'],
    ['http://192.168.1.1/', 'RFC1918 192.168/16'],
    ['http://172.16.31.9/', 'RFC1918 172.16/12'],
    ['http://[::1]/', 'bracketed IPv6 loopback'],
    ['http://[0:0:0:0:0:ffff:7f00:1]/', 'IPv4-mapped IPv6 loopback'],
    ['http://[64:ff9b::a9fe:a9fe]/', 'NAT64-encoded cloud metadata'],
    ['http://127.0.0.1/', 'IPv4 loopback'],
    ['http://localhost/', 'blocked hostname'],
  ])('rejects %s (%s) without starting a run', async (url) => {
    const res = await POST(post(url));

    expect(res.status).toBe(400);
    // The run must not start: a rejected target that still kicked off a durable
    // workflow would only move the fetch somewhere harder to see.
    expect(start).not.toHaveBeenCalled();
    // Every literal above is decided from the caller's own input, so none of
    // them should reach the resolver either.
    expect(lookup).not.toHaveBeenCalled();
  });

  it('rejects a hostname that resolves to a private address', async () => {
    lookup.mockResolvedValueOnce([{ address: '10.0.0.5', family: 4 }]);

    const res = await POST(post('https://sneaky.example.com/'));

    expect(res.status).toBe(400);
    expect(start).not.toHaveBeenCalled();
    expect(lookup).toHaveBeenCalledWith('sneaky.example.com', { all: true });
  });

  it('does not tell the caller why the host was refused', async () => {
    // The load-bearing assertion is indistinguishability: "does not resolve"
    // and "resolves to a private address" must read identically to the caller,
    // or the endpoint is a DNS oracle for internal names (CWE-209, #1381).
    lookup.mockRejectedValueOnce(
      Object.assign(new Error('getaddrinfo ENOTFOUND vault.corp.example'), {
        code: 'ENOTFOUND',
      })
    );
    const missing = await (await POST(post('https://vault.corp.example/'))).json();

    lookup.mockResolvedValueOnce([{ address: '10.1.2.3', family: 4 }]);
    const private_ = await (await POST(post('https://vault.corp.example/'))).json();

    expect(missing).toEqual(private_);
    expect(JSON.stringify(missing)).not.toContain('vault.corp.example');
    expect(JSON.stringify(missing)).not.toContain('ENOTFOUND');
    expect(JSON.stringify(private_)).not.toContain('10.1.2.3');
  });

  it('starts the run for a host that resolves publicly', async () => {
    // The control. Without it, every test above would pass just as well if the
    // route rejected unconditionally.
    lookup.mockResolvedValueOnce([{ address: '93.184.216.34', family: 4 }]);

    const res = await POST(post('https://www.youtube.com/watch?v=dQw4w9WgXcQ'));
    const body = await res.json();

    expect(res.status).toBe(200);
    expect(body.ok).toBe(true);
    expect(body.runId).toBe('wrun_test');
    expect(start).toHaveBeenCalledTimes(1);
  });
});
