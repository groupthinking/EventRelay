// @vitest-environment jsdom
import React from 'react';
import { act, cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import OneLoopStudio from '@/components/OneLoopStudio';
import { useDashboardStore, type Video } from '@/store/dashboard-store';
import { pollVideoToActions, startVideoToActions } from '@/lib/studio-workflow';
import { reviewPackFixture } from '@/test/grounded-spec-fixture';

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
  useSearchParams: () => new URLSearchParams(),
}));
vi.mock('next-auth/react', () => ({ useSession: () => ({ data: null, status: 'unauthenticated' }) }));
vi.mock('@/lib/studio-workflow', () => ({ startVideoToActions: vi.fn(), pollVideoToActions: vi.fn() }));
vi.mock('@/components/Nav', () => ({ default: () => null }));
vi.mock('@/app/studio/actions', () => ({ openGitHubPrsForApprovedSpecs: vi.fn() }));
vi.mock('@/components/studio/StudioBoundTasks', () => ({ default: () => <div>Bound tasks</div> }));
vi.mock('@/lib/use-youtube-player', () => ({
  useYouTubePlayer: () => ({ containerRef: { current: null }, ready: true, failed: false, seekTo: vi.fn() }),
}));

type PollResult = Awaited<ReturnType<typeof pollVideoToActions>>;

function analyzedVideo(): Video {
  const pack = reviewPackFixture();
  return {
    id: 'saved-row', title: 'Analyzed video', url: pack.source_url,
    status: 'complete', progress: 100, runId: 'run-original', transcript: 'Source transcript.',
    videoPack: {
      version: pack.version, packId: pack.id, videoId: pack.video_id,
      sourceUrl: pack.source_url, sourceHash: pack.provenance.source_hash, pack,
    },
  };
}

function result(video: Video, label: string): PollResult {
  return {
    ok: true, status: 200, runId: video.runId!, runStatus: 'completed',
    result: {
      url: video.url, transcriptChars: 18, actionCount: 1,
      actions: [{ tool: 'review_action', status: 'proposed', result: label }],
    },
  };
}

function pendingPolls() {
  const finish: Array<(value: PollResult) => void> = [];
  vi.mocked(pollVideoToActions).mockImplementation(() => new Promise((resolve) => { finish.push(resolve); }));
  return finish;
}

function review() {
  fireEvent.click(screen.getByTestId('studio-act-button'));
}

beforeEach(() => {
  vi.stubGlobal('React', React);
  vi.spyOn(useDashboardStore.persist, 'rehydrate').mockImplementation(() => undefined);
  vi.mocked(pollVideoToActions).mockReset();
  vi.mocked(startVideoToActions).mockReset();
  useDashboardStore.setState({ videos: [], selectedVideoId: null });
});

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe('review-only actions remain bound to the current selection', () => {
  it('discards an earlier A response after selecting B, returning to A, and reviewing again', async () => {
    const rowA = analyzedVideo();
    const rowB: Video = { ...rowA, id: 'another-row', runId: 'another-run' };
    const finish = pendingPolls();
    useDashboardStore.setState({ videos: [rowA, rowB], selectedVideoId: rowA.id });
    render(<OneLoopStudio showAgentWorkflowUi />);
    review();
    act(() => useDashboardStore.setState({ selectedVideoId: rowB.id }));
    act(() => useDashboardStore.setState({ selectedVideoId: rowA.id }));
    review();
    expect(finish).toHaveLength(2);

    await act(async () => { finish[0](result(rowA, 'Stale first review')); });
    expect(screen.getByTestId('studio-act-button').hasAttribute('disabled')).toBe(true);
    expect(screen.getByTestId('studio-ide-status').textContent).toMatch(/loading proposed actions/i);
    fireEvent.click(screen.getByRole('tab', { name: 'Intent' }));
    expect(screen.queryByText('Stale first review')).toBeNull();

    await act(async () => { finish[1](result(rowA, 'Current second review')); });
    expect(screen.getByText('Current second review')).toBeTruthy();
    expect(startVideoToActions).not.toHaveBeenCalled();
  });

  it.each(['run', 'pack', 'source'] as const)('discards a stale response after the same row changes its %s identity', async (changed) => {
    const original = analyzedVideo();
    const updated: Video = {
      ...original,
      runId: changed === 'run' ? 'run-replacement' : original.runId,
      videoPack: {
        ...original.videoPack!,
        packId: changed === 'pack' ? 'pack-replacement' : original.videoPack!.packId,
        sourceHash: changed === 'source' ? 'b'.repeat(64) : original.videoPack!.sourceHash,
      },
    };
    const finish = pendingPolls();
    useDashboardStore.setState({ videos: [original], selectedVideoId: original.id });
    render(<OneLoopStudio showAgentWorkflowUi />);
    review();
    act(() => useDashboardStore.setState({ videos: [updated] }));
    review();

    await act(async () => { finish[0](result(original, 'Stale original identity')); });
    expect(screen.getByTestId('studio-act-button').hasAttribute('disabled')).toBe(true);
    fireEvent.click(screen.getByRole('tab', { name: 'Intent' }));
    expect(screen.queryByText('Stale original identity')).toBeNull();

    await act(async () => { finish[1](result(updated, 'Current replacement identity')); });
    expect(screen.getByText('Current replacement identity')).toBeTruthy();
    expect(startVideoToActions).not.toHaveBeenCalled();
  });

  it('does not poll or start a workflow when the feature is disabled', () => {
    const video = analyzedVideo();
    useDashboardStore.setState({ videos: [video], selectedVideoId: video.id });
    render(<OneLoopStudio showAgentWorkflowUi={false} />);
    expect(screen.queryByTestId('studio-act-button')).toBeNull();
    expect(pollVideoToActions).not.toHaveBeenCalled();
    expect(startVideoToActions).not.toHaveBeenCalled();
  });

  it.each(['videoId', 'sourceUrl'] as const)('holds review when the pack citation %s belongs to another video', (mismatch) => {
    const video = analyzedVideo();
    video.videoPack = {
      ...video.videoPack!,
      ...(mismatch === 'videoId' ? { videoId: 'jNQXAC9IVRw' } : { sourceUrl: 'https://www.youtube.com/watch?v=jNQXAC9IVRw' }),
    };
    useDashboardStore.setState({ videos: [video], selectedVideoId: video.id });
    render(<OneLoopStudio showAgentWorkflowUi />);
    expect(screen.getByTestId('studio-act-button').hasAttribute('disabled')).toBe(true);
    review();
    expect(pollVideoToActions).not.toHaveBeenCalled();
    expect(startVideoToActions).not.toHaveBeenCalled();
  });

  it('invalidates an in-flight review when the feature is disabled before being enabled again', async () => {
    const video = analyzedVideo();
    const finish = pendingPolls();
    useDashboardStore.setState({ videos: [video], selectedVideoId: video.id });
    const view = render(<OneLoopStudio showAgentWorkflowUi />);
    review();
    view.rerender(<OneLoopStudio showAgentWorkflowUi={false} />);
    await act(async () => { finish[0](result(video, 'Review completed after disabling')); });
    view.rerender(<OneLoopStudio showAgentWorkflowUi />);
    fireEvent.click(screen.getByRole('tab', { name: 'Intent' }));
    expect(screen.queryByText('Review completed after disabling')).toBeNull();
    expect(startVideoToActions).not.toHaveBeenCalled();
  });
});
