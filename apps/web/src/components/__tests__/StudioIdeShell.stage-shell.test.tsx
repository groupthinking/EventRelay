// @vitest-environment jsdom
/**
 * Cut 1 exit checks: Hybrid D activity + stage + context; collapse; no persona grid.
 */
import React from 'react';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import StudioIdeShell, {
  STUDIO_ACTIVITY_MODES,
} from '@/components/studio/StudioIdeShell';

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe('Cut 1 stage shell layout contract', () => {
  it('exposes Video · Agents · Tools · Files · Canvas · Code activity modes only', () => {
    vi.stubGlobal('React', React);
    render(
      <StudioIdeShell
        toolbar={null}
        videoPane={<div data-testid="fixture-player">player</div>}
        chatPane={<p>chat</p>}
        outputPane={<p>output</p>}
      />,
    );

    expect(STUDIO_ACTIVITY_MODES).toEqual([
      'video',
      'agents',
      'tools',
      'files',
      'canvas',
      'code',
    ]);
    for (const mode of STUDIO_ACTIVITY_MODES) {
      expect(screen.getByTestId(`studio-activity-${mode}`)).toBeTruthy();
    }
    expect(screen.queryByText(/HIRE/i)).toBeNull();
    expect(screen.queryByRole('button', { name: /hire/i })).toBeNull();
  });

  it('keeps the stage mounted while context collapses and restores', () => {
    vi.stubGlobal('React', React);
    render(
      <StudioIdeShell
        toolbar={<button type="button">Analyze</button>}
        videoPane={<div data-testid="fixture-player">auJzb1D-fag</div>}
        chatPane={<p>Agents stream</p>}
        outputPane={<p>Pack tools</p>}
      />,
    );

    expect(screen.getByTestId('fixture-player').textContent).toBe('auJzb1D-fag');
    fireEvent.click(screen.getByTestId('studio-context-collapse'));
    expect(screen.getByTestId('studio-ide-video-pane')).toBeTruthy();
    expect(screen.getByTestId('fixture-player')).toBeTruthy();
    fireEvent.click(screen.getByTestId('studio-context-rail-collapsed'));
    expect(screen.getByTestId('studio-ide-chat-pane').hasAttribute('hidden')).toBe(false);
  });

  it('maps Files / Canvas / Code activity onto the output context pane', () => {
    vi.stubGlobal('React', React);
    render(
      <StudioIdeShell
        toolbar={null}
        videoPane={<p>stage</p>}
        chatPane={<p>agents</p>}
        outputPane={<p>deliverables</p>}
      />,
    );

    for (const mode of ['files', 'canvas', 'code'] as const) {
      fireEvent.click(screen.getByTestId(`studio-activity-${mode}`));
      expect(screen.getByTestId('studio-ide-shell').dataset.contextMode).toBe('output');
      expect(screen.getByTestId('studio-ide-output-pane').hasAttribute('hidden')).toBe(false);
      expect(screen.getByTestId('studio-ide-chat-pane').hasAttribute('hidden')).toBe(true);
    }
  });
});
