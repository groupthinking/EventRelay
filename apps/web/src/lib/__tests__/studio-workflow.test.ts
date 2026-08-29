import { afterEach, describe, expect, it, vi } from 'vitest';
import {
  getVideoToActionsStatus,
  pollStudioDeploy,
  pollVideoToActions,
  startStudioDeploy,
  startVideoToActions,
} from '@/lib/studio-workflow';

describe('studio-workflow (WDK Product v1)', () => {
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
