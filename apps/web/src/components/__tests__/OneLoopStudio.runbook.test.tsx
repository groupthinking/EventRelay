// @vitest-environment jsdom
import React from 'react';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import OneLoopStudio from '@/components/OneLoopStudio';
import { useDashboardStore, type Video } from '@/store/dashboard-store';
import { RUNBOOK_VIDEO_ID, runbookPackFixture } from '@/lib/__fixtures__/aujzb1d-fag-runbook';

const player = vi.hoisted(() => ({
  seekTo: vi.fn(),
  pause: vi.fn(),
  play: vi.fn(),
}));

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn() }),
  useSearchParams: () => new URLSearchParams(),
}));
vi.mock('@/components/Nav', () => ({ default: () => null }));
vi.mock('@/app/studio/actions', () => ({ openGitHubPrsForApprovedSpecs: vi.fn() }));
vi.mock('@/lib/use-youtube-player', () => ({
  useYouTubePlayer: () => ({
    containerRef: () => undefined,
    ready: true,
    failed: false,
    currentTime: 0,
    duration: 474,
    isPlaying: false,
    seekTo: player.seekTo,
    pause: player.pause,
    play: player.play,
  }),
}));

function seedPack(): Video {
  const pack = runbookPackFixture();
  return {
    id: 'row-runbook',
    title: 'Google AI Studio demonstration',
    url: `https://www.youtube.com/watch?v=${RUNBOOK_VIDEO_ID}`,
    status: 'complete',
    progress: 100,
    transcript: pack.transcript.full_text,
    videoPack: {
      packId: pack.id,
      videoId: pack.video_id,
      sourceUrl: pack.source_url,
      sourceHash: pack.provenance.source_hash,
      version: pack.version,
      pack,
    },
  };
}

beforeEach(() => {
  vi.stubGlobal('React', React);
  vi.spyOn(useDashboardStore.persist, 'rehydrate').mockImplementation(() => undefined);
  window.history.replaceState(null, '', '/studio');
  window.localStorage.clear();
  const row = seedPack();
  useDashboardStore.setState({ videos: [row], selectedVideoId: row.id });
});

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
  player.seekTo.mockReset();
  player.pause.mockReset();
  player.play.mockReset();
});

describe('OneLoopStudio Deliverables → Runbook', () => {
  it('preserves the initial step hash while a stored pack is auto-selected', async () => {
    const row = seedPack();
    useDashboardStore.setState({ videos: [row], selectedVideoId: null });
    window.history.replaceState(null, '', '/studio#step-3');
    render(<OneLoopStudio showAgentWorkflowUi={false} />);
    await waitFor(() => expect(useDashboardStore.getState().selectedVideoId).toBe(row.id));
    expect(window.location.hash).toBe('#step-3');
    expect((await screen.findByTestId('step-runner-position')).textContent).toBe('Step 3 of 8');
  });

  it('opens Deliverables on the Runbook step runner for a stored pack', () => {
    render(<OneLoopStudio showAgentWorkflowUi={false} />);
    const tab = screen.getByTestId('studio-ide-output-tab-runbook');
    expect(tab.getAttribute('aria-selected')).toBe('true');
    expect(screen.getByTestId('studio-runbook-pane')).toBeTruthy();
    expect(screen.getByTestId('step-runner-position').textContent).toBe('Prerequisites · 0 of 8');
    // The seven extraction tabs are still there.
    expect(screen.getByTestId('studio-ide-output-tab-events')).toBeTruthy();
    expect(screen.getByTestId('studio-ide-output-tab-transcript')).toBeTruthy();
  });

  it('Next seeks the player, updates the hash, and re-grounds the chat to the active step', async () => {
    render(<OneLoopStudio showAgentWorkflowUi={false} />);
    expect(screen.queryByTestId('studio-ide-chat-step')).toBeNull();

    fireEvent.click(screen.getByTestId('step-runner-next'));

    expect(player.seekTo).toHaveBeenCalledWith(102, { autoplay: true });
    expect(window.location.hash).toBe('#step-1');
    const chip = await screen.findByTestId('studio-ide-chat-step');
    expect(chip.textContent).toContain('Step 1');
    expect(chip.textContent).toContain('Long Context Video Ingestion');
    expect((screen.getByTestId('studio-ide-chat-input') as HTMLInputElement).placeholder).toMatch(/Step 1/);

    // Clearing the chip returns to whole-pack grounding until the next step change.
    fireEvent.click(screen.getByRole('button', { name: /whole pack/i }));
    expect(screen.queryByTestId('studio-ide-chat-step')).toBeNull();
    fireEvent.click(screen.getByTestId('step-runner-next'));
    expect((await screen.findByTestId('studio-ide-chat-step')).textContent).toContain('Step 2');
  });

  it('sends the active step with the chat request and focuses the composer from Troubleshoot', async () => {
    const fetchMock = vi.fn(async () =>
      new Response(JSON.stringify({ answer: 'Re-watch 1:42.' }), {
        status: 200,
        headers: { 'content-type': 'application/json' },
      }),
    );
    vi.stubGlobal('fetch', fetchMock);
    render(<OneLoopStudio showAgentWorkflowUi={false} />);

    fireEvent.click(screen.getByTestId('step-runner-next'));
    fireEvent.click(screen.getByTestId('step-runner-troubleshoot'));
    const input = screen.getByTestId('studio-ide-chat-input') as HTMLInputElement;
    await waitFor(() => expect(document.activeElement).toBe(input));

    fireEvent.change(input, { target: { value: 'The long video upload failed' } });
    fireEvent.click(screen.getByTestId('studio-ide-chat-send'));
    await screen.findByText('Re-watch 1:42.');

    const [, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit];
    const body = JSON.parse(String(init.body)) as {
      step?: { id: string; step_number: number; total_steps: number; timestamp_range: [number, number] | null };
      video_id?: string;
    };
    expect(body.video_id).toBe(RUNBOOK_VIDEO_ID);
    expect(body.step?.id).toBe('rb-req-01');
    expect(body.step?.step_number).toBe(1);
    expect(body.step?.total_steps).toBe(8);
    expect(body.step?.timestamp_range).toEqual([102, 148]);

    fireEvent.click(screen.getByTestId('step-runner-next'));
    await waitFor(() => expect(screen.queryByText('Re-watch 1:42.')).toBeNull());
    fireEvent.change(input, { target: { value: 'What is next?' } });
    fireEvent.click(screen.getByTestId('studio-ide-chat-send'));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2));
    const [, nextInit] = fetchMock.mock.calls[1] as unknown as [string, RequestInit];
    const nextBody = JSON.parse(String(nextInit.body)) as {
      step?: { id: string };
      history: Array<{ role: string; content: string }>;
    };
    expect(nextBody.step?.id).toBe('rb-req-02');
    expect(nextBody.history).toEqual([{ role: 'user', content: 'What is next?' }]);
  });

  it('persists runbook progress on the selected video row', () => {
    render(<OneLoopStudio showAgentWorkflowUi={false} />);
    fireEvent.click(screen.getAllByTestId('step-runner-prereq-toggle')[0]);
    fireEvent.click(screen.getByTestId('step-runner-next'));
    fireEvent.click(screen.getByTestId('step-runner-complete'));
    const row = useDashboardStore.getState().videos[0];
    expect(row.runbookProgress?.version).toBe(1);
    expect(row.runbookProgress?.checkedPrerequisites).toEqual(['prereq-tool-google-ai-studio']);
    expect(row.runbookProgress?.completedSteps).toEqual(['rb-req-01']);
  });

  it('does not drive the player when the loaded video is not the pack video', () => {
    render(<OneLoopStudio showAgentWorkflowUi={false} />);
    fireEvent.change(screen.getByLabelText('YouTube URL'), {
      target: { value: 'https://www.youtube.com/watch?v=jNQXAC9IVRw' },
    });
    fireEvent.click(screen.getByTestId('step-runner-next'));
    expect(player.seekTo).not.toHaveBeenCalled();
    expect(screen.getByTestId('step-runner-seek').hasAttribute('disabled')).toBe(true);
  });
});
