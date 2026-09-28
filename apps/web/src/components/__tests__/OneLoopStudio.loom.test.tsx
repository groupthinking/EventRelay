// @vitest-environment jsdom
import React from 'react';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import OneLoopStudio from '@/components/OneLoopStudio';
import { useDashboardStore } from '@/store/dashboard-store';

const { requestLoomProBuild } = vi.hoisted(() => ({
  requestLoomProBuild: vi.fn(),
}));

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
vi.mock('@/lib/loom-studio-client', () => ({
  requestLoomProBuild,
}));

const SHARE = 'https://www.loom.com/share/c43a642f815f4378b6f80a889bb73d8d';
const originalProcessVideo = useDashboardStore.getState().processVideo;

beforeEach(() => {
  vi.stubGlobal('React', React);
  vi.spyOn(useDashboardStore.persist, 'rehydrate').mockImplementation(() => undefined);
  useDashboardStore.setState({
    videos: [],
    selectedVideoId: null,
    processVideo: vi.fn(async () => 'youtube-row'),
  });
  requestLoomProBuild.mockReset();
  requestLoomProBuild.mockResolvedValue({
    ok: true,
    loomId: 'c43a642f815f4378b6f80a889bb73d8d',
    shareUrl: SHARE,
    transcript: 'Ship the queue worker next.',
    duration: 18.2,
    answer: 'Build a queue worker with a single retry rail.',
    provider: 'xai',
    model: 'grok-4-1-fast',
    sttModel: 'grok-voice-transcribe-2.0',
    audioSource: 'transcoded-url',
    plan: 'pro',
  });
});

afterEach(() => {
  cleanup();
  useDashboardStore.setState({
    videos: [],
    selectedVideoId: null,
    processVideo: originalProcessVideo,
  });
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe('OneLoopStudio Loom paste', () => {
  it('puts the xAI transcript and Pro Grok build in the session without the YouTube pack path', async () => {
    render(<OneLoopStudio showAgentWorkflowUi={false} />);
    const input = screen.getByLabelText(/YouTube URL/i);
    fireEvent.change(input, { target: { value: `https://loom.com/embed/${SHARE.split('/').pop()}` } });
    fireEvent.submit(input.closest('form')!);

    const build = await screen.findByTestId('studio-loom-grok-build');
    expect(build.textContent).toContain('Build a queue worker with a single retry rail.');
    expect(screen.getByTestId('studio-transcript-body').textContent).toContain('Ship the queue worker next.');
    expect(requestLoomProBuild).toHaveBeenCalledWith(SHARE);
    expect(useDashboardStore.getState().processVideo).not.toHaveBeenCalled();
  });
});
