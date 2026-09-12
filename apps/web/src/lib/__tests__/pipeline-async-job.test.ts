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

  it('reads live_url nested in job metadata without inventing one', async () => {
    vi.mocked(getBackendConfig).mockReturnValue({
      configured: true,
      url: 'https://api.uvai.io',
    });
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => ({
          data: {
            status: 'completed',
            metadata: { live_url: 'https://shipped.example.app' },
          },
        }),
      }),
    );
    const status = await fetchAsyncVideoJob('job_nested');
    expect(status.live_url).toBe('https://shipped.example.app');
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

  it('treats backend JobStatus.complete as terminal (not only completed)', () => {
    expect(isTerminalJobStatus('complete')).toBe(true);
    expect(isTerminalJobStatus('completed')).toBe(true);
  });

  it('reads live_url from job.metadata.outputs.deployment without inventing one', async () => {
    vi.mocked(getBackendConfig).mockReturnValue({
      configured: true,
      url: 'https://api.uvai.io',
    });
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => ({
          data: {
            status: 'complete',
            metadata: {
              outputs: { deployment: { live_url: 'https://ship.example.app' } },
            },
          },
        }),
      }),
    );
    const status = await fetchAsyncVideoJob('job_complete');
    expect(status.jobStatus).toBe('complete');
    expect(isTerminalJobStatus(status.jobStatus)).toBe(true);
    expect(status.live_url).toBe('https://ship.example.app');
  });

  it('surfaces backend job.error as the status message', async () => {
    vi.mocked(getBackendConfig).mockReturnValue({
      configured: true,
      url: 'https://api.uvai.io',
    });
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => ({
          data: { status: 'failed', error: 'Transcript-action workflow failed' },
        }),
      }),
    );
    const status = await fetchAsyncVideoJob('job_err');
    expect(status.jobStatus).toBe('failed');
    expect(status.message).toBe('Transcript-action workflow failed');
  });

  it('passes through a video-to-software live_url from kickoff', async () => {
    vi.mocked(checkBackendHealth).mockResolvedValue({
      configured: true,
      available: true,
      host: 'api.uvai.io',
    });
    vi.mocked(getBackendConfig).mockReturnValue({
      configured: true,
      url: 'https://api.uvai.io',
    });
    const fetchMock = vi.fn().mockImplementation(async (input: unknown) => {
      const href = String(input);
      if (href.includes('/video-to-software')) {
        return {
          ok: true,
          status: 200,
          json: async () => ({ live_url: 'https://xy.vercel.app' }),
        };
      }
      throw new Error(`unexpected fetch ${href}`);
    });
    vi.stubGlobal('fetch', fetchMock);
    const kicked = await kickoffAsyncVideoJob(
      'https://www.youtube.com/watch?v=auJzb1D-fag',
    );
    expect(kicked.kind).toBe('live');
    expect(kicked.live_url).toBe('https://xy.vercel.app');
    expect(fetchMock).toHaveBeenCalledWith(
      'https://api.uvai.io/api/v1/video-to-software',
      expect.objectContaining({ method: 'POST' }),
    );
  });

  it('falls through to videos/process when video-to-software is 401 (not an auth cut)', async () => {
    vi.mocked(checkBackendHealth).mockResolvedValue({
      configured: true,
      available: true,
      host: 'api.uvai.io',
    });
    vi.mocked(getBackendConfig).mockReturnValue({
      configured: true,
      url: 'https://api.uvai.io',
    });
    const fetchMock = vi.fn().mockImplementation(async (input: unknown) => {
      const href = String(input);
      if (href.includes('/video-to-software')) {
        return {
          ok: false,
          status: 401,
          json: async () => ({ error: 'Authentication required' }),
        };
      }
      return {
        ok: true,
        status: 202,
        json: async () => ({ data: { job_id: 'job_after_401' } }),
      };
    });
    vi.stubGlobal('fetch', fetchMock);
    const kicked = await kickoffAsyncVideoJob(
      'https://www.youtube.com/watch?v=auJzb1D-fag',
    );
    expect(kicked.kind).toBe('job');
    expect(kicked.jobId).toBe('job_after_401');
    expect(kicked.message ?? '').not.toMatch(/Authentication required/);
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
