/**
 * Resolve and validate video URLs for BFF routes.
 *
 * Host allowlist mirrors backend `_YOUTUBE_URL_REGEX` — arbitrary hosts
 * (SSRF) and leading-dash tokens (yt-dlp CWE-88) must never leave the edge.
 */

/** Anchored YouTube watch / short / embed / youtu.be patterns with 11-char id. */
const YOUTUBE_URL_REGEX =
  /^(https?:\/\/)?(www\.)?(youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/|youtube\.com\/shorts\/)[a-zA-Z0-9_-]{11}/;

export function resolveVideoUrl(body: Record<string, unknown> | null | undefined): string {
  if (!body) return '';

  const value =
    body.url ??
    body.youtubeUrl ??
    body.videoUrl ??
    body.video_url;

  return typeof value === 'string' ? value.trim() : '';
}

/**
 * True only for allowlisted YouTube URL shapes. Rejects link-local/metadata
 * hosts that merely contain an 11-char token, and rejects leading-dash argv
 * injection strings.
 */
export function isAllowedYoutubeUrl(url: string): boolean {
  if (!url || typeof url !== 'string') return false;
  const trimmed = url.trim();
  if (!trimmed || trimmed.startsWith('-')) return false;
  return YOUTUBE_URL_REGEX.test(trimmed);
}

/**
 * Resolve URL from body and return it only if allowlisted; otherwise ''.
 */
export function resolveAllowedVideoUrl(
  body: Record<string, unknown> | null | undefined,
): string {
  const url = resolveVideoUrl(body);
  return isAllowedYoutubeUrl(url) ? url : '';
}
