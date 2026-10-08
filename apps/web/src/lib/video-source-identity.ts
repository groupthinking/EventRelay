/** Credential-free YouTube identity boundary; parsing never fetches a URL. */
const VIDEO_ID = /^[A-Za-z0-9_-]{11}$/;
const YOUTUBE_HOSTS = new Set(['youtube.com', 'www.youtube.com', 'm.youtube.com', 'music.youtube.com']);

export function resolveYouTubeSourceId(input: string): string | null {
  const value = input.trim();
  if (VIDEO_ID.test(value)) return value;
  if (/[\\\u0000-\u0020\u007f]/.test(value)) return null;
  // URL normalizes explicit default ports and backslashes; reject them first.
  const authority = /^https:\/\/([^/?#]+)/.exec(value)?.[1];
  if (!authority || authority.includes(':') || authority.includes('@') || authority.includes('%')) return null;
  try {
    const url = new URL(value);
    if (url.protocol !== 'https:' || url.username || url.password || url.port) return null;
    let candidate: string | null = null;
    if (url.hostname === 'youtu.be') {
      candidate = url.pathname.slice(1);
    } else if (YOUTUBE_HOSTS.has(url.hostname)) {
      if (url.pathname === '/watch') {
        const ids = url.searchParams.getAll('v');
        candidate = ids.length === 1 ? ids[0] : null;
      } else {
        candidate = /^\/(?:embed|shorts|v)\/([A-Za-z0-9_-]{11})$/.exec(url.pathname)?.[1] ?? null;
      }
    }
    return candidate !== null && VIDEO_ID.test(candidate) ? candidate : null;
  } catch {
    return null;
  }
}

export function canonicalYouTubeSource(videoId: string, suppliedSource?: string): string {
  if (!VIDEO_ID.test(videoId)) throw new Error('Invalid YouTube video identity');
  if (suppliedSource && resolveYouTubeSourceId(suppliedSource) !== videoId) {
    throw new Error('YouTube source does not match video identity');
  }
  return `https://www.youtube.com/watch?v=${videoId}`;
}
