// @vitest-environment jsdom
import React from 'react';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import StudioIdeChat from '@/components/studio/StudioIdeChat';
import { loadSamplePack } from '@/lib/sample-pack';
import { studioPackFormation } from '@/lib/studio-pipeline-status';

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

  it('shows Cut 3 artifact stream instead of idle prompt while a video run is in progress', () => {
    render(
      <StudioIdeChat
        videoId="auJzb1D-fag"
        packId={null}
        disabled
        isWorking
        artifactStreamInputs={{
          busy: true,
          elapsedSeconds: 12,
          progress: 8,
        }}
      />,
    );
    expect(screen.getByText('Extracting Video Pack…')).toBeTruthy();
    const stream = screen.getByTestId('studio-artifact-stream');
    expect(stream.getAttribute('data-phase')).toMatch(/skeletal|filling/);
    expect(stream.getAttribute('data-video-id')).toBe('auJzb1D-fag');
    expect(screen.queryByText('Run a video to start chatting')).toBeNull();
    const input = screen.getByTestId('studio-ide-chat-input') as HTMLTextAreaElement;
    expect(input.placeholder).toBe('Extracting video pack…');
    expect(input.disabled).toBe(true);
  });

  it('settles the artifact stream into real pack preview when formation is ready', () => {
    const citation = loadSamplePack();
    expect(citation.videoId).toBe('auJzb1D-fag');
    const formation = studioPackFormation(citation);
    render(
      <StudioIdeChat
        videoId={citation.videoId}
        packId={citation.packId}
        artifactStreamInputs={{
          busy: false,
          hasPack: true,
          hasTranscript: true,
          formation: {
            architecture: formation.architecture,
            artifacts: formation.artifacts,
            tools: formation.tools,
          },
        }}
      />,
    );
    expect(screen.getByTestId('studio-artifact-stream').getAttribute('data-phase')).toBe('settled');
    expect(screen.getByTestId('studio-artifact-stream-preview')).toBeTruthy();
    expect(screen.getByTestId('studio-artifact-stream-architecture').textContent).toMatch(
      /Multimodal ingestion/i,
    );
    expect(screen.getByTestId('studio-artifact-stream-artifacts').textContent).toMatch(
      /SpatialDetector/,
    );
    expect(screen.getByTestId('studio-artifact-stream-tools').textContent).toMatch(
      /Google AI Studio/,
    );
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
    expect(input.id).toBe('studio-chat-input');
    expect(input.name).toBe('studioChatMessage');

    fireEvent.change(input, { target: { value: 'https://youtu.be/auJzb1D-fag' } });
    fireEvent.keyDown(input, { key: 'Enter', shiftKey: true });
    expect(onSubmitUrl).not.toHaveBeenCalled();

    fireEvent.keyDown(input, { key: 'Enter', shiftKey: false });
    expect(onSubmitUrl).toHaveBeenCalledWith('https://www.youtube.com/watch?v=auJzb1D-fag');
    expect(network).not.toHaveBeenCalled();
    expect(input.value).toBe('');
  });

  it('sanitizes videoId before building external timestamp fallback links', async () => {
    const network = vi.fn().mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => ({ answer: 'Check 1:05 for setup.' }),
    });
    vi.stubGlobal('fetch', network);

    render(<StudioIdeChat videoId={'" onclick="alert(1)'} packId="vp:v0:test" />);
    fireEvent.change(screen.getByTestId('studio-ide-chat-input'), { target: { value: 'Where is setup?' } });
    fireEvent.submit(screen.getByTestId('studio-ide-chat-composer'));

    const chip = await screen.findByTestId('chat-timestamp-chip');
    expect(chip.tagName).toBe('SPAN');
    expect(chip.getAttribute('href')).toBeNull();
  });
});
