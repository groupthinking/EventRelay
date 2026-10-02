// @vitest-environment jsdom
import React from 'react';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import OneLoopStudio from '@/components/OneLoopStudio';
import { useDashboardStore, type Video } from '@/store/dashboard-store';

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
  useSearchParams: () => new URLSearchParams(),
  usePathname: () => '/studio',
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

const idleVideo: Video = {
  id: 'row-job-strip',
  title: 'Job strip',
  url: 'https://www.youtube.com/watch?v=auJzb1D-fag',
  status: 'complete',
  progress: 100,
};

beforeEach(() => {
  vi.stubGlobal('React', React);
  vi.spyOn(useDashboardStore.persist, 'rehydrate').mockImplementation(() => undefined);
  useDashboardStore.setState({ videos: [], selectedVideoId: null });
});

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe('OneLoopStudio IDE status and transcript', () => {
  it('shows idle status in the toolbar when no pack is stored', () => {
    render(<OneLoopStudio showAgentWorkflowUi={false} />);

    expect(screen.getByTestId('studio-ide-shell')).toBeTruthy();
    expect(screen.getByTestId('studio-ide-status')).toBeTruthy();
    // Transcript tab shows the idle state.
    expect(screen.getByTestId('studio-ide-output-tab-transcript')).toBeTruthy();
  });

  it('names the stored pack in the video pane after a pack exists', async () => {
    const { reviewPackFixture } = await import('@/test/grounded-spec-fixture');
    const pack = reviewPackFixture();
    useDashboardStore.setState({
      videos: [
        {
          ...idleVideo,
          transcript: 'Select a task to mark it complete.',
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
      selectedVideoId: idleVideo.id,
    });

    render(<OneLoopStudio showAgentWorkflowUi={false} />);

    expect(screen.getByTestId('studio-build-live-button').getAttribute('title')).toBe(
      'Compile the stored Video Pack for auJzb1D-fag.',
    );
    expect(screen.getByTestId('studio-build-live-button').getAttribute('title')).not.toContain('/d/');
  });

  it('shows the extract error instead of the idle transcript after a failed pack', () => {
    const extractError = 'Gemini 3.8 Flash returned no extracted spec content.';
    useDashboardStore.setState({
      videos: [
        {
          ...idleVideo,
          status: 'failed',
          transcript: '',
          failure: {
            stage: 'analysis',
            message: extractError,
            retryable: true,
            failedAt: '2026-09-23T00:00:00.000Z',
          },
        },
      ],
      selectedVideoId: idleVideo.id,
    });

    render(<OneLoopStudio showAgentWorkflowUi={false} />);

    fireEvent.click(screen.getByTestId('studio-ide-output-tab-transcript'));
    expect(screen.getByTestId('studio-transcript-body').textContent).toBe(extractError);
    expect(screen.queryByText('Nothing yet.')).toBeNull();
  });
});
