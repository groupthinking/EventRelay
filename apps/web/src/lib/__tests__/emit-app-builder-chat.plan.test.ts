// @vitest-environment jsdom
import { runInNewContext } from 'node:vm';
import ts from 'typescript';
import { waitFor } from '@testing-library/dom';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { emitAppBuilderSandbox } from '@/lib/emit-app-builder-sandbox';
import {
  QJ_PACK_ID,
  QJ_SOURCE_HASH,
  QJ_SOURCE_URL,
  QJ_TRANSCRIPT,
  QJ_VIDEO_ID,
  QJ_VISUAL_EVENTS,
  QJ_SOP_STEPS,
} from '@/lib/__fixtures__/qj-z5ohr7sga-emit';

describe('emitted App Builder chat Video Pack planning', () => {
  afterEach(() => {
    document.body.innerHTML = '';
    localStorage.clear();
    vi.restoreAllMocks();
  });

  it('renders questions and submits accumulated interview answers on the bound second turn', async () => {
    const sandbox = emitAppBuilderSandbox({
      videoId: QJ_VIDEO_ID,
      sourceUrl: QJ_SOURCE_URL,
      sourceHash: QJ_SOURCE_HASH,
      packId: QJ_PACK_ID,
      transcript: QJ_TRANSCRIPT,
      visualEvents: QJ_VISUAL_EVENTS,
      sopSteps: QJ_SOP_STEPS,
    });
    const main = sandbox.files['src/main.ts'];
    const start = main.indexOf('function bindChatRail(): void {');
    const end = main.indexOf('\nfunction bindShellLayout(): void {', start);
    expect(start).toBeGreaterThan(-1);
    expect(end).toBeGreaterThan(start);
    const source = main.slice(start, end);
    const compiled = ts.transpileModule(source, {
      compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.None },
    }).outputText;

    document.body.innerHTML = `
      <div data-testid="shell-chat-panel"></div>
      <div data-testid="shell-chat-messages"></div>
      <form data-testid="shell-chat-composer">
        <textarea data-testid="shell-chat-input"></textarea>
        <button data-testid="shell-chat-send" type="submit">Send</button>
      </form>`;
    vi.stubGlobal('scrollTo', vi.fn());
    Element.prototype.scrollIntoView = vi.fn();
    const network = vi.fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          answer: 'Before planning, answer these questions.',
          requiresInterview: true,
          interviewQuestions: [
            'What exact deliverable should the agent build from this video?',
            'What event starts it?',
            'Which tools are available?',
            'What constraints apply?',
            'What proves it works?',
          ],
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ answer: 'Video Pack Build Plan', requiresInterview: false, provider: 'video-pack-planner' }),
      });
    runInNewContext(`${compiled}\nbindChatRail();`, {
      document,
      fetch: network,
      pack: { videoId: QJ_VIDEO_ID, packId: QJ_PACK_ID, sourceUrl: QJ_SOURCE_URL },
      storagePrefix: 'test-pack',
      localStorage,
      AbortSignal,
      console,
    });

    const form = document.querySelector<HTMLFormElement>('[data-testid="shell-chat-composer"]')!;
    const input = document.querySelector<HTMLTextAreaElement>('[data-testid="shell-chat-input"]')!;
    const messages = document.querySelector<HTMLElement>('[data-testid="shell-chat-messages"]')!;
    input.value = 'Plan a build from this Video Pack';
    form.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
    await waitFor(() => expect(messages.textContent).toContain('What exact deliverable should the agent build'));

    input.value = [
      'useCase: Build a safety checklist from the video',
      'trigger: User selects the source video',
      'tools: Git, npm, Playwright',
      'constraints: No invented video claims',
      'successSignal: Checklist steps match the cited source',
    ].join('\n');
    form.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
    await waitFor(() => expect(messages.textContent).toContain('Video Pack Build Plan'));

    expect(network).toHaveBeenCalledTimes(2);
    const second = JSON.parse((network.mock.calls[1]?.[1] as RequestInit).body as string);
    expect(second).toMatchObject({
      video_id: QJ_VIDEO_ID,
      pack_id: QJ_PACK_ID,
      planIntent: true,
      planInterview: {
        useCase: 'Build a safety checklist from the video',
        trigger: 'User selects the source video',
        tools: ['Git', 'npm', 'Playwright'],
        constraints: 'No invented video claims',
        successSignal: 'Checklist steps match the cited source',
      },
    });
  });
});
