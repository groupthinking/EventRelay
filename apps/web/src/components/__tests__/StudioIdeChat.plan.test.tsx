// @vitest-environment jsdom
import React from 'react';
import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import StudioIdeChat from '@/components/studio/StudioIdeChat';

describe('StudioIdeChat plan interview chaining', () => {
  beforeEach(() => {
    vi.stubGlobal('React', React);
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it('renders interview questions and keeps plan intent/interview payload on follow-up turn', async () => {
    const network = vi
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({
          answer:
            'Before I design the system, I need a short use-case interview so the workflow stays concrete and executable.',
          requiresInterview: true,
          interviewQuestions: [
            'What exact deliverable should the agent build from this video?',
            'What event, schedule, or manual action should start the workflow?',
            'Which tools or systems are available in the target codebase?',
            'What constraints must the implementation respect?',
            'What observable test or result will prove the deliverable works?',
          ],
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({
          answer: 'Video Pack Build Plan',
          requiresInterview: false,
          provider: 'video-pack-planner',
        }),
      });
    vi.stubGlobal('fetch', network);

    render(<StudioIdeChat videoId="auJzb1D-fag" packId="vp:v0:auJzb1D-fag" />);

    fireEvent.click(screen.getByTestId('studio-ide-chat-plan-prompt'));
    expect(screen.getByTestId('studio-ide-chat-input').tagName).toBe('TEXTAREA');
    expect(screen.getByTestId('studio-ide-chat-input')).toHaveProperty('value', 'Plan a build from this Video Pack');
    fireEvent.submit(screen.getByTestId('studio-ide-chat-composer'));

    await waitFor(() => expect(network).toHaveBeenCalledTimes(1));
    await screen.findByText(/What exact deliverable should the agent build from this video\?/i);

    fireEvent.change(screen.getByTestId('studio-ide-chat-input'), {
      target: {
        value: [
          'useCase: Build a safety checklist from the video',
          'trigger: User selects the source video',
          'tools: Git, npm, Playwright',
          'constraints: No invented video claims',
          'successSignal: Checklist steps match the cited source',
        ].join('\n'),
      },
    });
    fireEvent.submit(screen.getByTestId('studio-ide-chat-composer'));

    await waitFor(() => expect(network).toHaveBeenCalledTimes(2));
    const secondBody = JSON.parse((network.mock.calls[1]?.[1] as RequestInit).body as string) as {
      planIntent?: boolean;
      planInterview?: {
        useCase?: string;
        trigger?: string;
        tools?: string[];
        constraints?: string;
        successSignal?: string;
      };
    };

    expect(secondBody.planIntent).toBe(true);
    expect(secondBody.planInterview).toEqual({
      useCase: 'Build a safety checklist from the video',
      trigger: 'User selects the source video',
      tools: ['Git', 'npm', 'Playwright'],
      constraints: 'No invented video claims',
      successSignal: 'Checklist steps match the cited source',
    });
    await screen.findByText('Video Pack Build Plan');
  });

  it('does not treat the request that starts the interview as its first answer', async () => {
    const interview = {
      answer: 'Before I design the system, I need a short use-case interview.',
      requiresInterview: true,
      interviewQuestions: ['What exact deliverable should the agent build from this video?'],
    };
    const network = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => interview,
    });
    vi.stubGlobal('fetch', network);

    render(<StudioIdeChat videoId="auJzb1D-fag" packId="vp:v0:auJzb1D-fag" />);
    fireEvent.change(screen.getByTestId('studio-ide-chat-input'), {
      target: { value: 'Plan a build from this Video Pack' },
    });
    fireEvent.submit(screen.getByTestId('studio-ide-chat-composer'));
    await screen.findByText(/What exact deliverable should the agent build from this video\?/i);

    fireEvent.change(screen.getByTestId('studio-ide-chat-input'), {
      target: { value: 'Build a safety checklist from the video' },
    });
    fireEvent.submit(screen.getByTestId('studio-ide-chat-composer'));
    await waitFor(() => expect(network).toHaveBeenCalledTimes(2));

    const secondBody = JSON.parse((network.mock.calls[1]?.[1] as RequestInit).body as string);
    expect(secondBody.planIntent).toBe(true);
    expect(secondBody.planInterview).toEqual({ useCase: 'Build a safety checklist from the video' });
  });
  it('clears interview answers across step mode and restores whole-pack planning', async () => {
    const interview = { answer: 'Planning interview', requiresInterview: true, interviewQuestions: ['What deliverable?'] };
    const network = vi.fn().mockImplementation(async (_url: string, options: RequestInit) => {
      const body = JSON.parse(options.body as string);
      return { ok: true, status: 200, json: async () => body.step ? { answer: 'Step-only reply' } : interview };
    });
    vi.stubGlobal('fetch', network);
    const props = { videoId: 'auJzb1D-fag', packId: 'vp:v0:auJzb1D-fag' };
    const step = { id: 'rb-1', step_number: 1, title: 'Connect the fixture', timestamp_range: [0, 10] as [number, number] };
    const view = render(<StudioIdeChat {...props} />);
    const submit = async (text: string, calls: number) => {
      fireEvent.change(screen.getByTestId('studio-ide-chat-input'), { target: { value: text } });
      fireEvent.submit(screen.getByTestId('studio-ide-chat-composer'));
      await waitFor(() => expect(network).toHaveBeenCalledTimes(calls));
      await waitFor(() => expect(screen.getByTestId('studio-ide-chat-input')).toHaveProperty('disabled', false));
    };
    await submit('Plan a build from this Video Pack', 1);
    await submit('Old whole-pack deliverable', 2);
    expect(JSON.parse(network.mock.calls[1][1].body).planInterview).toEqual({ useCase: 'Old whole-pack deliverable' });

    view.rerender(<StudioIdeChat {...props} stepContext={step} />);
    expect(screen.queryByTestId('studio-ide-chat-plan-prompt')).toBeNull();
    expect(screen.queryByText(/Planning interview/)).toBeNull();
    await submit('Help with this step', 3);
    const stepBody = JSON.parse(network.mock.calls[2][1].body);
    expect(stepBody.step).toEqual(step);
    expect(stepBody).not.toHaveProperty('planIntent');
    expect(stepBody).not.toHaveProperty('planInterview');
    expect(stepBody.history).toEqual([{ role: 'user', content: 'Help with this step' }]);

    view.rerender(<StudioIdeChat {...props} />);
    expect(screen.getByTestId('studio-ide-chat-plan-prompt')).toBeTruthy();
    await submit('Plan a build from this Video Pack', 4);
    expect(JSON.parse(network.mock.calls[3][1].body)).not.toHaveProperty('planInterview');
    await submit('New whole-pack deliverable', 5);
    expect(JSON.parse(network.mock.calls[4][1].body).planInterview).toEqual({ useCase: 'New whole-pack deliverable' });
  });

  it('ignores a pending interview response after switching to a step', async () => {
    let resolveOld: (value: unknown) => void = () => {};
    const oldResponse = new Promise(resolve => { resolveOld = resolve; });
    const network = vi.fn().mockReturnValueOnce(oldResponse).mockResolvedValue({
      ok: true, status: 200, json: async () => ({ answer: 'Current step reply' }),
    });
    vi.stubGlobal('fetch', network);
    const props = { videoId: 'auJzb1D-fag', packId: 'vp:v0:auJzb1D-fag' };
    const view = render(<StudioIdeChat {...props} />);
    fireEvent.change(screen.getByTestId('studio-ide-chat-input'), { target: { value: 'Plan a build from this Video Pack' } });
    fireEvent.submit(screen.getByTestId('studio-ide-chat-composer'));
    expect(screen.getByTestId('studio-ide-chat-input')).toHaveProperty('disabled', true);
    view.rerender(<StudioIdeChat {...props} stepContext={{ id: 'rb-2', step_number: 2, title: 'Check the fixture' }} />);
    await waitFor(() => expect(screen.getByTestId('studio-ide-chat-input')).toHaveProperty('disabled', false));
    await act(async () => {
      resolveOld({ ok: true, status: 200, json: async () => ({ answer: 'Stale interview', requiresInterview: true, interviewQuestions: ['Stale question'] }) });
      await oldResponse;
    });
    expect(screen.queryByText(/Stale interview/)).toBeNull();
    expect(screen.queryByText(/Stale question/)).toBeNull();
    fireEvent.change(screen.getByTestId('studio-ide-chat-input'), { target: { value: 'Check this step' } });
    fireEvent.submit(screen.getByTestId('studio-ide-chat-composer'));
    await screen.findByText('Current step reply');
    const body = JSON.parse(network.mock.calls[1][1].body);
    expect(body.step.id).toBe('rb-2');
    expect(body).not.toHaveProperty('planIntent');
    expect(body).not.toHaveProperty('planInterview');
    expect(body.history).toEqual([{ role: 'user', content: 'Check this step' }]);
  });

  it('focuses the multiline composer when the Step Runner focus nonce changes', () => {
    const props = { videoId: 'auJzb1D-fag', packId: 'vp:v0:auJzb1D-fag', stepContext: { id: 'rb-1', step_number: 1, title: 'Connect the fixture' } };
    const view = render(<StudioIdeChat {...props} focusNonce={0} />);
    const composer = screen.getByTestId('studio-ide-chat-input');
    expect(composer.tagName).toBe('TEXTAREA');
    expect(composer).toHaveProperty('placeholder', 'Paste the error or ask about Step 1…');
    view.rerender(<StudioIdeChat {...props} focusNonce={1} />);
    expect(document.activeElement).toBe(composer);
  });

  it.each(['success', 'error'] as const)('ignores an old %s after returning to the same pack while a new request is pending', async (outcome) => {
    let resolveOld: (value: unknown) => void = () => {};
    let rejectOld: (reason: Error) => void = () => {};
    let resolveCurrent: (value: unknown) => void = () => {};
    const oldResponse = new Promise((resolve, reject) => { resolveOld = resolve; rejectOld = reject; });
    const currentResponse = new Promise(resolve => { resolveCurrent = resolve; });
    const network = vi.fn().mockReturnValueOnce(oldResponse).mockReturnValueOnce(currentResponse);
    vi.stubGlobal('fetch', network);
    const props = { videoId: 'auJzb1D-fag', packId: 'vp:v0:auJzb1D-fag' };
    const view = render(<StudioIdeChat {...props} />);
    fireEvent.change(screen.getByTestId('studio-ide-chat-input'), { target: { value: 'Plan a build from this Video Pack' } });
    fireEvent.submit(screen.getByTestId('studio-ide-chat-composer'));
    await waitFor(() => expect(network).toHaveBeenCalledTimes(1));

    view.rerender(<StudioIdeChat {...props} stepContext={{ id: 'rb-2', step_number: 2, title: 'Check the fixture' }} />);
    await waitFor(() => expect(screen.getByTestId('studio-ide-chat-input')).toHaveProperty('disabled', false));
    view.rerender(<StudioIdeChat {...props} />);
    fireEvent.change(screen.getByTestId('studio-ide-chat-input'), { target: { value: 'Current whole-pack request' } });
    fireEvent.submit(screen.getByTestId('studio-ide-chat-composer'));
    await waitFor(() => expect(network).toHaveBeenCalledTimes(2));

    await act(async () => {
      if (outcome === 'success') {
        resolveOld({ ok: true, status: 200, json: async () => ({ answer: 'Stale prior interview', requiresInterview: true, interviewQuestions: ['Stale prior question'] }) });
      } else {
        rejectOld(new Error('Stale prior failure'));
      }
      await oldResponse.catch(() => {});
    });
    expect(screen.queryAllByText(/Stale prior/)).toHaveLength(0);
    expect(screen.getByTestId('studio-ide-chat-input')).toHaveProperty('disabled', true);
    expect(JSON.parse(network.mock.calls[1][1].body).history).toEqual([{ role: 'user', content: 'Current whole-pack request' }]);

    await act(async () => {
      resolveCurrent({ ok: true, status: 200, json: async () => ({ answer: 'Current whole-pack reply' }) });
      await currentResponse;
    });
    await screen.findByText('Current whole-pack reply');
    expect(screen.getByTestId('studio-ide-chat-input')).toHaveProperty('disabled', false);
  });

});
