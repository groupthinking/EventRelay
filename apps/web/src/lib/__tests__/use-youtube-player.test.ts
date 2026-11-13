// @vitest-environment jsdom
import { act, renderHook, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useYouTubePlayer } from '@/lib/use-youtube-player';

type Events = {
  onReady?: (e: { data: number; target: FakePlayer }) => void;
  onStateChange?: (e: { data: number; target: FakePlayer }) => void;
};

class FakePlayer {
  static instances: FakePlayer[] = [];
  seekTo = vi.fn();
  playVideo = vi.fn();
  pauseVideo = vi.fn();
  destroy = vi.fn();
  getCurrentTime = vi.fn(() => 0);
  getDuration = vi.fn(() => 480);
  constructor(_el: HTMLElement | string, opts: { events?: Events }) {
    FakePlayer.instances.push(this);
    setTimeout(() => opts.events?.onReady?.({ data: -1, target: this }), 0);
  }
}

beforeEach(() => {
  FakePlayer.instances = [];
  window.YT = {
    Player: FakePlayer as unknown as NonNullable<Window['YT']>['Player'],
    PlayerState: { PLAYING: 1, PAUSED: 2, ENDED: 0, BUFFERING: 3 },
  };
});

afterEach(() => {
  delete window.YT;
});

async function mountPlayer() {
  const hook = renderHook(() => useYouTubePlayer('auJzb1D-fag'));
  const container = document.createElement('div');
  act(() => hook.result.current.containerRef(container));
  await waitFor(() => expect(hook.result.current.ready).toBe(true));
  const player = FakePlayer.instances[0];
  if (!player) throw new Error('player not constructed');
  return { hook, player };
}

describe('useYouTubePlayer seekTo', () => {
  it('seeks and plays by default (existing behavior)', async () => {
    const { hook, player } = await mountPlayer();
    act(() => hook.result.current.seekTo(42.7));
    expect(player.seekTo).toHaveBeenCalledWith(42.7, true);
    expect(player.playVideo).toHaveBeenCalledTimes(1);
    expect(player.pauseVideo).not.toHaveBeenCalled();
    expect(hook.result.current.currentTime).toBe(42.7);
  });

  it('cues without playing when autoplay is false', async () => {
    const { hook, player } = await mountPlayer();
    act(() => hook.result.current.seekTo(120, { autoplay: false }));
    expect(player.seekTo).toHaveBeenCalledWith(120, true);
    expect(player.playVideo).not.toHaveBeenCalled();
    expect(player.pauseVideo).toHaveBeenCalledTimes(1);
    expect(hook.result.current.currentTime).toBe(120);
  });

  it('clamps negative seek targets to zero', async () => {
    const { hook, player } = await mountPlayer();
    act(() => hook.result.current.seekTo(-9));
    expect(player.seekTo).toHaveBeenCalledWith(0, true);
  });
});
