import { beforeEach, describe, expect, it, vi } from 'vitest';

const start = vi.fn();

vi.mock('workflow/api', () => ({
  start: (...args: unknown[]) => start(...args),
}));

vi.mock('@/workflows/video-to-actions', () => ({
  videoToActionsWorkflow: async () => ({}),
}));

describe('POST /api/workflows/video-to-actions error body', () => {
  beforeEach(() => {
    start.mockReset();
  });

  it('returns 500 with WORKFLOW_UNDICI_DISPATCH_CONFLICT and no leaked cause', async () => {
    const err = new Error('fetch failed');
    err.cause = new Error(
      'Cannot read private member #P from an object whose class did not declare it',
    );
    start.mockRejectedValue(err);

    const { POST } = await import('../route');
    const res = await POST(
      new Request('https://uvai.io/api/workflows/video-to-actions', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ url: 'https://www.youtube.com/watch?v=dQw4w9WgXcQ' }),
      }),
    );
    const json = (await res.json()) as Record<string, unknown>;

    expect(res.status).toBe(500);
    expect(json.ok).toBe(false);
    expect(json.error).toBe('fetch failed');
    expect(json.code).toBe('WORKFLOW_UNDICI_DISPATCH_CONFLICT');
    expect(json.cause).toBeUndefined();
  });

  it('returns 500 with the generic withWorkflow hint for other start() errors', async () => {
    start.mockRejectedValue(new Error('world not configured'));
    vi.resetModules();
    const { POST } = await import('../route');
    const res = await POST(
      new Request('https://uvai.io/api/workflows/video-to-actions', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ url: 'https://www.youtube.com/watch?v=dQw4w9WgXcQ' }),
      }),
    );
    const json = (await res.json()) as Record<string, unknown>;

    expect(res.status).toBe(500);
    expect(json.code).toBeUndefined();
    expect(String(json.hint)).toMatch(/withWorkflow/);
    expect(json.cause).toBeUndefined();
  });
});
