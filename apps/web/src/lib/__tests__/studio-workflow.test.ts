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
      url: 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
      videoTitle: 'Demo',
    });
    expect(result.ok).toBe(true);
    expect(result.runId).toBe('wrun_abc');
    expect(fetch).toHaveBeenCalledWith(
      '/api/workflows/video-to-actions',
      expect.objectContaining({ method: 'POST' }),
    );
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

  it('startStudioDeploy requires a runId', async () => {
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
      url: 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
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
});
