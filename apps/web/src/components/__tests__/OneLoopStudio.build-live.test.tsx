// @vitest-environment jsdom
import React from 'react';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import OneLoopStudio from '@/components/OneLoopStudio';
import { useDashboardStore, type Video } from '@/store/dashboard-store';
import * as packBuildLive from '@/lib/pack-build-live-client';

const navigation = { push: vi.fn() };

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: navigation.push }),
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
  id: 'row-1',
  title: 'Build live honesty',
  url: 'https://www.youtube.com/watch?v=XYMcBrFSJ4c',
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

describe('OneLoopStudio Build live honesty (B3b)', () => {
  it('renders workbench empty UI when no pack is stored', () => {
    render(<OneLoopStudio showAgentWorkflowUi={false} />);
    expect(screen.getByTestId('studio-workbench-empty')).toBeTruthy();
    expect(screen.getByText(/video pack not stored/i)).toBeTruthy();
  });

  it('shows recovery CTAs when Build live fails for a missing pack', async () => {
    vi.spyOn(packBuildLive, 'verifyPackBuildLive').mockResolvedValue({
      ok: false,
      message: 'No stored Video Pack for this video. Run analysis on this URL, then try Build live again.',
      reasonCode: 'HOSTED_PACK_NOT_FOUND',
    });
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
    fireEvent.click(screen.getByTestId('studio-build-live-button'));

    await waitFor(() => {
      expect(screen.getByTestId('studio-build-live-failure')).toBeTruthy();
    });
    expect(screen.getByTestId('studio-build-live-recovery-rerun_analysis')).toBeTruthy();
    expect(screen.queryByText(/\/api\/video\/pack/i)).toBeNull();
  });
});

describe('OneLoopStudio Build live Setup→Result (D1)', () => {
  it('renders a success receipt card with /d/{videoId} after verified Build live', async () => {
    const { reviewPackFixture } = await import('@/test/grounded-spec-fixture');
    const pack = reviewPackFixture();
    const youtubeId = pack.video_id;
    const liveUrl = `https://uvai.io/d/${youtubeId}`;
    vi.spyOn(packBuildLive, 'verifyPackBuildLive').mockResolvedValue({
      ok: true,
      liveUrl,
      reasonCode: 'FACTORY_DELIVER_READY',
    });
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
    fireEvent.click(screen.getByTestId('studio-build-live-button'));

    await waitFor(() => {
      expect(screen.getByTestId('studio-pack-build-live-result')).toBeTruthy();
    });
    expect(screen.getByTestId('studio-pack-build-live-state').textContent).toBe('Ready');
    expect(screen.getByTestId('studio-pack-build-live-video-id').textContent).toBe(youtubeId);
    const artifactLink = screen.getByTestId('studio-pack-build-live-artifact-link');
    expect(artifactLink.getAttribute('href')).toBe(`/d/${youtubeId}`);
    const proCta = screen.getByTestId('studio-pack-build-live-pro-cta');
    expect(proCta.getAttribute('href')).toBe('/#get-pro');
    expect(proCta.textContent).toMatch(/unlock workflow pro/i);
    expect(screen.getByTestId('studio-pack-build-live-reason-code').textContent).toBe(
      'FACTORY_DELIVER_READY',
    );
    expect(screen.queryByTestId('studio-build-live-failure')).toBeNull();
  });

  it('keeps the Ready receipt card visible after a later failed retry for the same video', async () => {
    const { reviewPackFixture } = await import('@/test/grounded-spec-fixture');
    const pack = reviewPackFixture();
    const youtubeId = pack.video_id;
    const liveUrl = `https://uvai.io/d/${youtubeId}`;
    vi.spyOn(packBuildLive, 'verifyPackBuildLive')
      .mockResolvedValueOnce({
        ok: true,
        liveUrl,
        reasonCode: 'FACTORY_DELIVER_READY',
      })
      .mockResolvedValueOnce({
        ok: false,
        message: 'No stored Video Pack for this video. Run analysis on this URL, then try Build live again.',
        reasonCode: 'HOSTED_PACK_NOT_FOUND',
      });
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
    fireEvent.click(screen.getByTestId('studio-build-live-button'));

    await waitFor(() => {
      expect(screen.getByTestId('studio-pack-build-live-result')).toBeTruthy();
    });
    expect(screen.getByTestId('studio-pack-build-live-video-id').textContent).toBe(youtubeId);

    fireEvent.click(screen.getByTestId('studio-build-live-button'));

    await waitFor(() => {
      expect(screen.getByTestId('studio-build-live-failure')).toBeTruthy();
    });
    expect(screen.getByTestId('studio-pack-build-live-result')).toBeTruthy();
    expect(screen.getByTestId('studio-pack-build-live-video-id').textContent).toBe(youtubeId);
    expect(screen.getByTestId('studio-pack-build-live-reason-code').textContent).toBe(
      'FACTORY_DELIVER_READY',
    );
  });
});
