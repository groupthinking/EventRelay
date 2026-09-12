import { extractYouTubeId } from '@/lib/timestamp';
import { CANONICAL_STUDIO_PATH } from '@/lib/auth-paths';
import { startVideoPackEmit } from '@/lib/emit-video-pack';

export type StudioHandoff = {
  videoId: string;
  watchUrl: string;
  href: string;
};

/** Normalize a paste (watch URL, share URL, or raw id) into a canonical watch URL. */
export function youtubeWatchUrlFromInput(raw: string): string | null {
  const videoId = extractYouTubeId(raw.trim());
  if (!videoId) return null;
  return `https://www.youtube.com/watch?v=${videoId}`;
}

export function resolveStudioHandoff(raw: string): StudioHandoff | null {
  const watchUrl = youtubeWatchUrlFromInput(raw);
  if (!watchUrl) return null;
  const videoId = extractYouTubeId(watchUrl);
  if (!videoId) return null;
  return {
    videoId,
    watchUrl,
    href: `${CANONICAL_STUDIO_PATH}?video=${encodeURIComponent(watchUrl)}`,
  };
}

export function studioVideoHref(raw: string): string | null {
  return resolveStudioHandoff(raw)?.href ?? null;
}

/**
 * Home paste: validate YouTube URL, kick pack emit, return /studio?video=.
 * Does not wait for spec extract. Invalid input returns null and does not emit.
 */
export function submitHomePaste(raw: string): string | null {
  const handoff = resolveStudioHandoff(raw);
  if (!handoff) return null;
  startVideoPackEmit(handoff.watchUrl);
  return handoff.href;
}

export type StudioQueryStartedKey = { current: string | null };
let strictModeAutoStartedVideoId: string | null = null;

/**
 * Clear the module-level Strict Mode auto-start guard. Studio calls this on a
 * genuine unmount so re-navigating to the same ?video= later in the same SPA
 * session (or retrying after a failed run) can auto-start again. The guard only
 * exists to swallow React's synchronous Strict Mode double-mount, so it must be
 * released once the component truly leaves the tree.
 */
export function resetStudioQueryAutoStart(): void {
  strictModeAutoStartedVideoId = null;
}

/**
 * One-shot ?video= / ?url= kick. Safe under Strict Mode remounts: both the
 * caller ref and a module-level key suppress duplicate start() calls.
 */
export type StudioSearchParams = {
  get(name: string): string | null;
};

/**
 * Read ?video= / ?url= from Studio. Browsers keep
 * `?video=https://www.youtube.com/watch?v=ID` as one param. Proxies that
 * rewrite the second `?` into `&` leave `video` without an id and `v` as a
 * sibling — reconstruct that pair instead of treating the handoff as junk.
 */
export function studioQueryFromSearchParams(
  params: StudioSearchParams | null | undefined,
): string | null {
  if (!params) return null;
  const video = (params.get('video') || params.get('url') || '').trim();
  const siblingId = (params.get('v') || '').trim();
  if (video && extractYouTubeId(video)) return video;
  if (video && siblingId && /youtube\.com\/watch\/?$/i.test(video)) {
    return `${video.replace(/\/$/, '')}?v=${siblingId}`;
  }
  if (siblingId && extractYouTubeId(siblingId)) return siblingId;
  return video || null;
}

export function applyStudioQueryAutoStart(input: {
  query?: string | null | undefined;
  searchParams?: StudioSearchParams | null;
  startedKey: StudioQueryStartedKey;
  start: (watchUrl: string) => void;
  onResolved?: (watchUrl: string) => void;
  onInvalidQuery?: (raw: string) => void;
}): 'skipped' | 'invalid' | 'started' | 'already' {
  const query = (
    input.searchParams
      ? studioQueryFromSearchParams(input.searchParams)
      : typeof input.query === 'string'
        ? input.query.trim()
        : ''
  ) || '';
  if (!query) return 'skipped';
  const handoff = resolveStudioHandoff(query);
  if (!handoff) {
    input.onInvalidQuery?.(query);
    return 'invalid';
  }
  input.onResolved?.(handoff.watchUrl);
  if (
    input.startedKey.current === handoff.videoId ||
    strictModeAutoStartedVideoId === handoff.videoId
  ) {
    return 'already';
  }
  input.startedKey.current = handoff.videoId;
  strictModeAutoStartedVideoId = handoff.videoId;
  input.start(handoff.watchUrl);
  return 'started';
}
