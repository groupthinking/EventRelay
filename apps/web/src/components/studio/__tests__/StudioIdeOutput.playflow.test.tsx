// @vitest-environment jsdom
import React from 'react';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it } from 'vitest';
import StudioIdeOutput from '@/components/studio/StudioIdeOutput';
import type { Video } from '@/store/dashboard-types';

const baseVideo: Video = {
  id: 'row-output',
  title: 'Playflow output',
  url: 'https://www.youtube.com/watch?v=auJzb1D-fag',
  status: 'complete',
  progress: 100,
  transcript: 'Enough transcript text for analysis ready state in Studio tests.',
};

afterEach(() => {
  cleanup();
});

describe('StudioIdeOutput playflow', () => {
  it('renders pack-named stack checks as skip/unknown rows that do not look like a hold', () => {
    render(
      <StudioIdeOutput
        video={baseVideo}
        stackChecks={[
          {
            id: 'chk_tool_seadance',
            title: 'Use SeaDance 2.5 as named in the video',
            status: 'unknown',
            statusLabel: 'Unknown — UVAI cannot run this check',
            holdsShip: false,
          },
        ]}
      />,
    );
    fireEvent.click(screen.getByTestId('studio-ide-output-tab-tools'));
    const row = screen.getByTestId('studio-stack-check-chk_tool_seadance');
    expect(row.textContent).toMatch(/SeaDance 2\.5/);
    expect(row.textContent).toMatch(/cannot run this check/i);
    expect(row.textContent).not.toMatch(/production is held/i);
  });

  it('renders review_action results as cards with status, title, and detail', () => {
    render(
      <StudioIdeOutput
        video={baseVideo}
        reviewActions={[
          { tool: 'review_action', status: 'proposed', result: 'Review evidence' },
        ]}
      />,
    );
    fireEvent.click(screen.getByTestId('studio-ide-output-tab-intent'));
    const card = screen.getByTestId('studio-review-action-card');
    expect(card.textContent).toMatch(/review this result/i);
    expect(card.textContent).toMatch(/needs review/i);
    expect(card.textContent).toMatch(/Review evidence/);
  });
});
