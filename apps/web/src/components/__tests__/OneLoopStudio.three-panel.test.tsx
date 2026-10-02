// @vitest-environment jsdom
import React from 'react';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import OneLoopStudio from '@/components/OneLoopStudio';
import { useDashboardStore, type Video } from '@/store/dashboard-store';

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn() }),
  useSearchParams: () => new URLSearchParams(),
}));
vi.mock('@/components/Nav', () => ({ default: () => null }));
vi.mock('@/app/studio/actions', () => ({ openGitHubPrsForApprovedSpecs: vi.fn() }));
vi.mock('@/lib/use-youtube-player', () => ({
  useYouTubePlayer: () => ({
    containerRef: { current: null },
    ready: false,
    failed: false,
    seekTo: vi.fn(),
  }),
}));

const baseVideo: Video = {
  id: 'row-ide',
  title: 'IDE shell',
  url: 'https://www.youtube.com/watch?v=auJzb1D-fag',
  status: 'complete',
  progress: 100,
  transcript: 'Enough transcript text for analysis ready state in Studio tests.',
};

beforeEach(() => {
  vi.stubGlobal('React', React);
  vi.spyOn(useDashboardStore.persist, 'rehydrate').mockImplementation(() => undefined);
  useDashboardStore.setState({ videos: [baseVideo], selectedVideoId: baseVideo.id });
});

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe('OneLoopStudio IDE shell', () => {
  it('renders the IDE shell with toolbar and three panes when idle', () => {
    render(<OneLoopStudio showAgentWorkflowUi={false} />);
    expect(screen.getByTestId('studio-ide-shell')).toBeTruthy();
    expect(screen.getByTestId('studio-ide-toolbar')).toBeTruthy();
    expect(screen.getByTestId('studio-ide-video-pane')).toBeTruthy();
    expect(screen.getByTestId('studio-ide-chat-pane')).toBeTruthy();
    expect(screen.getByTestId('studio-ide-output-pane')).toBeTruthy();
    expect(screen.getByTestId('studio-ide-splitter-left')).toBeTruthy();
    expect(screen.getByTestId('studio-ide-splitter-right')).toBeTruthy();
    // Toolbar carries the run + pack actions.
    expect(screen.getByTestId('studio-ide-run')).toBeTruthy();
    expect(screen.getByTestId('studio-ide-export')).toBeTruthy();
    expect(screen.getByTestId('studio-build-live-button')).toBeTruthy();
    expect(screen.getByTestId('studio-deploy-button')).toBeTruthy();
  });

  it('renders video, chat, and output panes when a stored Video Pack is selected', async () => {
    const { reviewPackFixture } = await import('@/test/grounded-spec-fixture');
    const pack = reviewPackFixture();
    useDashboardStore.setState({
      videos: [
        {
          ...baseVideo,
          videoPack: {
            packId: pack.id,
            videoId: pack.video_id,
            sourceUrl: pack.source_url,
            sourceHash: pack.provenance.source_hash,
            version: pack.version,
            pack,
          },
        },
      ],
      selectedVideoId: baseVideo.id,
    });

    render(<OneLoopStudio showAgentWorkflowUi={false} />);

    expect(screen.getByTestId('studio-ide-shell')).toBeTruthy();
    expect(screen.getByTestId('studio-ide-video-pane')).toBeTruthy();
    expect(screen.getByTestId('studio-ide-chat')).toBeTruthy();
    expect(screen.getByTestId('studio-ide-output')).toBeTruthy();
    // Chat composer is live (wired to /api/chat), not a preview stub.
    expect(screen.getByTestId('studio-ide-chat-input')).toBeTruthy();
    expect(screen.getByTestId('studio-ide-chat-send')).toBeTruthy();
    // Output pane shows the action-extraction tabs.
    expect(screen.getByTestId('studio-ide-output-tab-events')).toBeTruthy();
    expect(screen.getByTestId('studio-ide-output-tab-lingo')).toBeTruthy();
    expect(screen.getByTestId('studio-ide-output-tab-tools')).toBeTruthy();
    expect(screen.getByTestId('studio-ide-output-tab-intent')).toBeTruthy();
    expect(screen.getByTestId('studio-ide-output-tab-signals')).toBeTruthy();
  });

  it('shows a cancel button while a run is in flight', async () => {
    render(<OneLoopStudio showAgentWorkflowUi={false} />);
    const input = screen.getByLabelText('YouTube URL');
    fireEvent.change(input, { target: { value: 'https://www.youtube.com/watch?v=auJzb1D-fag' } });
    // Run is async; the cancel button appears once busy flips true.
    fireEvent.click(screen.getByTestId('studio-ide-run'));
    expect(await screen.findByTestId('studio-ide-cancel')).toBeTruthy();
  });
});
