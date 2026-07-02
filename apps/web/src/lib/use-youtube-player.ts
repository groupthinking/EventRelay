'use client';

import { useCallback, useEffect, useRef, useState } from 'react';

/**
 * Minimal typing for the parts of the YouTube IFrame Player API we use.
 * Avoids pulling in @types/youtube for a handful of methods.
 */
interface YTPlayer {
  playVideo: () => void;
  pauseVideo: () => void;
  seekTo: (seconds: number, allowSeekAhead: boolean) => void;
  getCurrentTime: () => number;
  getDuration: () => number;
  destroy: () => void;
}

interface YTPlayerEvent {
  data: number;
  target: YTPlayer;
}

type YTNamespace = {
  Player: new (
    el: HTMLElement | string,
    opts: {
      videoId: string;
      playerVars?: Record<string, string | number>;
      events?: {
        onReady?: (e: YTPlayerEvent) => void;
        onStateChange?: (e: YTPlayerEvent) => void;
      };
    },
  ) => YTPlayer;
  PlayerState: { PLAYING: number; PAUSED: number; ENDED: number; BUFFERING: number };
};

declare global {
  interface Window {
    YT?: YTNamespace;
    onYouTubeIframeAPIReady?: () => void;
  }
}

const YT_SRC = 'https://www.youtube.com/iframe_api';
let apiPromise: Promise<YTNamespace> | null = null;

/** Load the IFrame API exactly once and resolve when `window.YT` is ready. */
function loadYouTubeApi(): Promise<YTNamespace> {
  if (typeof window === 'undefined') {
    return Promise.reject(new Error('YouTube API unavailable during SSR'));
  }
  if (window.YT?.Player) return Promise.resolve(window.YT);
  if (apiPromise) return apiPromise;

  apiPromise = new Promise<YTNamespace>((resolve) => {
    const existing = window.onYouTubeIframeAPIReady;
    window.onYouTubeIframeAPIReady = () => {
      existing?.();
      if (window.YT) resolve(window.YT);
    };
    if (!document.querySelector(`script[src="${YT_SRC}"]`)) {
      const tag = document.createElement('script');
      tag.src = YT_SRC;
      tag.async = true;
      document.head.appendChild(tag);
    }
  });
  return apiPromise;
}

export interface UseYouTubePlayerResult {
  /** Attach to the element that should be replaced by the player iframe. */
  containerRef: React.RefObject<HTMLDivElement | null>;
  currentTime: number;
  duration: number;
  isPlaying: boolean;
  ready: boolean;
  /** True when the IFrame API could not load/init (e.g. blocked or offline). */
  failed: boolean;
  seekTo: (seconds: number) => void;
  play: () => void;
  pause: () => void;
}

/**
 * Embed a YouTube video via the IFrame API and expose synchronized playback
 * state (currentTime, isPlaying) plus imperative controls (seekTo/play/pause).
 *
 * Polls getCurrentTime on a light interval so consumers can highlight the
 * active transcript line / timeline marker as the video plays.
 */
export function useYouTubePlayer(videoId: string | null): UseYouTubePlayerResult {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const playerRef = useRef<YTPlayer | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const readyRef = useRef(false);

  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [ready, setReady] = useState(false);
  const [failed, setFailed] = useState(false);

  const stopPolling = useCallback(() => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }, []);

  const startPolling = useCallback(() => {
    stopPolling();
    pollRef.current = setInterval(() => {
      const p = playerRef.current;
      if (!p) return;
      try {
        setCurrentTime(p.getCurrentTime() || 0);
      } catch {
        /* player not ready yet */
      }
    }, 250);
  }, [stopPolling]);

  useEffect(() => {
    let cancelled = false;
    readyRef.current = false;
    setReady(false);
    setFailed(false);
    setCurrentTime(0);
    setDuration(0);
    setIsPlaying(false);

    if (!videoId || !containerRef.current) return;

    // If the API never initializes (blocked script, offline, CSP), surface a
    // failure after a grace period so the UI can fall back to a plain embed.
    const failTimer = setTimeout(() => {
      if (!cancelled && !readyRef.current) setFailed(true);
    }, 8000);

    loadYouTubeApi()
      .then((YT) => {
        if (cancelled || !containerRef.current) return;
        playerRef.current = new YT.Player(containerRef.current, {
          videoId,
          playerVars: {
            rel: 0,
            modestbranding: 1,
            playsinline: 1,
          },
          events: {
            onReady: (e) => {
              if (cancelled) return;
              clearTimeout(failTimer);
              readyRef.current = true;
              setReady(true);
              setFailed(false);
              try {
                setDuration(e.target.getDuration() || 0);
              } catch {
                /* noop */
              }
            },
            onStateChange: (e) => {
              if (cancelled) return;
              const state = e.data;
              const playing = state === YT.PlayerState.PLAYING;
              setIsPlaying(playing);
              if (playing) startPolling();
              else stopPolling();
              if (state === YT.PlayerState.PLAYING || state === YT.PlayerState.PAUSED) {
                try {
                  setDuration(e.target.getDuration() || 0);
                  setCurrentTime(e.target.getCurrentTime() || 0);
                } catch {
                  /* noop */
                }
              }
            },
          },
        });
      })
      .catch(() => {
        if (!cancelled) {
          clearTimeout(failTimer);
          setReady(false);
          setFailed(true);
        }
      });

    return () => {
      cancelled = true;
      clearTimeout(failTimer);
      stopPolling();
      try {
        playerRef.current?.destroy();
      } catch {
        /* noop */
      }
      playerRef.current = null;
    };
  }, [videoId, startPolling, stopPolling]);

  const seekTo = useCallback((seconds: number) => {
    const p = playerRef.current;
    if (!p) return;
    try {
      p.seekTo(Math.max(0, seconds), true);
      p.playVideo();
      setCurrentTime(Math.max(0, seconds));
    } catch {
      /* noop */
    }
  }, []);

  const play = useCallback(() => {
    try {
      playerRef.current?.playVideo();
    } catch {
      /* noop */
    }
  }, []);

  const pause = useCallback(() => {
    try {
      playerRef.current?.pauseVideo();
    } catch {
      /* noop */
    }
  }, []);

  return { containerRef, currentTime, duration, isPlaying, ready, failed, seekTo, play, pause };
}
