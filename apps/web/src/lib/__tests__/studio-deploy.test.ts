import { afterEach, describe, expect, it, vi } from 'vitest';
import { kickoffStudioDeploy, pollStudioJob } from '@/lib/studio-deploy';

describe('studio-deploy (F5)', () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it('kickoffStudioDeploy parses job_id from pipeline response', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        status: 202,
        json: async () => ({
          job_id: 'job_abc',
          status_url: '/api/jobs/job_abc',
          pipeline: 'backend-async',
        }),
      }),
    );

    const result = await kickoffStudioDeploy({ url: 'https://www.youtube.com/watch?v=dQw4w9WgXcQ' });
    expect(result.ok).toBe(true);
    expect(result.jobId).toBe('job_abc');
    expect(result.statusUrl).toBe('/api/jobs/job_abc');
    expect(result.handoff).toBe(false);
    expect(fetch).toHaveBeenCalledWith(
      '/api/pipeline',
      expect.objectContaining({ method: 'POST' }),
    );
  });

  it('kickoffStudioDeploy marks handoff when no job and not ok', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: false,
        status: 503,
        json: async () => ({ error: 'BACKEND_URL not configured' }),
      }),
    );

    const result = await kickoffStudioDeploy({ url: 'https://www.youtube.com/watch?v=dQw4w9WgXcQ' });
    expect(result.ok).toBe(false);
    expect(result.handoff).toBe(true);
    expect(result.message).toContain('BACKEND_URL');
  });

  it('pollStudioJob returns live_url when job completes', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => ({
          status: 'completed',
          data: { status: 'completed', live_url: 'https://example.vercel.app' },
        }),
      }),
    );

    const polled = await pollStudioJob('job_1', { attempts: 1, delayMs: 0 });
    expect(polled.ok).toBe(true);
    expect(polled.live_url).toBe('https://example.vercel.app');
    expect(polled.jobStatus).toBe('completed');
  });
});
