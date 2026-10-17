// @vitest-environment jsdom
import React from 'react';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import OneLoopStudio from '@/components/OneLoopStudio';
import { useDashboardStore, type Video } from '@/store/dashboard-store';
import { PBST6V_VIDEO_ID, pbst6vPackFixture } from '@/lib/__fixtures__/pbst6v-cio8-runbook';

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
  const pack = pbst6vPackFixture();
  return {
    id: 'row-runbook',
    title: 'SeaDance outreach podcast',
    url: `https://www.youtube.com/watch?v=${PBST6V_VIDEO_ID}`,
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
  it('opens Deliverables on the Runbook step runner for a stored pack', () => {
    render(<OneLoopStudio showAgentWorkflowUi={false} />);
    const tab = screen.getByTestId('studio-ide-output-tab-runbook');
    expect(tab.getAttribute('aria-selected')).toBe('true');
    expect(screen.getByTestId('studio-runbook-pane')).toBeTruthy();
    expect(screen.getByTestId('step-runner-position').textContent).toBe('Prerequisites · 0 of 7');
    // The seven extraction tabs are still there.
    expect(screen.getByTestId('studio-ide-output-tab-events')).toBeTruthy();
    expect(screen.getByTestId('studio-ide-output-tab-transcript')).toBeTruthy();
  });

  it('Next seeks the player, updates the hash, and re-grounds the chat to the active step', async () => {
    render(<OneLoopStudio showAgentWorkflowUi={false} />);
    expect(screen.queryByTestId('studio-ide-chat-step')).toBeNull();

    fireEvent.click(screen.getByTestId('step-runner-next'));

    expect(player.seekTo).toHaveBeenCalledWith(247, { autoplay: true });
    expect(window.location.hash).toBe('#step-1');
    const chip = await screen.findByTestId('studio-ide-chat-step');
    expect(chip.textContent).toContain('Step 1');
    expect(chip.textContent).toContain('AI Video Generation Tooling');
    expect((screen.getByTestId('studio-ide-chat-input') as HTMLInputElement).placeholder).toMatch(/Step 1/);

    // Clearing the chip returns to whole-pack grounding until the next step change.
    fireEvent.click(screen.getByRole('button', { name: /whole pack/i }));
    expect(screen.queryByTestId('studio-ide-chat-step')).toBeNull();
    fireEvent.click(screen.getByTestId('step-runner-next'));
    expect((await screen.findByTestId('studio-ide-chat-step')).textContent).toContain('Step 2');
  });

  it('sends the active step with the chat request and focuses the composer from Troubleshoot', async () => {
    const fetchMock = vi.fn(async () =>
      new Response(JSON.stringify({ answer: 'Re-watch 4:07.' }), {
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

    fireEvent.change(input, { target: { value: 'SeaDance returns a 403' } });
    fireEvent.click(screen.getByTestId('studio-ide-chat-send'));
    await screen.findByText('Re-watch 4:07.');

    const [, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit];
    const body = JSON.parse(String(init.body)) as {
      step?: { id: string; step_number: number; total_steps: number; timestamp_range: [number, number] | null };
      video_id?: string;
    };
    expect(body.video_id).toBe(PBST6V_VIDEO_ID);
    expect(body.step?.id).toBe('rb-req-01');
    expect(body.step?.step_number).toBe(1);
    expect(body.step?.total_steps).toBe(7);
    expect(body.step?.timestamp_range).toEqual([247, 254.5]);
  });

  it('persists runbook progress on the selected video row', () => {
    render(<OneLoopStudio showAgentWorkflowUi={false} />);
    fireEvent.click(screen.getAllByTestId('step-runner-prereq-toggle')[0]);
    fireEvent.click(screen.getByTestId('step-runner-next'));
    fireEvent.click(screen.getByTestId('step-runner-complete'));
    const row = useDashboardStore.getState().videos[0];
    expect(row.runbookProgress?.version).toBe(1);
    expect(row.runbookProgress?.checkedPrerequisites).toEqual(['prereq-tool-seadance-2-5']);
    expect(row.runbookProgress?.completedSteps).toEqual(['rb-req-01']);
  });

  it('does not drive the player when the loaded video is not the pack video', () => {
    render(<OneLoopStudio showAgentWorkflowUi={false} />);
    fireEvent.change(screen.getByLabelText('YouTube URL'), {
      target: { value: 'https://www.youtube.com/watch?v=auJzb1D-fag' },
    });
    fireEvent.click(screen.getByTestId('step-runner-next'));
    expect(player.seekTo).not.toHaveBeenCalled();
    expect(screen.getByTestId('step-runner-seek').hasAttribute('disabled')).toBe(true);
  });
});
