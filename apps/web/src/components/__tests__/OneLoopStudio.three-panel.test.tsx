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
const seekToMock = vi.fn();
const playerStateMock = vi.fn(() => ({
  containerRef: (() => undefined) as (node: HTMLDivElement | null) => void,
  currentTime: 0,
  duration: 0,
  isPlaying: false,
  ready: false,
  failed: false,
  seekTo: seekToMock,
  play: vi.fn(),
  pause: vi.fn(),
}));
vi.mock('@/lib/use-youtube-player', () => ({
  useYouTubePlayer: () => playerStateMock(),
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
  seekToMock.mockReset();
  playerStateMock.mockImplementation(() => ({
    containerRef: (() => undefined) as (node: HTMLDivElement | null) => void,
    currentTime: 0,
    duration: 0,
    isPlaying: false,
    ready: false,
    failed: false,
    seekTo: seekToMock,
    play: vi.fn(),
    pause: vi.fn(),
  }));
  vi.spyOn(useDashboardStore.persist, 'rehydrate').mockImplementation(() => undefined);
  useDashboardStore.setState({ videos: [baseVideo], selectedVideoId: baseVideo.id });
});

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe('OneLoopStudio IDE shell', () => {
  it('renders the streamlined IDE shell with Analyze, Export, and no duplicate toolbar bloat', () => {
    render(<OneLoopStudio showAgentWorkflowUi />);
    expect(screen.getByTestId('studio-ide-shell')).toBeTruthy();
    expect(screen.getByTestId('studio-ide-toolbar')).toBeTruthy();
    expect(screen.getByTestId('studio-ide-video-pane')).toBeTruthy();
    expect(screen.getByTestId('studio-ide-chat-pane')).toBeTruthy();
    expect(screen.getByTestId('studio-ide-output-pane')).toBeTruthy();
    expect(screen.queryByTestId('studio-ide-splitter-left')).toBeNull();
    expect(screen.queryByTestId('studio-ide-splitter-right')).toBeNull();
    expect(screen.getByTestId('studio-ide-run').textContent?.trim()).toBe('Analyze');
    expect(screen.getByTestId('studio-ide-ship').textContent?.trim()).toBe('Export');
    expect(screen.queryByTestId('studio-act-button')).toBeNull();
    expect(screen.queryByTestId('studio-build-live-button')).toBeNull();
    expect(screen.queryByTestId('studio-ide-delete-pack')).toBeNull();
    expect(screen.queryByRole('button', { name: 'Sample' })).toBeNull();
  });

  it('offers Try sample inside the empty video frame and loads the fixture URL', () => {
    useDashboardStore.setState({ videos: [], selectedVideoId: null });
    render(<OneLoopStudio showAgentWorkflowUi={false} />);
    const sampleBtn = screen.getByTestId('studio-try-sample');
    fireEvent.click(sampleBtn);
    expect((screen.getByLabelText('YouTube URL') as HTMLInputElement).value).toBe(
      'https://www.youtube.com/watch?v=auJzb1D-fag',
    );
    expect(screen.getByTestId('studio-player-poster').getAttribute('src')).toBe(
      'https://i.ytimg.com/vi/auJzb1D-fag/hqdefault.jpg',
    );
  });

  it('shows immediate poster backdrop while loading and direct nocookie embed on click or failure', () => {
    render(<OneLoopStudio showAgentWorkflowUi={false} />);
    const poster = screen.getByTestId('studio-player-poster');
    expect(poster.getAttribute('src')).toBe('https://i.ytimg.com/vi/auJzb1D-fag/hqdefault.jpg');
    fireEvent.click(screen.getByTestId('studio-player-overlay'));
    const iframe = screen.getByTestId('studio-player-fallback-iframe') as HTMLIFrameElement;
    expect(iframe.src).toContain('https://www.youtube-nocookie.com/embed/auJzb1D-fag?rel=0&modestbranding=1');

    cleanup();
    playerStateMock.mockImplementation(() => ({
      containerRef: (() => undefined) as (node: HTMLDivElement | null) => void,
      currentTime: 0,
      duration: 0,
      isPlaying: false,
      ready: false,
      failed: true,
      seekTo: seekToMock,
      play: vi.fn(),
      pause: vi.fn(),
    }));
    render(<OneLoopStudio showAgentWorkflowUi={false} />);
    expect(screen.queryByTestId('studio-player-poster')).toBeNull();
    expect(screen.getByTestId('studio-player-retry')).toBeTruthy();
  });

  it('never auto-selects failed runs on boot, formats Saved videos cleanly, and clears prior errors on switch or Analyze', async () => {
    const { reviewPackFixture } = await import('@/test/grounded-spec-fixture');
    const pack = reviewPackFixture();
    const failedPackVideo: Video = {
      id: 'failed-pack',
      title: 'Analyzing: https://www.youtube.com/watch?v=6TrjBFW6EKg',
      url: 'https://www.youtube.com/watch?v=6TrjBFW6EKg',
      status: 'failed',
      progress: 5,
      failure: {
        stage: 'analysis',
        message: 'Extraction stopped before finishing.',
        retryable: true,
        failedAt: '2026-10-17T00:00:00.000Z',
      },
      videoPack: {
        packId: 'vp:v0:6TrjBFW6EKg',
        videoId: '6TrjBFW6EKg',
        sourceUrl: 'https://www.youtube.com/watch?v=6TrjBFW6EKg',
        sourceHash: 'abc123456789',
        version: pack.version,
        pack: { ...pack, video_id: '6TrjBFW6EKg', source_url: 'https://www.youtube.com/watch?v=6TrjBFW6EKg' },
      },
    };
    const completePackVideo: Video = {
      ...baseVideo,
      id: 'complete-pack',
      title: 'Clean Complete Video',
      videoPack: {
        packId: pack.id,
        videoId: pack.video_id,
        sourceUrl: pack.source_url,
        sourceHash: pack.provenance.source_hash,
        version: pack.version,
        pack,
      },
    };

    // Only failed pack in store: must NOT auto-select or display error/working banner on boot.
    useDashboardStore.setState({ videos: [failedPackVideo], selectedVideoId: null });
    render(<OneLoopStudio showAgentWorkflowUi={false} />);
    expect(useDashboardStore.getState().selectedVideoId).toBeNull();
    expect(screen.queryByTestId('studio-transcript-retry')).toBeNull();
    expect(screen.getByTestId('studio-ide-status').textContent).not.toMatch(/^Working/);

    const savedSelect = screen.getByRole('combobox', { name: 'Saved videos' });
    expect(savedSelect.textContent).toContain('YouTube · 6TrjBFW6EKg');
    expect(savedSelect.textContent).not.toContain('Analyzing: https://');

    // Select the failed pack manually -> shows retry banner.
    fireEvent.change(savedSelect, { target: { value: 'failed-pack' } });
    expect(screen.getByTestId('studio-transcript-retry')).toBeTruthy();

    // Switch to a complete video -> error banner clears immediately.
    act(() => {
      useDashboardStore.setState({ videos: [failedPackVideo, completePackVideo] });
    });
    fireEvent.change(savedSelect, { target: { value: 'complete-pack' } });
    expect(screen.queryByTestId('studio-transcript-retry')).toBeNull();

    // Select failed pack again, then start a new Analyze run -> error clears immediately.
    fireEvent.change(savedSelect, { target: { value: 'failed-pack' } });
    expect(screen.getByTestId('studio-transcript-retry')).toBeTruthy();
    const pendingProcess = vi.fn(() => new Promise<string>(() => {}));
    useDashboardStore.setState({ processVideo: pendingProcess });
    fireEvent.change(screen.getByLabelText('YouTube URL'), {
      target: { value: 'https://www.youtube.com/watch?v=auJzb1D-fag' },
    });
    fireEvent.click(screen.getByTestId('studio-ide-run'));
    expect(screen.queryByTestId('studio-transcript-retry')).toBeNull();
    expect(await screen.findByTestId('studio-ide-cancel')).toBeTruthy();
  });

  it('renders wrapped singularized metric pills and Ready badge without overflow', async () => {
    const { reviewPackFixture } = await import('@/test/grounded-spec-fixture');
    const pack = reviewPackFixture();
    pack.action_items = [{ id: 'a1', title: 'Action 1', description: 'Do 1', type: 'step' }];
    pack.stack.tools = [{ name: 'Workflow API', kind: 'API', evidence: 'Source mentions workflow calls.' }];
    pack.code_snippets = [{ path_hint: 'app.ts', lang: 'ts', content: 'export const ok = true;' }];
    const words = Array.from({ length: 154 }, (_, i) => `word${i}`).join(' ');
    useDashboardStore.setState({
      videos: [
        {
          ...baseVideo,
          transcript: words,
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
    const videoPane = screen.getByTestId('studio-ide-video-pane');
    expect(videoPane.textContent).toContain('1 action');
    expect(videoPane.textContent).toContain('1 tool');
    expect(videoPane.textContent).toContain('1 code file');
    expect(videoPane.textContent).toContain('154 words');
    expect(videoPane.textContent).toContain('Ready');
  });

  it('shows the stack in a pack with tools in Tasks & Tools and renders chat + output panes', async () => {
    const { reviewPackFixture } = await import('@/test/grounded-spec-fixture');
    const pack = reviewPackFixture();
    pack.stack.tools = [{ name: 'Workflow API', kind: 'API', evidence: 'Source mentions workflow calls.' }];
    useDashboardStore.setState({
      videos: [{
        ...baseVideo,
        events: [],
        videoPack: {
          packId: pack.id,
          videoId: pack.video_id,
          sourceUrl: pack.source_url,
          sourceHash: pack.provenance.source_hash,
          version: pack.version,
          pack,
        },
      }],
      selectedVideoId: baseVideo.id,
    });

    render(<OneLoopStudio showAgentWorkflowUi={false} />);
    expect(screen.getByTestId('studio-ide-chat')).toBeTruthy();
    expect(screen.getByTestId('studio-ide-chat-input')).toBeTruthy();
    expect(screen.getByTestId('studio-ide-chat-send')).toBeTruthy();
    expect(screen.getByTestId('studio-ide-output')).toBeTruthy();
    fireEvent.click(screen.getByTestId('studio-ide-output-tab-tasks'));
    expect(screen.getByTestId('pack-stack-tools').textContent).toMatch(/Workflow API/);
    expect((screen.getByTestId('studio-ide-ship') as HTMLButtonElement).disabled).toBe(false);
  });

  it('shows transcript retry when analysis failed and is retryable', () => {
    useDashboardStore.setState({
      videos: [
        {
          ...baseVideo,
          status: 'failed',
          failure: {
            stage: 'analysis',
            message: 'Gemini 3.8 Flash returned no extracted spec content.',
            retryable: true,
            failedAt: '2026-10-17T00:00:00.000Z',
          },
        },
      ],
      selectedVideoId: baseVideo.id,
    });
    render(<OneLoopStudio showAgentWorkflowUi={false} />);
    expect(screen.getByTestId('studio-transcript-retry')).toBeTruthy();
  });

  it('shows a Stop button while a run is in flight', async () => {
    render(<OneLoopStudio showAgentWorkflowUi={false} />);
    const input = screen.getByLabelText('YouTube URL');
    fireEvent.change(input, { target: { value: 'https://www.youtube.com/watch?v=auJzb1D-fag' } });
    fireEvent.click(screen.getByTestId('studio-ide-run'));
    const stopBtn = await screen.findByTestId('studio-ide-cancel');
    expect(stopBtn.textContent?.trim()).toBe('Stop');
  });

  it('disables Quick jump chapters when the URL input changes to another video', async () => {
    const { reviewPackFixture } = await import('@/test/grounded-spec-fixture');
    const pack = reviewPackFixture();
    pack.chapters = [
      { start: 12, end: 40, topic: 'Calibration', key_points: ['Mount camera'] },
    ];
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
    const jumpBtn = screen.getByTestId('studio-quick-jump-0') as HTMLButtonElement;
    expect(jumpBtn.disabled).toBe(false);
    fireEvent.click(jumpBtn);
    expect(seekToMock).toHaveBeenCalledWith(12);

    seekToMock.mockReset();
    fireEvent.change(screen.getByLabelText('YouTube URL'), {
      target: { value: 'https://www.youtube.com/watch?v=9PICEmtfpWU' },
    });
    expect(jumpBtn.disabled).toBe(true);
    fireEvent.click(jumpBtn);
    expect(seekToMock).not.toHaveBeenCalled();
  });

  it('useYouTubePlayer lowers stall timeout to 3500ms and mounts nocookie fallback iframe', async () => {
    vi.useFakeTimers();
    const actual = await vi.importActual<typeof import('@/lib/use-youtube-player')>(
      '@/lib/use-youtube-player',
    );
    const { renderHook } = await import('@testing-library/react');
    const host = document.createElement('div');
    document.body.appendChild(host);

    const { result, unmount } = renderHook(() => actual.useYouTubePlayer('6TrjBFW6EKg'));
    act(() => {
      result.current.containerRef(host);
    });

    expect(result.current.failed).toBe(false);
    await act(async () => {
      await vi.advanceTimersByTimeAsync(3400);
    });
    expect(result.current.failed).toBe(false);

    await act(async () => {
      await vi.advanceTimersByTimeAsync(200);
    });
    expect(result.current.failed).toBe(true);
    const iframe = host.querySelector('iframe') as HTMLIFrameElement | null;
    expect(iframe).not.toBeNull();
    expect(iframe?.src).toBe(
      'https://www.youtube-nocookie.com/embed/6TrjBFW6EKg?rel=0&modestbranding=1',
    );

    unmount();
    host.remove();
    vi.useRealTimers();
  });

  it('normalizes orphaned processing rows and Analyzing URL titles during rehydrate', async () => {
    vi.restoreAllMocks();
    vi.stubGlobal('React', React);
    useDashboardStore.setState({ videos: [], selectedVideoId: null });
    window.localStorage.setItem(
      'eventrelay-dashboard-v1',
      JSON.stringify({
        state: {
          videos: [
            {
              id: 'orphan-6trj',
              title: 'Analyzing: https://www.youtube.com/watch?v=6TrjBFW6EKg',
              url: 'https://www.youtube.com/watch?v=6TrjBFW6EKg',
              status: 'processing',
              progress: 5,
            },
          ],
        },
        version: 0,
      }),
    );
    await act(async () => {
      await useDashboardStore.persist.rehydrate();
    });

    const [rehydrated] = useDashboardStore.getState().videos;
    expect(rehydrated?.status).toBe('failed');
    expect(rehydrated?.title).toBe('YouTube · 6TrjBFW6EKg');
    expect(useDashboardStore.getState().selectedVideoId).toBeNull();
    window.localStorage.removeItem('eventrelay-dashboard-v1');
  });
});
