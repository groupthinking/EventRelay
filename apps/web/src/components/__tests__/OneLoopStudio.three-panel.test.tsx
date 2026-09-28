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
  id: 'row-three-panel',
  title: 'Three panel parity',
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

describe('OneLoopStudio Result Ready three-panel shell (P1.7)', () => {
  it('does not render SaaS shell markers when idle with no stored pack', () => {
    render(<OneLoopStudio showAgentWorkflowUi={false} />);
    expect(screen.getByTestId('studio-workbench-empty')).toBeTruthy();
    expect(screen.queryByTestId('shell-nav-panel')).toBeNull();
    expect(screen.queryByTestId('saas-three-panel-shell')).toBeNull();
  });

  it('renders adjustable three-panel shell when a stored Video Pack is selected', async () => {
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

    expect(screen.queryByTestId('studio-workbench-empty')).toBeNull();
    expect(screen.getByTestId('saas-three-panel-shell')).toBeTruthy();
    expect(screen.getByTestId('shell-nav-panel')).toBeTruthy();
    expect(screen.getByTestId('shell-splitter-left')).toBeTruthy();
    expect(screen.getByTestId('shell-splitter-right')).toBeTruthy();
    expect(screen.getByTestId('shell-chat-panel')).toBeTruthy();
    expect(screen.getByTestId('shell-nav-collapse')).toBeTruthy();
    expect(screen.getByTestId('chat-cta-summarize')).toBeTruthy();
    expect(screen.getByTestId('chat-cta-extract')).toBeTruthy();
    expect(screen.getByTestId('chat-cta-open-d')).toBeTruthy();

    // Single-pane workbench: a tab bar picks one pane at a time. The default
    // pane is Video, so the grounded spec is NOT stacked on first paint.
    expect(screen.getByTestId('studio-workbench-tabs')).toBeTruthy();
    expect(screen.getByTestId('studio-workbench-tab-video').getAttribute('data-active')).toBe('true');
    expect(screen.queryByTestId('studio-result-ready-pane')).toBeNull();

    // Selecting the Spec tab swaps the single main pane to the grounded spec.
    fireEvent.click(screen.getByTestId('studio-workbench-tab-spec'));
    expect(screen.getByTestId('studio-result-ready-pane')).toBeTruthy();
    expect(screen.getByTestId('grounded-spec-review')).toBeTruthy();
  });
});
