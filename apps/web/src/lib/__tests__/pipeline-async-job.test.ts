import { afterEach, describe, expect, it, vi } from 'vitest';

vi.mock('server-only', () => ({}));

vi.mock('@/lib/pipeline-backend-health', () => ({
  checkBackendHealth: vi.fn(),
  getBackendConfig: vi.fn(),
}));

import { checkBackendHealth, getBackendConfig } from '@/lib/pipeline-backend-health';
import {
  decideStudioDeployPoll,
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
      expect.objectContaining({
        method: 'POST',
        signal: expect.any(AbortSignal),
      }),
    );
  });

  it('hands off to an async deploy job when video-to-software times out (no HTTP 524 HOLD)', async () => {
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
        throw Object.assign(new Error('The operation was aborted due to timeout'), {
          name: 'TimeoutError',
        });
      }
      if (href.includes('/videos/process')) {
        return {
          ok: true,
          status: 202,
          json: async () => ({ data: { job_id: 'job_after_timeout' } }),
        };
      }
      throw new Error(`unexpected fetch ${href}`);
    });
    vi.stubGlobal('fetch', fetchMock);
    const kicked = await kickoffAsyncVideoJob(
      'https://www.youtube.com/watch?v=XYMcBrFSJ4c',
    );
    expect(kicked.kind).toBe('job');
    expect(kicked.jobId).toBe('job_after_timeout');
    expect(kicked.message ?? '').not.toMatch(/HTTP 524/);
    const processInit = fetchMock.mock.calls.find(([input]) =>
      String(input).includes('/videos/process'),
    )?.[1] as { body?: string };
    expect(String(processInit.body)).toMatch(/video-to-software/);
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

  const READY_TRANSCRIPT =
    'Studio Video Pack for XYMcBrFSJ4c already has a usable transcript ready for deploy.';

  it('does not start videos/process when a ready transcript exists and vts is 401', async () => {
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
      if (href.includes('/videos/process')) {
        throw new Error('must not re-hit YouTube via videos/process');
      }
      if (href.includes('/video-to-software')) {
        return {
          ok: false,
          status: 401,
          json: async () => ({ error: 'Authentication required' }),
        };
      }
      throw new Error(`unexpected fetch ${href}`);
    });
    vi.stubGlobal('fetch', fetchMock);
    const kicked = await kickoffAsyncVideoJob(
      'https://www.youtube.com/watch?v=XYMcBrFSJ4c',
      { transcript: READY_TRANSCRIPT },
    );
    expect(kicked.kind).toBe('failed');
    expect(kicked.jobId).toBeUndefined();
    expect(kicked.message ?? '').toMatch(/401|Authentication required/i);
    expect(kicked.message ?? '').not.toMatch(/Sign in to confirm you’re not a bot/i);
    expect(kicked.message ?? '').not.toMatch(/UNKNOWN checks are not a live URL/i);
    expect(kicked.message ?? '').not.toMatch(/Failed to read workflow run/i);
    expect(kicked.message ?? '').not.toMatch(/Failed to read workflow return value/i);
    expect(kicked.message ?? '').not.toMatch(/BACKEND_URL is not configured/i);
    expect(fetchMock).toHaveBeenCalledTimes(1);
    const vtsInit = fetchMock.mock.calls[0]?.[1] as { body?: string };
    expect(String(vtsInit.body)).toContain(READY_TRANSCRIPT);
  });

  it('does not surface a YouTube bot HOLD when vts re-hits YouTube despite a ready transcript', async () => {
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
      if (href.includes('/videos/process')) {
        throw new Error('must not re-hit YouTube via videos/process');
      }
      return {
        ok: false,
        status: 500,
        json: async () => ({
          error:
            'ERROR: [youtube] XYMcBrFSJ4c: Sign in to confirm you’re not a bot. Use --cookies-from-browser or --cookies for the authentication.',
        }),
      };
    });
    vi.stubGlobal('fetch', fetchMock);
    const kicked = await kickoffAsyncVideoJob(
      'https://www.youtube.com/watch?v=XYMcBrFSJ4c',
      { transcript: READY_TRANSCRIPT },
    );
    expect(kicked.kind).toBe('failed');
    expect(kicked.message ?? '').not.toMatch(/Sign in to confirm you’re not a bot/i);
    expect(kicked.message ?? '').not.toMatch(/cookies-from-browser/i);
    expect(kicked.message ?? '').toMatch(/ready transcript|must not re-fetch YouTube|no verified deploy receipt/i);
    expect(fetchMock.mock.calls.some(([input]) => String(input).includes('/videos/process'))).toBe(
      false,
    );
  });

  it('uses an origin 202 job_id from video-to-software (no HTTP 524 HOLD)', async () => {
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
      if (href.includes('/videos/process')) {
        throw new Error('must use the origin 202 job_id, not a second process job');
      }
      if (href.includes('/video-to-software')) {
        return {
          ok: true,
          status: 202,
          json: async () => ({
            status: 'success',
            data: { job_id: 'job_01M2AE6Z9Q2KZRBA0Z0Q455B0S' },
          }),
        };
      }
      throw new Error(`unexpected fetch ${href}`);
    });
    vi.stubGlobal('fetch', fetchMock);
    const kicked = await kickoffAsyncVideoJob(
      'https://www.youtube.com/watch?v=XYMcBrFSJ4c',
      { transcript: READY_TRANSCRIPT },
    );
    expect(kicked.kind).toBe('job');
    expect(kicked.jobId).toBe('job_01M2AE6Z9Q2KZRBA0Z0Q455B0S');
    expect(kicked.message ?? '').not.toMatch(/HTTP 524/);
    expect(kicked.message ?? '').not.toMatch(/Sign in to confirm you’re not a bot/i);
    expect(kicked.message ?? '').not.toMatch(/BACKEND_URL is not configured/i);
    expect(fetchMock.mock.calls.some(([input]) => String(input).includes('/videos/process'))).toBe(
      false,
    );
  });

  it('does not start videos/process on HTTP 524 when a ready transcript exists', async () => {
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
      if (href.includes('/videos/process')) {
        throw new Error('must not re-hit YouTube via videos/process');
      }
      if (href.includes('/video-to-software')) {
        return {
          ok: false,
          status: 524,
          json: async () => ({ error: 'error code: 524' }),
        };
      }
      throw new Error(`unexpected fetch ${href}`);
    });
    vi.stubGlobal('fetch', fetchMock);
    const kicked = await kickoffAsyncVideoJob(
      'https://www.youtube.com/watch?v=XYMcBrFSJ4c',
      { transcript: READY_TRANSCRIPT },
    );
    expect(kicked.kind).toBe('failed');
    expect(kicked.jobId).toBeUndefined();
    expect(kicked.message ?? '').toMatch(/ready transcript|must not re-fetch YouTube|no verified deploy receipt/i);
    expect(kicked.message ?? '').not.toMatch(/HTTP 524/);
    expect(kicked.message ?? '').not.toMatch(/Sign in to confirm you’re not a bot/i);
    expect(kicked.message ?? '').not.toMatch(/UNKNOWN checks are not a live URL/i);
    expect(kicked.message ?? '').not.toMatch(/Failed to read workflow run/i);
    expect(kicked.message ?? '').not.toMatch(/Failed to read workflow return value/i);
    expect(kicked.message ?? '').not.toMatch(/BACKEND_URL is not configured/i);
    expect(fetchMock.mock.calls.some(([input]) => String(input).includes('/videos/process'))).toBe(
      false,
    );
  });

  it('retries origin video-to-software on abort timeout when a ready transcript exists', async () => {
    vi.mocked(checkBackendHealth).mockResolvedValue({
      configured: true,
      available: true,
      host: 'api.uvai.io',
    });
    vi.mocked(getBackendConfig).mockReturnValue({
      configured: true,
      url: 'https://api.uvai.io',
    });
    let vtsAttempts = 0;
    const fetchMock = vi.fn().mockImplementation(async (input: unknown) => {
      const href = String(input);
      if (href.includes('/videos/process')) {
        throw new Error('must not re-hit YouTube via videos/process');
      }
      if (href.includes('/video-to-software')) {
        vtsAttempts += 1;
        if (vtsAttempts === 1) {
          throw Object.assign(new Error('The operation was aborted due to timeout'), {
            name: 'TimeoutError',
          });
        }
        return {
          ok: true,
          status: 202,
          json: async () => ({
            status: 'success',
            data: { job_id: 'job_01M2AKRAVZ0SEBM670BGXEMCQZ' },
          }),
        };
      }
      throw new Error(`unexpected fetch ${href}`);
    });
    vi.stubGlobal('fetch', fetchMock);
    const kicked = await kickoffAsyncVideoJob(
      'https://www.youtube.com/watch?v=XYMcBrFSJ4c',
      { transcript: READY_TRANSCRIPT },
    );
    expect(kicked.kind).toBe('job');
    expect(kicked.jobId).toBe('job_01M2AKRAVZ0SEBM670BGXEMCQZ');
    expect(kicked.retryable).not.toBe(true);
    expect(kicked.message ?? '').not.toMatch(/aborted due to timeout/i);
    expect(kicked.message ?? '').not.toMatch(/HTTP 524/);
    expect(kicked.message ?? '').not.toMatch(/Sign in to confirm you’re not a bot/i);
    expect(kicked.message ?? '').not.toMatch(/UNKNOWN checks are not a live URL/i);
    expect(kicked.message ?? '').not.toMatch(/Failed to read workflow run/i);
    expect(kicked.message ?? '').not.toMatch(/Failed to read workflow return value/i);
    expect(kicked.message ?? '').not.toMatch(/BACKEND_URL is not configured/i);
    expect(vtsAttempts).toBe(2);
    expect(fetchMock.mock.calls.some(([input]) => String(input).includes('/videos/process'))).toBe(
      false,
    );
  });

  it('does not HOLD the raw abort string when ready-transcript vts retries still time out', async () => {
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
      if (href.includes('/videos/process')) {
        throw new Error('must not re-hit YouTube via videos/process');
      }
      if (href.includes('/video-to-software')) {
        throw Object.assign(new Error('The operation was aborted due to timeout'), {
          name: 'TimeoutError',
        });
      }
      throw new Error(`unexpected fetch ${href}`);
    });
    vi.stubGlobal('fetch', fetchMock);
    const kicked = await kickoffAsyncVideoJob(
      'https://www.youtube.com/watch?v=XYMcBrFSJ4c',
      { transcript: READY_TRANSCRIPT },
    );
    expect(kicked.kind).toBe('failed');
    expect(kicked.retryable).toBe(true);
    expect(kicked.jobId).toBeUndefined();
    expect(kicked.message ?? '').toMatch(/ready transcript|must not re-fetch YouTube|no verified deploy receipt|origin job/i);
    expect(kicked.message ?? '').not.toMatch(/aborted due to timeout/i);
    expect(kicked.message ?? '').not.toMatch(/HTTP 524/);
    expect(kicked.message ?? '').not.toMatch(/Sign in to confirm you’re not a bot/i);
    expect(kicked.message ?? '').not.toMatch(/UNKNOWN checks are not a live URL/i);
    expect(kicked.message ?? '').not.toMatch(/Failed to read workflow run/i);
    expect(kicked.message ?? '').not.toMatch(/Failed to read workflow return value/i);
    expect(kicked.message ?? '').not.toMatch(/BACKEND_URL is not configured/i);
    expect(fetchMock.mock.calls.filter(([input]) => String(input).includes('/video-to-software')).length).toBeGreaterThan(1);
    expect(fetchMock.mock.calls.some(([input]) => String(input).includes('/videos/process'))).toBe(
      false,
    );
  });

  it('treats a job status abort timeout as retryable, not a terminal abort HOLD', async () => {
    vi.mocked(getBackendConfig).mockReturnValue({
      configured: true,
      url: 'https://api.uvai.io',
    });
    vi.stubGlobal(
      'fetch',
      vi.fn().mockImplementation(async () => {
        throw Object.assign(new Error('The operation was aborted due to timeout'), {
          name: 'TimeoutError',
        });
      }),
    );
    const status = await fetchAsyncVideoJob('job_01M2AKRAVZ0SEBM670BGXEMCQZ');
    expect(status.ok).toBe(false);
    expect(status.httpStatus).toBe(408);
    expect(status.message ?? '').not.toMatch(/aborted due to timeout/i);
    expect(status.message ?? '').toMatch(/timed out|retry/i);
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

  it('continues the deploy poll after a timeout abort status instead of HOLD', () => {
    const decided = decideStudioDeployPoll(
      {
        ok: false,
        httpStatus: 408,
        message: 'Deploy job status read timed out; retrying',
      },
      {
        jobId: 'job_01M2AKRAVZ0SEBM670BGXEMCQZ',
        transcript: READY_TRANSCRIPT,
      },
    );
    expect(decided.action).toBe('continue');
    expect(JSON.stringify(decided)).not.toMatch(/aborted due to timeout/i);
    expect(JSON.stringify(decided)).not.toMatch(/HTTP 524/);
    expect(JSON.stringify(decided)).not.toMatch(/Sign in to confirm you’re not a bot/i);
    expect(JSON.stringify(decided)).not.toMatch(/UNKNOWN checks are not a live URL/i);
    expect(JSON.stringify(decided)).not.toMatch(/Failed to read workflow run/i);
    expect(JSON.stringify(decided)).not.toMatch(/Failed to read workflow return value/i);
    expect(JSON.stringify(decided)).not.toMatch(/BACKEND_URL is not configured/i);
  });

  it('returns a live poll decision only when the backend supplies a live URL', () => {
    const decided = decideStudioDeployPoll(
      {
        ok: true,
        jobStatus: 'completed',
        live_url: 'https://xy.vercel.app',
      },
      { jobId: 'job_01M2AKRAVZ0SEBM670BGXEMCQZ', transcript: READY_TRANSCRIPT },
    );
    expect(decided).toEqual({
      action: 'live',
      live_url: 'https://xy.vercel.app',
      jobStatus: 'completed',
      github_repo: undefined,
    });
  });
});
