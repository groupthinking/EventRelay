// @vitest-environment jsdom
import React from 'react';
import { cleanup, fireEvent, render, screen, within } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import StepRunner, { type StepRunnerPlayer } from '@/components/studio/StepRunner';
import StudioRunbookPane from '@/components/studio/StudioRunbookPane';
import { compileRunbook, type RunbookProgress } from '@/lib/runbook-steps';
import { runbookPackFixture } from '@/lib/__fixtures__/aujzb1d-fag-runbook';

const runbook = compileRunbook({ pack: runbookPackFixture() });

function makePlayer(overrides: Partial<StepRunnerPlayer> = {}): StepRunnerPlayer {
  return {
    ready: true,
    currentTime: 0,
    isPlaying: false,
    seekTo: vi.fn(),
    pause: vi.fn(),
    ...overrides,
  };
}

beforeEach(() => {
  vi.stubGlobal('React', React);
  window.history.replaceState(null, '', '/studio');
  window.localStorage.clear();
});

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe('StepRunner', () => {
  it('opens on Step 0 prerequisites and advances with Next: seeks, updates the hash, re-grounds', () => {
    const player = makePlayer();
    const onActiveStepChange = vi.fn();
    render(
      <StepRunner
        runbook={runbook}
        player={player}
        progress={null}
        onProgressChange={vi.fn()}
        onActiveStepChange={onActiveStepChange}
      />,
    );
    expect(screen.getByTestId('step-runner-position').textContent).toBe('Prerequisites · 0 of 8');
    expect(screen.getByTestId('step-runner-prerequisites')).toBeTruthy();
    expect(onActiveStepChange).toHaveBeenLastCalledWith(null, 0);
    expect(screen.getByTestId('step-runner-prev').hasAttribute('disabled')).toBe(true);

    fireEvent.click(screen.getByTestId('step-runner-next'));
    expect(screen.getByTestId('step-runner-position').textContent).toBe('Step 1 of 8');
    expect(screen.getByTestId('step-runner-title').textContent).toBe('Long Context Video Ingestion');
    expect(player.seekTo).toHaveBeenCalledWith(102, { autoplay: true });
    expect(window.location.hash).toBe('#step-1');
    expect(onActiveStepChange).toHaveBeenLastCalledWith(
      expect.objectContaining({ source: { kind: 'requirement', id: 'REQ-01' } }),
      1,
    );
    expect(screen.getByTestId('step-runner-kind').textContent).toBe('Action');
    expect(screen.getByTestId('step-runner-range').textContent).toContain('1:42–2:28');
    expect(screen.getByTestId('step-runner-verification').textContent).toContain('no explicit check');
    expect(screen.queryByTestId('step-runner-keyframe')).toBeNull();

    fireEvent.click(screen.getByTestId('step-runner-prev'));
    expect(screen.getByTestId('step-runner-position').textContent).toBe('Prerequisites · 0 of 8');
    expect(window.location.hash).toBe('#step-0');
  });

  it('cues without playing when the autoplay toggle is off and pauses at the clip end when on', () => {
    const player = makePlayer();
    const view = render(
      <StepRunner runbook={runbook} player={player} progress={null} onProgressChange={vi.fn()} />,
    );
    const toggle = screen.getByTestId('step-runner-autoplay') as HTMLInputElement;
    expect(toggle.checked).toBe(true);
    fireEvent.click(toggle);
    expect(toggle.checked).toBe(false);
    fireEvent.change(screen.getByTestId('step-runner-jump'), { target: { value: '2' } });
    expect(player.seekTo).toHaveBeenLastCalledWith(311, { autoplay: false });

    // Turn autoplay back on, go to step 3 (239–252) and cross the clip end twice.
    fireEvent.click(toggle);
    fireEvent.change(screen.getByTestId('step-runner-jump'), { target: { value: '3' } });
    expect(player.seekTo).toHaveBeenLastCalledWith(239, { autoplay: true });
    view.rerender(
      <StepRunner
        runbook={runbook}
        player={{ ...player, currentTime: 253, isPlaying: true }}
        progress={null}
        onProgressChange={vi.fn()}
      />,
    );
    expect(player.pause).toHaveBeenCalledTimes(1);
    fireEvent.click(screen.getByTestId('step-runner-seek'));
    view.rerender(
      <StepRunner
        runbook={runbook}
        player={{ ...player, currentTime: 239, isPlaying: true }}
        progress={null}
        onProgressChange={vi.fn()}
      />,
    );
    view.rerender(
      <StepRunner
        runbook={runbook}
        player={{ ...player, currentTime: 253, isPlaying: true }}
        progress={null}
        onProgressChange={vi.fn()}
      />,
    );
    expect(player.pause).toHaveBeenCalledTimes(2);
  });

  it('shows which step is playing and lets the user jump without re-seeking', () => {
    const player = makePlayer({ currentTime: 407, isPlaying: true });
    render(<StepRunner runbook={runbook} player={player} progress={null} onProgressChange={vi.fn()} />);
    const chip = screen.getByTestId('step-runner-playing');
    expect(chip.textContent).toContain('Step 8');
    fireEvent.click(within(chip).getByRole('button', { name: /jump/i }));
    expect(screen.getByTestId('step-runner-position').textContent).toBe('Step 8 of 8');
    expect(player.seekTo).not.toHaveBeenCalled();
    expect(screen.getByTestId('step-runner-next').hasAttribute('disabled')).toBe(true);
  });

  it('persists prerequisite toggles and step completion through onProgressChange', () => {
    const onProgressChange = vi.fn<(progress: RunbookProgress) => void>();
    const { rerender } = render(
      <StepRunner runbook={runbook} player={makePlayer()} progress={null} onProgressChange={onProgressChange} />,
    );
    const prereq = screen.getAllByTestId('step-runner-prereq-toggle')[0] as HTMLInputElement;
    expect(prereq.checked).toBe(false);
    fireEvent.click(prereq);
    expect(onProgressChange).toHaveBeenLastCalledWith(
      expect.objectContaining({ version: 1, checkedPrerequisites: [runbook.prerequisites[0].id] }),
    );
    const saved = onProgressChange.mock.calls.at(-1)?.[0] ?? null;
    rerender(
      <StepRunner runbook={runbook} player={makePlayer()} progress={saved} onProgressChange={onProgressChange} />,
    );
    expect((screen.getAllByTestId('step-runner-prereq-toggle')[0] as HTMLInputElement).checked).toBe(true);
    expect(screen.getByTestId('step-runner-progress').textContent).toContain('1 / 5 prerequisites');

    fireEvent.click(screen.getByTestId('step-runner-next'));
    fireEvent.click(screen.getByTestId('step-runner-complete'));
    expect(onProgressChange).toHaveBeenLastCalledWith(
      expect.objectContaining({ completedSteps: [runbook.steps[0].id] }),
    );
    expect(screen.getByText(/local note, not evidence/i)).toBeTruthy();
  });

  it('disables seeking and says so when a step has no verified timestamp or the player is not this video', () => {
    const pack = runbookPackFixture();
    pack.requirements = [{ id: 'REQ-99', title: 'Rotate the quarterly budget spreadsheet', detail: 'Unrelated.' }];
    pack.action_items = [];
    const orphanRunbook = compileRunbook({ pack });
    render(<StepRunner runbook={orphanRunbook} player={makePlayer()} progress={null} onProgressChange={vi.fn()} />);
    fireEvent.click(screen.getByTestId('step-runner-next'));
    expect(screen.getByTestId('step-runner-range').textContent).toMatch(/No verified timestamp/);
    expect(screen.queryByTestId('step-runner-seek')).toBeNull();
    cleanup();
    // The hash restores the step on remount; start the second scenario from a clean URL.
    window.history.replaceState(null, '', '/studio');

    render(<StepRunner runbook={runbook} player={null} progress={null} onProgressChange={vi.fn()} />);
    fireEvent.click(screen.getByTestId('step-runner-next'));
    expect(screen.getByTestId('step-runner-range').textContent).toContain('1:42–2:28');
    expect(screen.getByTestId('step-runner-seek').hasAttribute('disabled')).toBe(true);
  });

  it('restores the step from the URL hash on mount and clamps out-of-range hashes', () => {
    window.history.replaceState(null, '', '/studio#step-4');
    const player = makePlayer();
    const view = render(
      <StepRunner runbook={runbook} player={player} progress={null} onProgressChange={vi.fn()} />,
    );
    expect(screen.getByTestId('step-runner-position').textContent).toBe('Step 4 of 8');
    // Restoring from the hash is a reference jump, not a playback command.
    expect(player.seekTo).not.toHaveBeenCalled();
    view.unmount();

    window.history.replaceState(null, '', '/studio#step-99');
    render(<StepRunner runbook={runbook} player={player} progress={null} onProgressChange={vi.fn()} />);
    expect(screen.getByTestId('step-runner-position').textContent).toBe('Step 8 of 8');
  });

  it('raises the active step for troubleshooting and renders a code step with its snippet', () => {
    const onTroubleshoot = vi.fn();
    render(
      <StepRunner
        runbook={runbook}
        player={makePlayer()}
        progress={null}
        onProgressChange={vi.fn()}
        onTroubleshoot={onTroubleshoot}
      />,
    );
    fireEvent.change(screen.getByTestId('step-runner-jump'), { target: { value: '5' } });
    expect(screen.getByTestId('step-runner-kind').textContent).toBe('Code snippet');
    expect(screen.getByTestId('step-runner-snippet').textContent).toContain('export function Content');
    fireEvent.click(screen.getByTestId('step-runner-troubleshoot'));
    expect(onTroubleshoot).toHaveBeenCalledWith(expect.objectContaining({ source: { kind: 'requirement', id: 'REQ-05' } }));
  });
});

describe('StudioRunbookPane', () => {
  it('switches between the step runner and the full RUNBOOK.md reference view', () => {
    render(
      <StudioRunbookPane runbook={runbook} player={makePlayer()} progress={null} onProgressChange={vi.fn()} />,
    );
    expect(screen.getByTestId('step-runner')).toBeTruthy();
    fireEvent.click(screen.getByTestId('studio-runbook-view-markdown'));
    const markdown = screen.getByTestId('studio-runbook-markdown');
    expect(markdown.textContent).toContain('# Runbook — auJzb1D-fag');
    expect(markdown.textContent).toContain('## Step 2 — Video Summarization & Analysis [5:11–5:28]');
    expect(screen.getByTestId('studio-runbook-download').getAttribute('download')).toBe('RUNBOOK.md');
    fireEvent.click(screen.getByTestId('studio-runbook-view-runner'));
    expect(screen.getByTestId('step-runner')).toBeTruthy();
  });

  it('renders an honest empty state for a pack without steps', () => {
    const pack = runbookPackFixture();
    pack.requirements = [];
    pack.action_items = [];
    pack.stack = { tools: [] };
    render(
      <StudioRunbookPane
        runbook={compileRunbook({ pack })}
        player={makePlayer()}
        progress={null}
        onProgressChange={vi.fn()}
      />,
    );
    expect(screen.getByTestId('studio-runbook-empty').textContent).toMatch(/no runbook steps/i);
  });
});
