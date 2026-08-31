import { beforeEach, describe, expect, it, vi } from 'vitest';

import { useActionAgentStore } from '@/store/action-agent-store';

const preparedActions = [
  {
    tool: 'create_workflow_task',
    input: { title: 'Review the source', priority: 'medium' },
    status: 'pending' as const,
    result: 'Prepared for review. No tool has been executed.',
  },
  {
    tool: 'save_resource',
    input: { title: 'Caption evidence', content: 'Verified excerpt' },
    status: 'pending' as const,
    result: 'Prepared for review. No tool has been executed.',
  },
];

describe('action agent store video review boundary', () => {
  beforeEach(() => {
    useActionAgentStore.getState().reset();
    vi.unstubAllGlobals();
  });

  it('keys a prepared plan to its source video and refuses cross-video confirmation', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({ success: true, provider: 'test', actions: preparedActions }),
          { status: 200, headers: { 'content-type': 'application/json' } },
        ),
      );
    vi.stubGlobal('fetch', fetchMock);

    await useActionAgentStore
      .getState()
      .runFromTranscript('A sufficiently long verified transcript for review.', 'Video A', 'video-a');

    expect(useActionAgentStore.getState().sourceVideoId).toBe('video-a');
    expect(useActionAgentStore.getState().lifecycle.phase).toBe('dispatching');

    await useActionAgentStore.getState().confirmPreparedActions(undefined, 'video-b');

    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(useActionAgentStore.getState().lifecycle.phase).toBe('dispatching');
  });

  it('executes only the actions selected during review', async () => {
    const fulfilled = [{ ...preparedActions[1], status: 'fulfilled' as const }];
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({ success: true, provider: 'test', actions: preparedActions }),
          { status: 200, headers: { 'content-type': 'application/json' } },
        ),
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({ success: true, provider: 'confirmed-plan', actions: fulfilled }),
          { status: 200, headers: { 'content-type': 'application/json' } },
        ),
      );
    vi.stubGlobal('fetch', fetchMock);

    await useActionAgentStore
      .getState()
      .runFromTranscript('A sufficiently long verified transcript for review.', 'Video A', 'video-a');
    await useActionAgentStore
      .getState()
      .confirmPreparedActions([preparedActions[1]], 'video-a');

    const executeRequest = fetchMock.mock.calls[1]?.[1] as RequestInit;
    expect(JSON.parse(String(executeRequest.body))).toEqual(
      expect.objectContaining({ mode: 'execute', actions: [preparedActions[1]] }),
    );
    expect(useActionAgentStore.getState().lifecycle.actions).toEqual(fulfilled);
  });
});
