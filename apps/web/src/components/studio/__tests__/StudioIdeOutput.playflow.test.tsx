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
  it('keeps Tasks, event context, and proposal review available beside a runbook', () => {
    render(
      <StudioIdeOutput
        video={baseVideo}
        runbook={<div>Saved video runbook</div>}
        eventsEmptyMessage="This pack has no extracted events. Its source stays available."
        reviewActions={[
          { tool: 'create_workflow_task', input: { title: 'Review the source' }, status: 'pending' },
        ]}
      />,
    );
    expect(screen.getByTestId('studio-ide-output-tab-runbook').getAttribute('aria-selected')).toBe('true');
    expect(screen.getByText('Saved video runbook')).toBeTruthy();

    fireEvent.click(screen.getByTestId('studio-ide-output-tab-tasks'));
    expect(screen.getByTestId('studio-bound-tasks').textContent).toMatch(/No tasks have been executed/);
    expect(screen.queryByText('Saved video runbook')).toBeNull();

    fireEvent.click(screen.getByTestId('studio-ide-output-tab-events'));
    expect(screen.getByTestId('studio-ide-output-events').textContent).toContain('Its source stays available.');
    fireEvent.click(screen.getByTestId('studio-ide-output-tab-intent'));
    fireEvent.click(screen.getByTestId('studio-review-act-button'));
    expect(screen.getByTestId('studio-proposal-detail').textContent).toContain('"title": "Review the source"');
    expect(screen.getByTestId('studio-proposal-detail').textContent).toContain('No tool has been executed');

    fireEvent.click(screen.getByTestId('studio-ide-output-tab-runbook'));
    expect(screen.getByText('Saved video runbook')).toBeTruthy();
  });

  it('opens Tasks when no runbook or video is available', () => {
    render(<StudioIdeOutput video={undefined} />);
    expect(screen.getByTestId('studio-ide-output-tab-tasks').getAttribute('aria-selected')).toBe('true');
    expect(screen.getByTestId('studio-bound-tasks').textContent).toMatch(/Run a YouTube video/);
  });

  it('opens a newly available runbook when the viewer has not selected a tab', () => {
    const view = render(<StudioIdeOutput video={baseVideo} />);
    expect(screen.getByTestId('studio-ide-output-tab-tasks').getAttribute('aria-selected')).toBe('true');
    view.rerender(<StudioIdeOutput video={baseVideo} runbook={<div>Newly available runbook</div>} />);
    expect(screen.getByTestId('studio-ide-output-tab-runbook').getAttribute('aria-selected')).toBe('true');
    expect(screen.getByText('Newly available runbook')).toBeTruthy();
  });

  it('keeps an explicitly selected Tasks tab when a runbook becomes available', () => {
    const view = render(<StudioIdeOutput video={baseVideo} />);
    fireEvent.click(screen.getByTestId('studio-ide-output-tab-tasks'));
    view.rerender(<StudioIdeOutput video={baseVideo} runbook={<div>Newly available runbook</div>} />);
    expect(screen.getByTestId('studio-ide-output-tab-tasks').getAttribute('aria-selected')).toBe('true');
    expect(screen.getByTestId('studio-bound-tasks')).toBeTruthy();
    expect(screen.queryByText('Newly available runbook')).toBeNull();
  });

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

  it('uses the honest Events empty copy and can host a pack workbench', () => {
    render(
      <StudioIdeOutput
        video={baseVideo}
        eventsEmptyMessage="This pack has no extracted events. Architecture and artifacts stay on this page."
        packWorkbench={<div data-testid="studio-pack-workbench">Pack workbench</div>}
      />,
    );
    fireEvent.click(screen.getByTestId('studio-ide-output-tab-events'));
    const events = screen.getByTestId('studio-ide-output-events');
    expect(events.textContent).toMatch(/no extracted events/i);
    expect(events.textContent).not.toMatch(/INSIGHT/i);
    expect(screen.getByTestId('studio-pack-workbench')).toBeTruthy();
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
    fireEvent.click(screen.getByTestId('studio-review-act-button'));
    expect(screen.getByTestId('studio-proposal-detail').textContent).toMatch(/No tool has been executed/i);
  });

  it('lets the viewer inspect a real pending tool proposal', () => {
    render(
      <StudioIdeOutput
        video={baseVideo}
        reviewActions={[
          { tool: 'create_workflow_task', input: { title: 'Draft a task from the video' }, status: 'pending', result: 'Draft a task from the video' },
        ]}
      />,
    );
    fireEvent.click(screen.getByTestId('studio-ide-output-tab-intent'));
    expect(screen.getByText('Needs review')).toBeTruthy();
    fireEvent.click(screen.getByTestId('studio-review-act-button'));
    expect(screen.getByTestId('studio-proposal-detail').textContent).toMatch(/create_workflow_task/);
    expect(screen.getByTestId('studio-proposal-detail').textContent).toMatch(/"title": "Draft a task from the video"/);
    expect(screen.getByTestId('studio-proposal-detail').textContent).toMatch(/No tool has been executed/i);
  });
});
