// @vitest-environment jsdom
import React from 'react';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import StudioIdeChat from '@/components/studio/StudioIdeChat';

describe('StudioIdeChat plan interview chaining & Antigravity UX', () => {
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
    expect(screen.getByTestId('studio-ide-chat-input')).toHaveProperty(
      'value',
      'Plan a build from this Video Pack',
    );
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
    expect(secondBody.planInterview).toEqual({
      useCase: 'Build a safety checklist from the video',
    });
  });

  it('shows active extraction timeline card instead of idle prompt while a video run is in progress', () => {
    render(
      <StudioIdeChat
        videoId="6TrjBFW6EKg"
        packId={null}
        disabled
        activeStage="transcript"
      />,
    );
    expect(screen.getByText('Extracting Video Pack…')).toBeTruthy();
    expect(screen.getByTestId('studio-chat-extraction-card')).toBeTruthy();
    expect(screen.queryByText('Run a video to start chatting')).toBeNull();
    const input = screen.getByTestId('studio-ide-chat-input') as HTMLTextAreaElement;
    expect(input.placeholder).toBe('Extracting video pack…');
    expect(input.disabled).toBe(true);
  });

  it('renders identity header, 3 suggested prompt pills, clickable timestamp chips, and Clear button', async () => {
    const onSeek = vi.fn();
    const network = vi.fn().mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => ({
        answer: 'Start setup at 1:23 and verify tests at [transcript 45s].',
      }),
    });
    vi.stubGlobal('fetch', network);

    render(
      <StudioIdeChat
        videoId="auJzb1D-fag"
        packId="vp:v0:auJzb1D-fag"
        videoTitle="Build a Next.js workflow"
        onSeek={onSeek}
      />,
    );

    expect(screen.getByTestId('studio-chat-header')).toBeTruthy();
    expect(screen.getByText('Studio Assistant')).toBeTruthy();
    expect(screen.getByText('ASK UVAI')).toBeTruthy();
    expect(screen.getByTestId('studio-chat-status-pill').textContent).toBe('Pack ready');

    const summarizePill = screen.getByTestId('studio-chat-prompt-summarize');
    expect(screen.getByTestId('studio-chat-prompt-stack')).toBeTruthy();
    expect(screen.getByTestId('studio-ide-chat-plan-prompt')).toBeTruthy();

    fireEvent.click(summarizePill);
    await waitFor(() => expect(network).toHaveBeenCalledTimes(1));

    const chips = await screen.findAllByTestId('chat-timestamp-chip');
    expect(chips).toHaveLength(2);
    fireEvent.click(chips[0]);
    fireEvent.click(chips[1]);
    expect(onSeek).toHaveBeenNthCalledWith(1, 83);
    expect(onSeek).toHaveBeenNthCalledWith(2, 45);

    fireEvent.click(screen.getByTestId('studio-ide-chat-clear'));
    expect(screen.queryByTestId('chat-msg-assistant')).toBeNull();
    expect(screen.getByTestId('studio-chat-prompt-summarize')).toBeTruthy();
  });

  it('submits a pasted YouTube URL via onSubmitUrl with Enter key and supports Shift+Enter newlines', () => {
    const onSubmitUrl = vi.fn();
    const network = vi.fn();
    vi.stubGlobal('fetch', network);

    render(<StudioIdeChat videoId={null} packId={null} onSubmitUrl={onSubmitUrl} />);

    const input = screen.getByTestId('studio-ide-chat-input') as HTMLTextAreaElement;
    expect(input.disabled).toBe(false);

    fireEvent.change(input, { target: { value: 'https://youtu.be/auJzb1D-fag' } });
    fireEvent.keyDown(input, { key: 'Enter', shiftKey: true });
    expect(onSubmitUrl).not.toHaveBeenCalled();

    fireEvent.keyDown(input, { key: 'Enter', shiftKey: false });
    expect(onSubmitUrl).toHaveBeenCalledWith('https://www.youtube.com/watch?v=auJzb1D-fag');
    expect(network).not.toHaveBeenCalled();
    expect(input.value).toBe('');
  });
});
