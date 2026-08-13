import { afterEach, describe, expect, it, vi } from 'vitest';

vi.mock('server-only', () => ({}));

vi.mock('@/lib/pipeline-backend-health', () => ({
  checkBackendHealth: vi.fn(),
  getBackendConfig: vi.fn(),
}));

import { checkBackendHealth, getBackendConfig } from '@/lib/pipeline-backend-health';
import {
  fetchAsyncVideoJob,
  isTerminalJobStatus,
  kickoffAsyncVideoJob,
} from '@/lib/pipeline-async-job';

describe('pipeline-async-job (WDK C)', () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it('returns a handoff when the backend is unavailable', async () => {
    vi.mocked(checkBackendHealth).mockResolvedValue({
      configured: false,
      available: false,
      host: null,
      reason: 'BACKEND_URL is not configured',
    });
    const kicked = await kickoffAsyncVideoJob('https://www.youtube.com/watch?v=auJzb1D-fag');
    expect(kicked.kind).toBe('handoff');
    expect(kicked.message).toMatch(/BACKEND_URL/);
  });

  it('parses job_id from FastAPI videos/process', async () => {
    vi.mocked(checkBackendHealth).mockResolvedValue({
      configured: true,
      available: true,
      host: 'api.example',
    });
    vi.mocked(getBackendConfig).mockReturnValue({
      configured: true,
      url: 'https://api.example',
    });
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        status: 202,
        json: async () => ({ data: { job_id: 'job_1' } }),
      }),
    );

    const kicked = await kickoffAsyncVideoJob('https://www.youtube.com/watch?v=auJzb1D-fag');
    expect(kicked).toEqual({
      kind: 'job',
      jobId: 'job_1',
      statusUrl: '/api/jobs/job_1',
    });
  });

  it('reads live_url from job status', async () => {
    vi.mocked(getBackendConfig).mockReturnValue({
      configured: true,
      url: 'https://api.example',
    });
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => ({
          data: { status: 'completed', live_url: 'https://app.vercel.app' },
        }),
      }),
    );
    const status = await fetchAsyncVideoJob('job_1');
    expect(status.jobStatus).toBe('completed');
    expect(status.live_url).toBe('https://app.vercel.app');
    expect(isTerminalJobStatus(status.jobStatus)).toBe(true);
  });

  it('does not treat pending as terminal', () => {
    expect(isTerminalJobStatus('pending')).toBe(false);
    expect(isTerminalJobStatus('running')).toBe(false);
  });

  it('treats a backend HTTP error as failed, not a config handoff', async () => {
    vi.mocked(checkBackendHealth).mockResolvedValue({
      configured: true,
      available: true,
      host: 'api.example',
    });
    vi.mocked(getBackendConfig).mockReturnValue({
      configured: true,
      url: 'https://api.example',
    });
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: false,
        status: 503,
        json: async () => ({ error: 'backend overloaded' }),
      }),
    );
    const kicked = await kickoffAsyncVideoJob(
      'https://www.youtube.com/watch?v=auJzb1D-fag',
    );
    expect(kicked.kind).toBe('failed');
    expect(kicked.message).toMatch(/overloaded|503/);
  });

  it('marks a non-ok job status read as not ok', async () => {
    vi.mocked(getBackendConfig).mockReturnValue({
      configured: true,
      url: 'https://api.example',
    });
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: false,
        status: 404,
        json: async () => ({ error: 'unknown job' }),
      }),
    );
    const status = await fetchAsyncVideoJob('job_missing');
    expect(status.ok).toBe(false);
    expect(status.httpStatus).toBe(404);
    expect(isTerminalJobStatus(status.jobStatus)).toBe(false);
  });
});
