// @vitest-environment jsdom
import React from 'react';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import StudioIdeChat from '@/components/studio/StudioIdeChat';

describe('StudioIdeChat sparkle interview chaining', () => {
  beforeEach(() => {
    vi.stubGlobal('React', React);
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it('renders interview questions and keeps sparkle intent/interview payload on follow-up turn', async () => {
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
            'What exact chore or workflow should sparkle pills automate?',
            'What should trigger each run (time, event, or manual action)?',
            'Which tools and systems must it update (for example Calendar, Slack, email)?',
            'What rules or constraints must never be violated?',
            'How will you measure success each week?',
          ],
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({
          answer: 'Sparkle Pills System Plan',
          requiresInterview: false,
          provider: 'sparkle-pills-planner',
        }),
      });
    vi.stubGlobal('fetch', network);

    render(<StudioIdeChat videoId="auJzb1D-fag" packId="vp:v0:auJzb1D-fag" />);

    fireEvent.change(screen.getByTestId('studio-ide-chat-input'), {
      target: { value: 'Build me a system for using sparkle pills' },
    });
    fireEvent.submit(screen.getByTestId('studio-ide-chat-composer'));

    await waitFor(() => expect(network).toHaveBeenCalledTimes(1));
    await screen.findByText(/What exact chore or workflow should sparkle pills automate\?/i);

    fireEvent.change(screen.getByTestId('studio-ide-chat-input'), {
      target: {
        value: [
          'useCase: Manage weekday focus sessions',
          'trigger: Start each weekday at 08:30',
          'tools: Google Calendar, Slack, Notion',
          'constraints: No notifications after 21:00',
          'successSignal: 5 sessions completed per week',
        ].join('\n'),
      },
    });
    fireEvent.submit(screen.getByTestId('studio-ide-chat-composer'));

    await waitFor(() => expect(network).toHaveBeenCalledTimes(2));
    const secondBody = JSON.parse((network.mock.calls[1]?.[1] as RequestInit).body as string) as {
      sparkleIntent?: boolean;
      sparkleInterview?: {
        useCase?: string;
        trigger?: string;
        tools?: string[];
        constraints?: string;
        successSignal?: string;
      };
    };

    expect(secondBody.sparkleIntent).toBe(true);
    expect(secondBody.sparkleInterview).toEqual({
      useCase: 'Manage weekday focus sessions',
      trigger: 'Start each weekday at 08:30',
      tools: ['Google Calendar', 'Slack', 'Notion'],
      constraints: 'No notifications after 21:00',
      successSignal: '5 sessions completed per week',
    });
    await screen.findByText('Sparkle Pills System Plan');
  });

  it('does not treat the request that starts the interview as its first answer', async () => {
    const interview = {
      answer: 'Before I design the system, I need a short use-case interview.',
      requiresInterview: true,
      interviewQuestions: ['What exact chore or workflow should sparkle pills automate?'],
    };
    const network = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => interview,
    });
    vi.stubGlobal('fetch', network);

    render(<StudioIdeChat videoId="auJzb1D-fag" packId="vp:v0:auJzb1D-fag" />);
    fireEvent.change(screen.getByTestId('studio-ide-chat-input'), {
      target: { value: 'Build me a system for using sparkle pills' },
    });
    fireEvent.submit(screen.getByTestId('studio-ide-chat-composer'));
    await screen.findByText(/What exact chore or workflow should sparkle pills automate\?/i);

    fireEvent.change(screen.getByTestId('studio-ide-chat-input'), {
      target: { value: 'Manage weekday focus sessions' },
    });
    fireEvent.submit(screen.getByTestId('studio-ide-chat-composer'));
    await waitFor(() => expect(network).toHaveBeenCalledTimes(2));

    const secondBody = JSON.parse((network.mock.calls[1]?.[1] as RequestInit).body as string);
    expect(secondBody.sparkleIntent).toBe(true);
    expect(secondBody.sparkleInterview).toEqual({ useCase: 'Manage weekday focus sessions' });
  });
});
