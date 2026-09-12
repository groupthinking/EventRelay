import { afterEach, describe, expect, it, vi } from 'vitest';
import {
  getVideoToActionsStatus,
  pollStudioDeploy,
  pollVideoToActions,
  startStudioDeploy,
  startVideoToActions,
  isTransientWorkflowRunReadError,
  isUnreadWorkflowRun,
  workflowReturnErrorMessage,
} from '@/lib/studio-workflow';

describe('studio-workflow (WDK Product v1)', () => {
  it('prefers a failed-run cause over a generic unread-return message', () => {
    const cause = new Error('Deploy job job_1 still complete');
    const failed = new Error('Workflow run failed');
    Object.assign(failed, { cause });
    expect(workflowReturnErrorMessage(failed)).toBe('Deploy job job_1 still complete');
    expect(workflowReturnErrorMessage(new Error('fetch failed'))).toBe('fetch failed');
  });

  it('treats Request-parse GET failures as unread workflow run, not a terminal HOLD', () => {
    const parseErr = new TypeError('Failed to parse URL from [object Request]');
    Object.assign(parseErr, {
      cause: Object.assign(new TypeError('Invalid URL'), { code: 'ERR_INVALID_URL' }),
    });
    expect(isTransientWorkflowRunReadError(parseErr)).toBe(true);
    expect(
      isUnreadWorkflowRun({
        status: 500,
        error: 'Failed to read workflow run',
      }),
    ).toBe(true);
    expect(
      isUnreadWorkflowRun({
        runStatus: 'completed',
        result: { kind: 'live', live_url: 'https://ready.example.app' },
      }),
    ).toBe(false);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it('startVideoToActions parses runId and statusUrl', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => ({
          ok: true,
          runId: 'wrun_abc',
          message: 'started',
        }),
      }),
    );

    const result = await startVideoToActions({
      url: 'https://www.youtube.com/watch?v=auJzb1D-fag',
      videoTitle: 'Demo',
    });
    expect(result.ok).toBe(true);
    expect(result.runId).toBe('wrun_abc');
    expect(fetch).toHaveBeenCalledWith(
      '/api/workflows/video-to-actions',
      expect.objectContaining({ method: 'POST' }),
    );
  });

  it('startVideoToActions posts the same-run transcript and events', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ ok: true, runId: 'wrun_same' }),
    });
    vi.stubGlobal('fetch', fetchMock);

    const result = await startVideoToActions({
      url: 'https://www.youtube.com/watch?v=auJzb1D-fag',
      videoTitle: 'Fixture',
      transcript: 'x'.repeat(50),
      events: [{ type: 'action', title: 'Ship', description: 'now' }],
    });
    expect(result.ok).toBe(true);
    expect(result.runId).toBe('wrun_same');
    const init = fetchMock.mock.calls[0][1] as RequestInit;
    const body = JSON.parse(String(init.body));
    expect(body.url).toContain('auJzb1D-fag');
    expect(body.transcript).toHaveLength(50);
    expect(body.events).toEqual([{ type: 'action', title: 'Ship', description: 'now' }]);
  });

  it('startVideoToActions fails closed when ok but no runId', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => ({ ok: true }),
      }),
    );
    const result = await startVideoToActions({
      url: 'https://www.youtube.com/watch?v=x',
    });
    expect(result.ok).toBe(false);
  });

  it('getVideoToActionsStatus maps completed result', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => ({
          ok: true,
          runId: 'wrun_1',
          runStatus: 'completed',
          result: {
            url: 'https://youtu.be/x',
            transcriptChars: 120,
            actionCount: 1,
            provider: 'openai',
            actions: [{ tool: 'create_workflow_task', status: 'fulfilled', result: 'ok' }],
          },
        }),
      }),
    );

    const poll = await getVideoToActionsStatus('wrun_1');
    expect(poll.ok).toBe(true);
    expect(poll.runStatus).toBe('completed');
    expect(poll.result?.actionCount).toBe(1);
    expect(poll.result?.actions[0].tool).toBe('create_workflow_task');
  });

  it('getVideoToActionsStatus maps usedProvidedTranscript', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => ({
          ok: true,
          runId: 'wrun_same',
          runStatus: 'completed',
          result: {
            url: 'https://www.youtube.com/watch?v=auJzb1D-fag',
            transcriptChars: 80,
            actionCount: 1,
            usedProvidedTranscript: true,
            actions: [{ tool: 'create_workflow_task', status: 'fulfilled', result: 'ok' }],
          },
        }),
      }),
    );
    const poll = await getVideoToActionsStatus('wrun_same');
    expect(poll.result?.usedProvidedTranscript).toBe(true);
    expect(poll.result?.url).toContain('auJzb1D-fag');
  });

  it('pollVideoToActions returns when status becomes terminal', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({ ok: true, runId: 'wrun_2', runStatus: 'running' }),
      })
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({
          ok: true,
          runId: 'wrun_2',
          runStatus: 'completed',
          result: {
            url: 'https://youtu.be/x',
            transcriptChars: 50,
            actionCount: 0,
            actions: [],
          },
        }),
      });
    vi.stubGlobal('fetch', fetchMock);

    const poll = await pollVideoToActions('wrun_2', { attempts: 5, delayMs: 1 });
    expect(poll.runStatus).toBe('completed');
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it('startStudioDeploy succeeds when the route returns a runId', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => ({
          ok: true,
          runId: 'wrun_c',
          message: 'started',
        }),
      }),
    );
    const started = await startStudioDeploy({
      url: 'https://www.youtube.com/watch?v=auJzb1D-fag',
    });
    expect(started.ok).toBe(true);
    expect(started.runId).toBe('wrun_c');
    expect(fetch).toHaveBeenCalledWith(
      '/api/workflows/studio-deploy',
      expect.objectContaining({ method: 'POST' }),
    );
  });

  it('startStudioDeploy sends a ready transcript so deploy can skip YouTube re-fetch', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ ok: true, runId: 'wrun_01M2ACYVYXBHM0YVMX1WHMQ1PJ' }),
    });
    vi.stubGlobal('fetch', fetchMock);
    const transcript =
      'Studio Video Pack for XYMcBrFSJ4c already has a usable transcript ready for deploy.';
    const started = await startStudioDeploy({
      url: 'https://www.youtube.com/watch?v=XYMcBrFSJ4c',
      transcript,
    });
    expect(started.ok).toBe(true);
    const init = fetchMock.mock.calls[0]?.[1] as { body?: string };
    const body = JSON.parse(String(init.body)) as { transcript?: string };
    expect(body.transcript).toBe(transcript);
  });

  it('pollStudioDeploy returns on handoff result', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        ok: true,
        runId: 'wrun_c2',
        runStatus: 'completed',
        result: { kind: 'handoff', message: 'BACKEND_URL is not configured' },
      }),
    });
    vi.stubGlobal('fetch', fetchMock);
    const poll = await pollStudioDeploy('wrun_c2', { attempts: 3, delayMs: 1 });
    expect(poll.runStatus).toBe('completed');
    expect(poll.result?.kind).toBe('handoff');
    expect(poll.result?.message).toMatch(/BACKEND_URL/);
  });

  it('startStudioDeploy is not ok when runId is missing', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => ({ ok: true }),
      }),
    );
    const started = await startStudioDeploy({
      url: 'https://www.youtube.com/watch?v=auJzb1D-fag',
    });
    expect(started.ok).toBe(false);
  });

  it('pollStudioDeploy keeps polling when GET cannot read the workflow run yet', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({
        ok: false,
        status: 500,
        json: async () => ({
          ok: false,
          runId: 'wrun_01M2A9Z9SYXD59NG211W9N8EQA',
          error: 'Failed to read workflow run',
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({
          ok: true,
          runId: 'wrun_01M2A9Z9SYXD59NG211W9N8EQA',
          runStatus: 'completed',
          result: { kind: 'live', live_url: 'https://ready.example.app' },
        }),
      });
    vi.stubGlobal('fetch', fetchMock);
    const poll = await pollStudioDeploy('wrun_01M2A9Z9SYXD59NG211W9N8EQA', {
      attempts: 4,
      delayMs: 1,
    });
    expect(poll.result?.live_url).toBe('https://ready.example.app');
    expect(poll.error).not.toBe('Failed to read workflow run');
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it('pollStudioDeploy keeps polling when completed has no result yet', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({
          ok: true,
          runId: 'wrun_unread',
          runStatus: 'completed',
          error: 'Failed to read workflow return value',
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({
          ok: true,
          runId: 'wrun_unread',
          runStatus: 'completed',
          result: { kind: 'live', live_url: 'https://ready.example.app' },
        }),
      });
    vi.stubGlobal('fetch', fetchMock);
    const poll = await pollStudioDeploy('wrun_unread', { attempts: 4, delayMs: 1 });
    expect(poll.result?.live_url).toBe('https://ready.example.app');
    expect(poll.error).toBeUndefined();
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it('pollStudioDeploy returns immediately on 404', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: false,
      status: 404,
      json: async () => ({ error: 'Workflow run not found' }),
    });
    vi.stubGlobal('fetch', fetchMock);
    const poll = await pollStudioDeploy('wrun_missing', { attempts: 5, delayMs: 1 });
    expect(poll.status).toBe(404);
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it('pollStudioDeploy keeps polling while the run is still running until a live URL exists', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({
          ok: true,
          runId: 'wrun_01M2ABB1NJ5TFZ153CTRNTPNW9',
          runStatus: 'running',
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({
          ok: true,
          runId: 'wrun_01M2ABB1NJ5TFZ153CTRNTPNW9',
          runStatus: 'running',
          result: { kind: 'job', jobId: 'job_96f498640b', jobStatus: 'transcribing' },
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({
          ok: true,
          runId: 'wrun_01M2ABB1NJ5TFZ153CTRNTPNW9',
          runStatus: 'completed',
          result: { kind: 'live', live_url: 'https://xy.vercel.app' },
        }),
      });
    vi.stubGlobal('fetch', fetchMock);
    const poll = await pollStudioDeploy('wrun_01M2ABB1NJ5TFZ153CTRNTPNW9', {
      attempts: 5,
      delayMs: 1,
    });
    expect(poll.result?.live_url).toBe('https://xy.vercel.app');
    expect(poll.runStatus).toBe('completed');
    expect(fetchMock).toHaveBeenCalledTimes(3);
  });

  it('pollStudioDeploy exhausted in-flight cites the job status, not UNKNOWN checks', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        ok: true,
        runId: 'wrun_01M2ABB1NJ5TFZ153CTRNTPNW9',
        runStatus: 'running',
        result: { kind: 'job', jobId: 'job_96f498640b', jobStatus: 'transcribing' },
      }),
    });
    vi.stubGlobal('fetch', fetchMock);
    const poll = await pollStudioDeploy('wrun_01M2ABB1NJ5TFZ153CTRNTPNW9', {
      attempts: 2,
      delayMs: 1,
    });
    const text = `${poll.error || ''} ${poll.message || ''}`;
    expect(text).toMatch(/job_96f498640b still transcribing/);
    expect(text).not.toMatch(/UNKNOWN checks are not a live URL/);
    expect(text).not.toMatch(/Failed to read workflow run/);
    expect(text).not.toMatch(/Failed to read workflow return value/);
    expect(text).not.toMatch(/BACKEND_URL is not configured/);
    expect(poll.runStatus).toBe('running');
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it('pollStudioDeploy keeps polling after a status-read abort timeout until a live URL exists', async () => {
    const fetchMock = vi
      .fn()
      .mockRejectedValueOnce(
        Object.assign(new Error('The operation was aborted due to timeout'), {
          name: 'TimeoutError',
        }),
      )
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({
          ok: true,
          runId: 'wrun_01M2AKRAVZ0SEBM670BGXEMCQZ',
          runStatus: 'completed',
          result: { kind: 'live', live_url: 'https://xy.vercel.app' },
        }),
      });
    vi.stubGlobal('fetch', fetchMock);
    const poll = await pollStudioDeploy('wrun_01M2AKRAVZ0SEBM670BGXEMCQZ', {
      attempts: 4,
      delayMs: 1,
    });
    expect(poll.result?.live_url).toBe('https://xy.vercel.app');
    expect(poll.runStatus).toBe('completed');
    expect(poll.error ?? '').not.toMatch(/aborted due to timeout/i);
    expect(poll.message ?? '').not.toMatch(/aborted due to timeout/i);
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it('startStudioDeploy remaps a kickoff abort timeout instead of throwing', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockRejectedValue(
        Object.assign(new Error('The operation was aborted due to timeout'), {
          name: 'TimeoutError',
        }),
      ),
    );
    const started = await startStudioDeploy({
      url: 'https://www.youtube.com/watch?v=XYMcBrFSJ4c',
      transcript:
        'Studio Video Pack for XYMcBrFSJ4c already has a usable transcript ready for deploy.',
    });
    expect(started.ok).toBe(false);
    expect(started.error ?? '').not.toMatch(/aborted due to timeout/i);
    expect(started.error ?? started.message ?? '').toMatch(/timed out|retry|origin/i);
  });

  it('pollStudioDeploy stops when the abort signal fires', async () => {
    const controller = new AbortController();
    const fetchMock = vi.fn().mockImplementation(async () => {
      controller.abort();
      return {
        ok: true,
        status: 200,
        json: async () => ({ ok: true, runId: 'wrun_c3', runStatus: 'running' }),
      };
    });
    vi.stubGlobal('fetch', fetchMock);
    const poll = await pollStudioDeploy('wrun_c3', {
      attempts: 8,
      delayMs: 20,
      signal: controller.signal,
    });
    expect(poll.message).toMatch(/abort/i);
    expect(fetchMock.mock.calls.length).toBeLessThan(8);
  });
});
