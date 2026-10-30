// @vitest-environment jsdom
import React from 'react';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import StudioIdeOutput from '@/components/studio/StudioIdeOutput';
import type { Video } from '@/store/dashboard-types';
import { studioEventsEmptyMessage } from '@/lib/studio-pipeline-status';

const emptyEventsVideo: Video = {
  id: 'pBsT6v-ciO8',
  title: 'AI gold rushes',
  url: 'https://www.youtube.com/watch?v=pBsT6v-ciO8',
  status: 'complete',
  progress: 100,
  transcript: 'SeaDance 2.5 and Cluely Desktop from the video.',
  events: [],
};

afterEach(() => {
  cleanup();
});

describe('StudioIdeOutput playflow (B/E/F + events vs Insights)', () => {
  it('labels the Events tab Events, never Insights, and tells the truth when events[] is empty', () => {
    const emptyMessage = studioEventsEmptyMessage({
      busy: false,
      hasCompletedRun: true,
      eventCount: 0,
      hasArchitecture: true,
      artifactCount: 2,
      toolCount: 4,
    });

    render(
      <StudioIdeOutput
        video={emptyEventsVideo}
        eventsEmptyMessage={emptyMessage}
        packWorkbench={<div data-testid="pack-workbench">Architecture from this pack</div>}
      />,
    );

    expect(screen.getByTestId('studio-ide-output-tab-events').textContent).toBe('Events');
    expect(screen.queryByRole('tab', { name: /insights/i })).toBeNull();
    expect(screen.getByTestId('studio-ide-output-events').textContent).toMatch(/no extracted events/i);
    expect(screen.getByTestId('studio-ide-output-events').textContent.toLowerCase()).not.toContain(
      'insights',
    );
    expect(screen.getByTestId('pack-workbench').textContent).toMatch(/architecture/i);
  });

  it('shows skip/unknown stack-check labels so SeaDance/Cluely do not look like a production hold', () => {
    render(
      <StudioIdeOutput
        video={emptyEventsVideo}
        stackChecks={[
          {
            id: 'chk_seadance',
            title: 'Use SeaDance 2.5 as named in the video',
            status: 'unknown',
            statusLabel: 'Unknown — UVAI cannot run this check',
            holdsShip: false,
          },
          {
            id: 'chk_cluely',
            title: 'Use Cluely Desktop as named in the video',
            status: 'unknown',
            statusLabel: 'Unknown — UVAI cannot run this check',
            holdsShip: false,
          },
        ]}
      />,
    );

    fireEvent.click(screen.getByTestId('studio-ide-output-tab-tools'));
    const tools = screen.getByTestId('studio-ide-output-tools');
    expect(tools.textContent).toMatch(/SeaDance/i);
    expect(tools.textContent).toMatch(/Cluely/i);
    expect(tools.textContent).toMatch(/cannot run this check/i);
    expect(tools.textContent.toLowerCase()).not.toMatch(/held until/);
  });

  it('renders review_action as a card with a clear CTA, not Run tools → review_action', () => {
    render(
      <StudioIdeOutput
        video={emptyEventsVideo}
        reviewActions={[
          {
            tool: 'review_action',
            status: 'proposed',
            result: 'Check the pack evidence before you ship.',
          },
        ]}
      />,
    );

    fireEvent.click(screen.getByTestId('studio-ide-output-tab-intent'));
    const intent = screen.getByTestId('studio-ide-output-intent');
    expect(intent.textContent).toMatch(/review this result/i);
    expect(intent.textContent).toMatch(/needs review/i);
    expect(intent.textContent).toContain('Check the pack evidence before you ship.');
    expect(intent.textContent.toLowerCase()).not.toContain('run tools');
    expect(intent.textContent).not.toMatch(/review_action/);
  });

  it('offers Retry transcript in the Transcript tab when the run failed', () => {
    const onRetry = vi.fn();
    render(
      <StudioIdeOutput
        video={{
          ...emptyEventsVideo,
          status: 'failed',
          transcript: '',
          failure: {
            stage: 'analysis',
            message: 'Captions were not available.',
            retryable: true,
            failedAt: '2026-10-17T00:00:00.000Z',
          },
        }}
        showTranscriptRetry
        onRetryTranscript={onRetry}
      />,
    );

    fireEvent.click(screen.getByTestId('studio-ide-output-tab-transcript'));
    fireEvent.click(screen.getByTestId('studio-transcript-retry'));
    expect(onRetry).toHaveBeenCalledTimes(1);
  });
});
