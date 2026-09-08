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

/**
 * One-shot ?video= / ?url= kick. Safe under Strict Mode: the same startedKey
 * ref suppresses a second start() for the same video id.
 */
export function applyStudioQueryAutoStart(input: {
  query: string | null | undefined;
  startedKey: StudioQueryStartedKey;
  start: (watchUrl: string) => void;
  onResolved?: (watchUrl: string) => void;
  onInvalidQuery?: (raw: string) => void;
}): 'skipped' | 'invalid' | 'started' | 'already' {
  const query = typeof input.query === 'string' ? input.query.trim() : '';
  if (!query) return 'skipped';
  const handoff = resolveStudioHandoff(query);
  if (!handoff) {
    input.onInvalidQuery?.(query);
    return 'invalid';
  }
  input.onResolved?.(handoff.watchUrl);
  if (input.startedKey.current === handoff.videoId) return 'already';
  input.startedKey.current = handoff.videoId;
  input.start(handoff.watchUrl);
  return 'started';
}
