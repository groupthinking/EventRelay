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

describe('OneLoopStudio job strip and failed-pack transcript', () => {
  it('links the idle job strip to /studio and keeps the transcript idle', () => {
    render(<OneLoopStudio showAgentWorkflowUi={false} />);

    const selfLink = screen.getByTestId('studio-job-self-link');
    expect(selfLink.getAttribute('href')).toBe('/studio');
    expect(selfLink.textContent).toBe('/studio');
    expect(screen.getByTestId('studio-primary-job-strip').textContent).not.toContain('/d/');
    expect(screen.getByTestId('studio-transcript-body').textContent).toBe('Nothing yet.');
    expect(screen.queryByText('/d/{videoId}')).toBeNull();
  });

  it('names the stored YouTube id after a pack exists', async () => {
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

    expect(screen.getByTestId('studio-job-video-id').textContent).toBe('auJzb1D-fag');
    expect(screen.queryByTestId('studio-job-self-link')).toBeNull();
    expect(screen.getByTestId('studio-primary-job-strip').textContent).not.toContain('/d/');
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

    expect(screen.getByTestId('studio-transcript-body').textContent).toBe(extractError);
    expect(screen.queryByText('Nothing yet.')).toBeNull();
    expect(screen.getByTestId('studio-workbench-empty').textContent).toContain(extractError);
  });

  it('shows the stored pack cite and transcript without a combobox change', async () => {
    const { reviewPackFixture } = await import('@/test/grounded-spec-fixture');
    const pack = reviewPackFixture();
    useDashboardStore.setState({
      videos: [
        {
          ...idleVideo,
          status: 'processing',
          progress: 12,
          transcript: '',
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

    expect(screen.getByTestId('video-pack-citation').textContent).toContain('cite:youtube:auJzb1D-fag');
    expect(screen.getByTestId('video-pack-citation').textContent).toContain(pack.provenance.source_hash);
    expect(screen.getByTestId('studio-job-video-id').textContent).toBe('auJzb1D-fag');
    expect(screen.getByTestId('studio-transcript-body').textContent).toBe(
      'Select a task to mark it complete.',
    );
    expect(screen.getAllByRole('status')[0]?.textContent ?? '').not.toContain('Building transcript');
  });

  it('follows the stored pack row after a combobox selection', async () => {
    const { reviewPackFixture } = await import('@/test/grounded-spec-fixture');
    const pack = reviewPackFixture();
    const otherTranscript = 'Second stored pack transcript line.';
    const otherPack = {
      ...pack,
      video_id: 'pBsT6v-ciO8',
      source_url: 'https://www.youtube.com/watch?v=pBsT6v-ciO8',
      transcript: {
        language: 'en',
        full_text: otherTranscript,
        segments: [{ idx: 0, start_s: 1, end_s: 2, text: otherTranscript }],
      },
    };
    useDashboardStore.setState({
      videos: [
        {
          ...idleVideo,
          transcript: '',
          videoPack: {
            packId: pack.id,
            videoId: pack.video_id,
            sourceUrl: pack.source_url,
            sourceHash: pack.provenance.source_hash,
            version: pack.version,
            pack,
          },
        },
        {
          id: 'row-other',
          title: 'Other stored pack',
          url: 'https://www.youtube.com/watch?v=pBsT6v-ciO8',
          status: 'complete',
          progress: 100,
          transcript: '',
          videoPack: {
            packId: otherPack.id,
            videoId: otherPack.video_id,
            sourceUrl: otherPack.source_url,
            sourceHash: otherPack.provenance.source_hash,
            version: otherPack.version,
            pack: otherPack,
          },
        },
      ],
      selectedVideoId: null,
    });

    render(<OneLoopStudio showAgentWorkflowUi={false} />);

    expect(useDashboardStore.getState().selectedVideoId).toBe(idleVideo.id);
    expect(screen.getByTestId('studio-job-video-id').textContent).toBe('auJzb1D-fag');
    expect(screen.getByTestId('studio-transcript-body').textContent).toBe(
      'Select a task to mark it complete.',
    );

    fireEvent.change(screen.getByRole('combobox', { name: 'Stored packs' }), {
      target: { value: 'row-other' },
    });

    expect(useDashboardStore.getState().selectedVideoId).toBe('row-other');
    expect(screen.getByTestId('studio-job-video-id').textContent).toBe('pBsT6v-ciO8');
    expect(screen.getByTestId('video-pack-citation').textContent).toContain('cite:youtube:pBsT6v-ciO8');
    expect(screen.getByTestId('studio-transcript-body').textContent).toBe(otherTranscript);
    expect(screen.getAllByRole('status')[0]?.textContent ?? '').not.toContain('Building transcript');
  });
});
