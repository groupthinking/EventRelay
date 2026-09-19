/** Client-safe hosted spec URL helpers (no server-only or react-dom imports). */

export function hostedSpecLivePath(videoId: string): string {
  return `/d/${encodeURIComponent(videoId.trim())}`;
}
