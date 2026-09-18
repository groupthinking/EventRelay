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
        body: JSON.stringify({ url: 'https://www.youtube.com/watch?v=auJzb1D-fag' }),
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
        body: JSON.stringify({ url: 'https://www.youtube.com/watch?v=auJzb1D-fag' }),
      }),
    );
    const json = (await res.json()) as Record<string, unknown>;

    expect(res.status).toBe(500);
    expect(json.code).toBeUndefined();
    expect(String(json.hint)).toMatch(/withWorkflow/);
    expect(json.cause).toBeUndefined();
  });

  it('forwards Analyze transcript and events so Act stays on the same run', async () => {
    start.mockResolvedValue({ runId: 'wrun_same' });
    vi.resetModules();
    const { POST } = await import('../route');
    const transcript = 'x'.repeat(50);
    const res = await POST(
      new Request('https://uvai.io/api/workflows/video-to-actions', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({
          url: 'https://www.youtube.com/watch?v=auJzb1D-fag',
          videoTitle: 'Fixture',
          transcript,
          events: [{ type: 'action', title: 'Ship', description: 'now' }],
        }),
      }),
    );
    const json = (await res.json()) as Record<string, unknown>;
    expect(res.status).toBe(200);
    expect(json.ok).toBe(true);
    expect(json.runId).toBe('wrun_same');
    expect(start).toHaveBeenCalledWith(
      expect.anything(),
      [
        expect.objectContaining({
          url: 'https://www.youtube.com/watch?v=auJzb1D-fag',
          videoTitle: 'Fixture',
          transcript,
          events: [{ type: 'action', title: 'Ship', description: 'now' }],
        }),
      ],
    );
  });

  it('does not forward a short transcript as same-run input', async () => {
    start.mockResolvedValue({ runId: 'wrun_short' });
    vi.resetModules();
    const { POST } = await import('../route');
    const res = await POST(
      new Request('https://uvai.io/api/workflows/video-to-actions', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({
          url: 'https://www.youtube.com/watch?v=auJzb1D-fag',
          transcript: 'too short',
        }),
      }),
    );
    expect(res.status).toBe(200);
    const args = start.mock.calls[0]?.[1] as Array<Record<string, unknown>>;
    expect(args[0]?.url).toContain('auJzb1D-fag');
    expect(args[0]?.transcript).toBeUndefined();
    expect(args[0]?.events).toBeUndefined();
  });
});
