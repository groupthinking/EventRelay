import { afterEach, describe, expect, it, vi } from 'vitest';
import {
  getVideoToActionsStatus,
  pollVideoToActions,
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
});
