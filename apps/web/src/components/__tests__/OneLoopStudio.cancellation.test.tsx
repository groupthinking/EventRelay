// @vitest-environment jsdom
import React from 'react';
import { act, cleanup, fireEvent, render, screen } from '@testing-library/react';
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
  useYouTubePlayer: () => ({ containerRef: { current: null }, ready: false, failed: false, seekTo: vi.fn() }),
}));

const originalProcessVideo = useDashboardStore.getState().processVideo;
const video: Video = {
  id: 'stored-analysis',
  title: 'Stored analysis',
  url: 'https://www.youtube.com/watch?v=auJzb1D-fag',
  status: 'complete',
  progress: 100,
  transcript: 'Enough source transcript for the existing analysis in these tests.',
};

beforeEach(() => {
  vi.stubGlobal('React', React);
  vi.spyOn(useDashboardStore.persist, 'rehydrate').mockImplementation(() => undefined);
  useDashboardStore.setState({ videos: [video], selectedVideoId: video.id });
});

afterEach(() => {
  cleanup();
  useDashboardStore.setState({ processVideo: originalProcessVideo });
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
  vi.useRealTimers();
});

describe('OneLoopStudio analysis cancellation', () => {
  it('releases the run controls immediately and explains the server boundary', async () => {
    const processVideo = vi.fn((_url: string, _opts?: { signal?: AbortSignal }) => new Promise<string>(() => {}));
    useDashboardStore.setState({ processVideo });
    render(<OneLoopStudio showAgentWorkflowUi={false} />);
    fireEvent.change(screen.getByLabelText('YouTube URL'), { target: { value: video.url } });
    fireEvent.click(screen.getByTestId('studio-ide-run'));
    expect(await screen.findByTestId('studio-ide-cancel')).toBeTruthy();

    fireEvent.click(screen.getByTestId('studio-ide-cancel'));

    expect(processVideo.mock.calls[0]?.[1]?.signal?.aborted).toBe(true);
    expect((screen.getByTestId('studio-ide-run') as HTMLButtonElement).disabled).toBe(false);
    expect(screen.queryByTestId('studio-ide-cancel')).toBeNull();
    expect(screen.getByText(/Analysis stopped in this browser\. Server work already accepted may continue\./)).toBeTruthy();
  });

  it('does not let a stopped run overwrite a newer run when its response arrives late', async () => {
    const finishes: Array<(id: string) => void> = [];
    const processVideo = vi.fn(() => new Promise<string>((resolve) => { finishes.push(resolve); }));
    useDashboardStore.setState({ processVideo });
    render(<OneLoopStudio showAgentWorkflowUi={false} />);
    fireEvent.change(screen.getByLabelText('YouTube URL'), { target: { value: video.url } });
    fireEvent.click(screen.getByTestId('studio-ide-run'));
    fireEvent.click(await screen.findByTestId('studio-ide-cancel'));
    fireEvent.click(screen.getByTestId('studio-ide-run'));
    expect(processVideo).toHaveBeenCalledTimes(2);

    await act(async () => { finishes[0](video.id); });

    expect(screen.getByTestId('studio-ide-cancel')).toBeTruthy();
    expect(screen.getByTestId('studio-ide-status').textContent).toMatch(/^Working/);
    expect(screen.queryByText(/Analysis cancelled/)).toBeNull();
    fireEvent.click(screen.getByTestId('studio-ide-cancel'));
    await act(async () => { finishes[1](video.id); });
    expect(screen.queryByTestId('studio-ide-cancel')).toBeNull();
    expect(screen.getByTestId('studio-ide-status').textContent).toContain('Analysis stopped in this browser. Server work already accepted may continue.');
  });

  it('stops the selection timer even if a stopped transport never settles', async () => {
    vi.useFakeTimers();
    const processVideo = vi.fn(() => new Promise<string>(() => {}));
    useDashboardStore.setState({ processVideo });
    render(<OneLoopStudio showAgentWorkflowUi={false} />);
    fireEvent.change(screen.getByLabelText('YouTube URL'), { target: { value: video.url } });
    fireEvent.click(screen.getByTestId('studio-ide-run'));
    fireEvent.click(screen.getByTestId('studio-ide-cancel'));
    act(() => {
      useDashboardStore.getState().addVideo({ ...video, id: 'another-selection', url: 'https://www.youtube.com/watch?v=jNQXAC9IVRw' });
      useDashboardStore.getState().selectVideo('another-selection');
    });

    await act(async () => { await vi.advanceTimersByTimeAsync(1_000); });

    expect(useDashboardStore.getState().selectedVideoId).toBe('another-selection');
  });
});
