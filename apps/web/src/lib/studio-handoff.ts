import { extractYouTubeId } from '@/lib/timestamp';
import { CANONICAL_STUDIO_PATH } from '@/lib/auth-paths';

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
