import { beforeEach, describe, expect, it, vi } from 'vitest';

const start = vi.fn();

vi.mock('workflow/api', () => ({
  start: (...args: unknown[]) => start(...args),
}));

vi.mock('@/workflows/studio-deploy', () => ({
  studioDeployWorkflow: async () => ({}),
}));

describe('POST /api/workflows/studio-deploy', () => {
  beforeEach(() => {
    start.mockReset();
  });

  it('rejects a missing url', async () => {
    const { POST } = await import('../route');
    const res = await POST(
      new Request('https://uvai.io/api/workflows/studio-deploy', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({}),
      }),
    );
    expect(res.status).toBe(400);
    expect(start).not.toHaveBeenCalled();
  });

  it('rejects a localhost url', async () => {
    const { POST } = await import('../route');
    const res = await POST(
      new Request('https://uvai.io/api/workflows/studio-deploy', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ url: 'http://127.0.0.1:3000/steal' }),
      }),
    );
    expect(res.status).toBe(400);
    expect(start).not.toHaveBeenCalled();
  });

  it('returns runId when start() succeeds', async () => {
    start.mockResolvedValue({ runId: 'wrun_c1' });
    const { POST } = await import('../route');
    const res = await POST(
      new Request('https://uvai.io/api/workflows/studio-deploy', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ url: 'https://www.youtube.com/watch?v=dQw4w9WgXcQ' }),
      }),
    );
    const json = (await res.json()) as Record<string, unknown>;
    expect(res.status).toBe(200);
    expect(json.ok).toBe(true);
    expect(json.runId).toBe('wrun_c1');
    expect(String(json.statusUrl)).toContain('wrun_c1');
  });
});
