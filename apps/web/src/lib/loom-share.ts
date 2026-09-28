/**
 * Public Loom share URL parsing and media classification.
 *
 * Accepted inputs (https only):
 *   https://www.loom.com/share/{32-hex}
 *   https://loom.com/share/{32-hex}
 *   https://www.loom.com/embed/{32-hex}
 *   https://loom.com/embed/{32-hex}
 * Query strings are ignored. Folders, watch-page HTML, and non-Loom hosts are not shares.
 *
 * Direct files xAI STT can take: mp4, m4a, webm, mkv, mp3, wav, ogg, opus, flac, aac
 * on cdn.loom.com or luna.loom.com. HLS (m3u8) and DASH (mpd) are playlists, not files.
 */

const LOOM_PAGE_HOSTS = new Set(['loom.com', 'www.loom.com']);

/** Hosts that have returned signed media for a public share (probed 2026-09-28). */
const LOOM_MEDIA_HOSTS = new Set(['cdn.loom.com', 'luna.loom.com']);

const DIRECT_EXTENSIONS = new Set([
  'mp4',
  'm4a',
  'webm',
  'mkv',
  'mp3',
  'wav',
  'ogg',
  'opus',
  'flac',
  'aac',
]);

const PLAYLIST_EXTENSIONS = new Set(['m3u8', 'mpd']);

export type LoomShareRef = {
  videoId: string;
  shareUrl: string;
};

export type LoomMediaKind = 'file' | 'playlist' | 'page' | 'other';

export function parseLoomShareInput(raw: string): LoomShareRef | null {
  const trimmed = raw.trim();
  if (!trimmed) return null;
  let url: URL;
  try {
    url = new URL(trimmed);
  } catch {
    return null;
  }
  if (url.protocol !== 'https:') return null;
  if (!LOOM_PAGE_HOSTS.has(url.hostname.toLowerCase())) return null;
  const parts = url.pathname.split('/').filter(Boolean);
  if (parts.length !== 2) return null;
  const kind = parts[0]?.toLowerCase();
  if (kind !== 'share' && kind !== 'embed') return null;
  const videoId = parts[1]?.toLowerCase() ?? '';
  if (!/^[a-f0-9]{32}$/.test(videoId)) return null;
  return {
    videoId,
    shareUrl: `https://www.loom.com/share/${videoId}`,
  };
}

export function isLoomMediaHost(hostname: string): boolean {
  return LOOM_MEDIA_HOSTS.has(hostname.toLowerCase().replace(/\.$/, ''));
}

function extensionOf(url: URL): string {
  const last = url.pathname.split('/').pop() ?? '';
  const dot = last.lastIndexOf('.');
  if (dot < 0) return '';
  return last.slice(dot + 1).toLowerCase();
}

export function loomMediaKind(raw: string): LoomMediaKind {
  let url: URL;
  try {
    url = new URL(raw);
  } catch {
    return 'other';
  }
  const host = url.hostname.toLowerCase();
  if (LOOM_PAGE_HOSTS.has(host)) {
    const parts = url.pathname.split('/').filter(Boolean);
    const head = parts[0]?.toLowerCase();
    if (head === 'share' || head === 'embed') return 'page';
  }
  const ext = extensionOf(url);
  if (DIRECT_EXTENSIONS.has(ext)) return 'file';
  if (PLAYLIST_EXTENSIONS.has(ext)) return 'playlist';
  return 'other';
}

export function looksLikeHtml(bytes: Uint8Array, contentType: string | null): boolean {
  if (contentType && /text\/html|application\/xhtml\+xml/i.test(contentType)) return true;
  const head = new TextDecoder('utf-8', { fatal: false })
    .decode(bytes.subarray(0, 64))
    .trimStart()
    .toLowerCase();
  return head.startsWith('<!doctype') || head.startsWith('<html') || head.startsWith('<head');
}

/** True when the leading bytes are a container xAI STT auto-detects, or ADTS/MP3. */
export function looksLikeMediaContainer(bytes: Uint8Array): boolean {
  if (bytes.length >= 8) {
    // ISO BMFF 'ftyp' at offset 4 (mp4 / m4a).
    if (bytes[4] === 0x66 && bytes[5] === 0x74 && bytes[6] === 0x79 && bytes[7] === 0x70) {
      return true;
    }
  }
  if (bytes.length >= 4) {
    // EBML (webm / mkv).
    if (bytes[0] === 0x1a && bytes[1] === 0x45 && bytes[2] === 0xdf && bytes[3] === 0xa3) return true;
    // RIFF (wav).
    if (bytes[0] === 0x52 && bytes[1] === 0x49 && bytes[2] === 0x46 && bytes[3] === 0x46) return true;
    // OggS.
    if (bytes[0] === 0x4f && bytes[1] === 0x67 && bytes[2] === 0x67 && bytes[3] === 0x53) return true;
    // fLaC.
    if (bytes[0] === 0x66 && bytes[1] === 0x4c && bytes[2] === 0x61 && bytes[3] === 0x43) return true;
  }
  if (bytes.length >= 3 && bytes[0] === 0x49 && bytes[1] === 0x44 && bytes[2] === 0x33) return true;
  if (bytes.length >= 2 && bytes[0] === 0xff && (bytes[1] & 0xf0) === 0xf0) return true;
  return false;
}

const CONTENT_TYPE_BY_EXTENSION: Record<string, string> = {
  mp4: 'video/mp4',
  m4a: 'audio/mp4',
  webm: 'video/webm',
  mkv: 'video/x-matroska',
  mp3: 'audio/mpeg',
  wav: 'audio/wav',
  ogg: 'audio/ogg',
  opus: 'audio/opus',
  flac: 'audio/flac',
  aac: 'audio/aac',
};

export function contentTypeForMediaUrl(raw: string): string | null {
  let url: URL;
  try {
    url = new URL(raw);
  } catch {
    return null;
  }
  return CONTENT_TYPE_BY_EXTENSION[extensionOf(url)] ?? null;
}

export type HlsDocument = {
  audioPlaylist: string | null;
  variantPlaylists: string[];
  segments: string[];
};

/**
 * Pull playlist and segment URIs out of an HLS document.
 * Audio rendition (`EXT-X-MEDIA` TYPE=AUDIO) is preferred over the video variant.
 */
export function parseHlsDocument(text: string): HlsDocument {
  let audioPlaylist: string | null = null;
  const variantPlaylists: string[] = [];
  const segments: string[] = [];
  const lines = text.split(/\r?\n/);
  for (let i = 0; i < lines.length; i += 1) {
    const line = lines[i]?.trim() ?? '';
    if (!line) continue;
    if (line.startsWith('#EXT-X-MEDIA:')) {
      if (/TYPE=AUDIO/i.test(line)) {
        const match = /URI="([^"]+)"/.exec(line);
        if (match?.[1]) audioPlaylist = match[1];
      }
      continue;
    }
    if (line.startsWith('#')) {
      continue;
    }
    const previous = lines[i - 1]?.trim() ?? '';
    if (previous.startsWith('#EXT-X-STREAM-INF')) {
      variantPlaylists.push(line);
      continue;
    }
    if (previous.startsWith('#EXTINF')) {
      segments.push(line);
    }
  }
  return { audioPlaylist, variantPlaylists, segments };
}

export function resolveHlsReference(baseUrl: string, reference: string): string {
  const base = new URL(baseUrl);
  const resolved = new URL(reference, base);
  if (!resolved.search && base.search) {
    resolved.search = base.search;
  }
  return resolved.toString();
}

/**
 * Concatenate ADTS AAC frames found in an MPEG-TS (or raw ADTS) buffer.
 * A candidate frame is kept only when the next byte is another sync or the end,
 * which rejects accidental 0xFFF patterns inside TS headers.
 */
export function extractAdtsAac(input: Uint8Array): Uint8Array {
  const frames: Uint8Array[] = [];
  let i = 0;
  while (i + 7 < input.length) {
    if (input[i] !== 0xff || (input[i + 1] & 0xf0) !== 0xf0) {
      i += 1;
      continue;
    }
    const frameLength =
      ((input[i + 3] & 0x03) << 11) | (input[i + 4] << 3) | ((input[i + 5] & 0xe0) >> 5);
    if (frameLength < 7 || i + frameLength > input.length) {
      i += 1;
      continue;
    }
    const next = i + frameLength;
    const atEnd = next >= input.length;
    const nextIsSync =
      !atEnd && next + 1 < input.length && input[next] === 0xff && (input[next + 1] & 0xf0) === 0xf0;
    if (!atEnd && !nextIsSync) {
      i += 1;
      continue;
    }
    frames.push(input.subarray(i, next));
    i = next;
  }
  const total = frames.reduce((sum, frame) => sum + frame.length, 0);
  const out = new Uint8Array(total);
  let offset = 0;
  for (const frame of frames) {
    out.set(frame, offset);
    offset += frame.length;
  }
  return out;
}
