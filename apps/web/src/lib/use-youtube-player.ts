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
        onError?: (e: YTPlayerEvent) => void;
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
const YT_API_STALL_TIMEOUT_MS = 3500;
let apiPromise: Promise<YTNamespace> | null = null;

function buildFallbackEmbedUrl(
  videoId: string,
  options?: { autoplay?: boolean; start?: number },
): string {
  const base = `https://www.youtube-nocookie.com/embed/${encodeURIComponent(videoId)}?rel=0&modestbranding=1`;
  const extra: string[] = [];
  if (options?.autoplay) extra.push('autoplay=1');
  if (options?.start && options.start > 0) extra.push(`start=${Math.floor(options.start)}`);
  return extra.length > 0 ? `${base}&${extra.join('&')}` : base;
}

function mountFallbackIframe(
  target: HTMLDivElement,
  videoId: string,
  options?: { autoplay?: boolean; start?: number },
): HTMLIFrameElement {
  const iframe = document.createElement('iframe');
  iframe.src = buildFallbackEmbedUrl(videoId, options);
  iframe.title = 'YouTube source player';
  iframe.className = 'h-full w-full border-0';
  iframe.allow =
    'accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share';
  iframe.allowFullscreen = true;
  iframe.referrerPolicy = 'strict-origin-when-cross-origin';
  iframe.setAttribute('data-testid', 'studio-player-fallback-iframe');
  target.replaceChildren(iframe);
  return iframe;
}

/** Load the IFrame API exactly once and resolve when `window.YT` is ready. */
function loadYouTubeApi(): Promise<YTNamespace> {
  if (typeof window === 'undefined') {
    return Promise.reject(new Error('YouTube API unavailable during SSR'));
  }
  if (window.YT?.Player) return Promise.resolve(window.YT);
  if (apiPromise) return apiPromise;

  apiPromise = new Promise<YTNamespace>((resolve, reject) => {
    const existing = window.onYouTubeIframeAPIReady;
    window.onYouTubeIframeAPIReady = () => {
      existing?.();
      if (window.YT?.Player) resolve(window.YT);
    };
    const existingScript = document.querySelector(
      `script[src="${YT_SRC}"]`,
    ) as HTMLScriptElement | null;
    if (existingScript) {
      existingScript.addEventListener(
        'error',
        () => {
          apiPromise = null;
          reject(new Error('Failed to load YouTube IFrame API'));
        },
        { once: true },
      );
      return;
    }
    const tag = document.createElement('script');
    tag.src = YT_SRC;
    tag.async = true;
    tag.onerror = () => {
      apiPromise = null;
      reject(new Error('Failed to load YouTube IFrame API'));
    };
    document.head.appendChild(tag);
  });
  return apiPromise;
}

export interface UseYouTubePlayerResult {
  /**
   * Callback ref — attach to the element that should be replaced by the player
   * iframe. Implemented as a callback (not a RefObject) so the player is torn
   * down and re-created when the container element itself changes — e.g. when
   * the stage is remounted into a different subtree while crossing a responsive
   * breakpoint, which leaves a RefObject-based player bound to a removed node.
   */
  containerRef: (node: HTMLDivElement | null) => void;
  currentTime: number;
  duration: number;
  isPlaying: boolean;
  ready: boolean;
  /**
   * True when the IFrame API player reported an embed error.
   * An API stall or blocked script is `direct`, not `failed`.
   */
  failed: boolean;
  /** True when a nocookie iframe is mounted because the IFrame API stalled or was blocked. */
  direct: boolean;
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
  // Track the container as state (via a callback ref) rather than a RefObject
  // so the init effect re-runs when the element is swapped, not only when
  // `videoId` changes.
  const [container, setContainer] = useState<HTMLDivElement | null>(null);
  const containerRef = useCallback((node: HTMLDivElement | null) => {
    setContainer(node);
  }, []);
  const playerRef = useRef<YTPlayer | null>(null);
  const fallbackIframeRef = useRef<HTMLIFrameElement | null>(null);
  const videoIdRef = useRef<string | null>(videoId);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const readyRef = useRef(false);

  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [ready, setReady] = useState(false);
  const [failed, setFailed] = useState(false);
  const [direct, setDirect] = useState(false);
  const mountedVideoRef = useRef<string | null>(null);

  useEffect(() => {
    videoIdRef.current = videoId;
  }, [videoId]);

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

    const videoChanged = mountedVideoRef.current !== videoId;
    mountedVideoRef.current = videoId;

    if (!videoId) {
      readyRef.current = false;
      fallbackIframeRef.current = null;
      setReady(false);
      setFailed(false);
      setDirect(false);
      setCurrentTime(0);
      setDuration(0);
      setIsPlaying(false);
      return;
    }

    if (!container) {
      // The Studio shell unmounts this host once it renders the direct iframe.
      // Keep `direct` for the same video so that swap does not restart the API.
      // A new video must try the API again.
      if (videoChanged) {
        readyRef.current = false;
        fallbackIframeRef.current = null;
        setReady(false);
        setFailed(false);
        setDirect(false);
        setIsPlaying(false);
      }
      return;
    }

    readyRef.current = false;
    fallbackIframeRef.current = null;
    setReady(false);
    setFailed(false);
    setDirect(false);
    setCurrentTime(0);
    setDuration(0);
    setIsPlaying(false);

    // Mount YT.Player on a child host so YouTube's DOM node swap never detaches React's container.
    const playerHost = document.createElement('div');
    playerHost.className = 'h-full w-full';
    container.replaceChildren(playerHost);

    const activateDirect = () => {
      if (cancelled || readyRef.current) return;
      clearTimeout(failTimer);
      stopPolling();
      try {
        playerRef.current?.destroy();
      } catch {
        /* noop */
      }
      playerRef.current = null;
      fallbackIframeRef.current = mountFallbackIframe(container, videoId);
      setReady(false);
      setIsPlaying(false);
      // The script never started the player. The nocookie iframe may still work,
      // so this is not an embed failure and must not be covered as one.
      setFailed(false);
      setDirect(true);
    };

    const markEmbedFailed = () => {
      if (cancelled) return;
      clearTimeout(failTimer);
      stopPolling();
      readyRef.current = false;
      try {
        playerRef.current?.destroy();
      } catch {
        /* noop */
      }
      playerRef.current = null;
      fallbackIframeRef.current = null;
      setReady(false);
      setIsPlaying(false);
      setDirect(false);
      setFailed(true);
    };

    // If the JS API stalls (blocked script, CSP, offline), mount a direct nocookie iframe after 3.5s.
    const failTimer = setTimeout(activateDirect, YT_API_STALL_TIMEOUT_MS);

    loadYouTubeApi()
      .then((YT) => {
        if (cancelled) return;
        try {
          playerRef.current = new YT.Player(playerHost, {
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
                fallbackIframeRef.current = null;
                setReady(true);
                setFailed(false);
                setDirect(false);
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
              onError: () => {
                markEmbedFailed();
              },
            },
          });
        } catch {
          activateDirect();
        }
      })
      .catch(() => {
        activateDirect();
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
      fallbackIframeRef.current = null;
      container.replaceChildren();
    };
  }, [videoId, container, startPolling, stopPolling]);

  const seekTo = useCallback((seconds: number) => {
    const target = Math.max(0, seconds);
    const p = playerRef.current;
    if (p) {
      try {
        p.seekTo(target, true);
        p.playVideo();
        setCurrentTime(target);
      } catch {
        /* noop */
      }
      return;
    }
    const iframe = fallbackIframeRef.current;
    const vid = videoIdRef.current;
    if (iframe && vid) {
      iframe.src = buildFallbackEmbedUrl(vid, { autoplay: true, start: target });
      setCurrentTime(target);
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

  return { containerRef, currentTime, duration, isPlaying, ready, failed, direct, seekTo, play, pause };
}
