import 'server-only';

import { assertPublicHttpUrl } from '@/lib/ssrf-guard';
import {
  contentTypeForMediaUrl,
  extractAdtsAac,
  isLoomMediaHost,
  looksLikeHtml,
  looksLikeMediaContainer,
  loomMediaKind,
  parseHlsDocument,
  parseLoomShareInput,
  resolveHlsReference,
  type LoomShareRef,
} from '@/lib/loom-share';

/** Cap extracted HLS audio. Direct CDN files are handed to xAI by URL instead. */
export const LOOM_HLS_BYTE_CAP = 48 * 1024 * 1024;

export const LOOM_AUDIO_UNAVAILABLE =
  'Loom did not yield extractable audio. The watch page alone cannot be transcribed.';

export const LOOM_AUDIO_PRIVATE =
  'This Loom share is private or password-protected, so audio cannot be extracted.';

export const LOOM_AUDIO_TOO_LARGE =
  'Loom audio is larger than the server can extract for transcription.';

export const LOOM_URL_INVALID =
  'Need a public Loom share URL (https://www.loom.com/share/<id> or /embed/<id>).';

export type LoomAudioSourceName =
  | 'transcoded-url'
  | 'graphql-mp4'
  | 'graphql-webm'
  | 'raw-url'
  | 'hls-audio';

export type AcquiredLoomAudio =
  | {
      mode: 'url';
      mediaUrl: string;
      contentType: string;
      source: LoomAudioSourceName;
      share: LoomShareRef;
    }
  | {
      mode: 'file';
      bytes: Uint8Array;
      filename: string;
      contentType: 'audio/aac';
      source: 'hls-audio';
      share: LoomShareRef;
    };

export class LoomAudioError extends Error {
  readonly code: 'loom_url_invalid' | 'loom_audio_unavailable' | 'loom_private' | 'loom_audio_too_large';
  readonly status: number;

  constructor(
    message: string,
    code: LoomAudioError['code'],
    status: number,
  ) {
    super(message);
    this.name = 'LoomAudioError';
    this.code = code;
    this.status = status;
  }
}

export type LoomFetch = (input: string, init?: RequestInit) => Promise<Response>;

type AcquireDeps = {
  fetch?: LoomFetch;
  assertPublic?: (input: string) => Promise<URL>;
};

const GRAPHQL_SOURCE = `
query GetVideoSource($videoId: ID!, $password: String, $acceptableMimes: [CloudfrontVideoAcceptableMime]) {
  getVideo(id: $videoId, password: $password) {
    __typename
    ... on RegularUserVideo {
      id
      nullableRawCdnUrl(acceptableMimes: $acceptableMimes, password: $password) {
        url
      }
    }
  }
}
`.trim();

type MediaCandidate = {
  url: string;
  source: Exclude<LoomAudioSourceName, 'hls-audio'>;
};

function loomPageHeaders(videoId: string): HeadersInit {
  return {
    Accept: 'application/json',
    'Content-Type': 'application/json',
    Origin: 'https://www.loom.com',
    Referer: `https://www.loom.com/share/${videoId}`,
  };
}

async function readBounded(response: Response, maxBytes: number): Promise<Uint8Array | 'too-large'> {
  const reader = response.body?.getReader();
  if (!reader) {
    const buffered = new Uint8Array(await response.arrayBuffer());
    if (buffered.byteLength > maxBytes) return 'too-large';
    return buffered;
  }
  const chunks: Uint8Array[] = [];
  let total = 0;
  try {
    while (total <= maxBytes) {
      const step = await reader.read();
      if (step.done) break;
      total += step.value.byteLength;
      if (total > maxBytes) return 'too-large';
      chunks.push(step.value);
    }
  } finally {
    await reader.cancel().catch((err: unknown) => {
      console.error('loom audio reader cancel failed', err);
    });
  }
  const out = new Uint8Array(total);
  let offset = 0;
  for (const chunk of chunks) {
    out.set(chunk, offset);
    offset += chunk.byteLength;
  }
  return out;
}

async function fetchChecked(
  fetchImpl: LoomFetch,
  assertPublic: (input: string) => Promise<URL>,
  rawUrl: string,
  init: RequestInit,
  timeoutMs: number,
): Promise<Response> {
  let current = rawUrl;
  for (let hop = 0; hop < 3; hop += 1) {
    const checked = await assertPublic(current);
    if (checked.protocol !== 'https:') {
      throw new LoomAudioError(LOOM_AUDIO_UNAVAILABLE, 'loom_audio_unavailable', 422);
    }
    const response = await fetchImpl(checked.toString(), {
      ...init,
      redirect: 'manual',
      signal: AbortSignal.timeout(timeoutMs),
    });
    if (response.status >= 300 && response.status < 400) {
      const location = response.headers.get('location');
      if (!location) {
        throw new LoomAudioError(LOOM_AUDIO_UNAVAILABLE, 'loom_audio_unavailable', 422);
      }
      current = new URL(location, checked).toString();
      continue;
    }
    return response;
  }
  throw new LoomAudioError(LOOM_AUDIO_UNAVAILABLE, 'loom_audio_unavailable', 422);
}

function readUrlField(data: unknown): string | null {
  if (!data || typeof data !== 'object') return null;
  const record = data as Record<string, unknown>;
  if (typeof record.url === 'string' && record.url.startsWith('https://')) return record.url;
  const nested = record.data;
  if (!nested || typeof nested !== 'object') return null;
  const video = (nested as Record<string, unknown>).getVideo;
  if (!video || typeof video !== 'object') return null;
  const cdn = (video as Record<string, unknown>).nullableRawCdnUrl;
  if (!cdn || typeof cdn !== 'object') return null;
  const url = (cdn as Record<string, unknown>).url;
  return typeof url === 'string' && url.startsWith('https://') ? url : null;
}

function isPrivateGraphql(data: unknown): boolean {
  if (!data || typeof data !== 'object') return false;
  const video = (data as { data?: { getVideo?: { __typename?: string } } }).data?.getVideo;
  const typename = video?.__typename;
  return typename === 'PrivateVideo' || typename === 'VideoPasswordMissingOrIncorrect';
}

async function postJson(
  fetchImpl: LoomFetch,
  assertPublic: (input: string) => Promise<URL>,
  url: string,
  body: unknown,
  headers: HeadersInit,
): Promise<{ status: number; data: unknown }> {
  const response = await fetchChecked(
    fetchImpl,
    assertPublic,
    url,
    { method: 'POST', headers, body: JSON.stringify(body) },
    15_000,
  );
  if (response.status === 204) return { status: 204, data: null };
  const text = await response.text();
  if (!text.trim()) return { status: response.status, data: null };
  try {
    return { status: response.status, data: JSON.parse(text) as unknown };
  } catch (err) {
    console.error('loom audio JSON parse failed', response.status, err);
    return { status: response.status, data: null };
  }
}

function acceptCandidate(url: string): MediaCandidate['source'] | 'playlist' | null {
  let parsed: URL;
  try {
    parsed = new URL(url);
  } catch {
    return null;
  }
  if (parsed.protocol !== 'https:' || !isLoomMediaHost(parsed.hostname)) return null;
  const kind = loomMediaKind(url);
  if (kind === 'page') return null;
  if (kind === 'file') return 'transcoded-url';
  if (kind === 'playlist') return 'playlist';
  return null;
}

async function probeDirectFile(
  fetchImpl: LoomFetch,
  assertPublic: (input: string) => Promise<URL>,
  mediaUrl: string,
): Promise<string | null> {
  const response = await fetchChecked(
    fetchImpl,
    assertPublic,
    mediaUrl,
    {
      method: 'GET',
      headers: {
        Range: 'bytes=0-4095',
        Accept: 'video/mp4,video/webm,audio/*,application/octet-stream',
        Referer: 'https://www.loom.com/',
      },
    },
    15_000,
  );
  if (response.status !== 200 && response.status !== 206) {
    console.error('loom media probe rejected', response.status);
    return null;
  }
  const contentType = response.headers.get('content-type');
  const sample = await readBounded(response, 4096);
  if (sample === 'too-large') return null;
  if (sample.byteLength === 0 || looksLikeHtml(sample, contentType)) return null;
  const typedMedia = Boolean(contentType && /^(audio|video)\//i.test(contentType));
  if (!typedMedia && !looksLikeMediaContainer(sample)) return null;
  if (contentType && /^(audio|video)\//i.test(contentType)) {
    return contentType.split(';')[0]?.trim() || contentTypeForMediaUrl(mediaUrl) || 'application/octet-stream';
  }
  return contentTypeForMediaUrl(mediaUrl);
}

async function downloadHlsAudio(
  fetchImpl: LoomFetch,
  assertPublic: (input: string) => Promise<URL>,
  playlistUrl: string,
  depth = 0,
): Promise<Uint8Array | null> {
  if (depth > 3) return null;
  let playlistParsed: URL;
  try {
    playlistParsed = new URL(playlistUrl);
  } catch (err) {
    console.error('loom hls playlist URL rejected', err);
    return null;
  }
  if (!isLoomMediaHost(playlistParsed.hostname)) return null;
  const playlist = await fetchChecked(
    fetchImpl,
    assertPublic,
    playlistUrl,
    { method: 'GET', headers: { Accept: 'application/vnd.apple.mpegurl,*/*', Referer: 'https://www.loom.com/' } },
    15_000,
  );
  if (!playlist.ok) return null;
  const playlistType = playlist.headers.get('content-type');
  const playlistBytes = await readBounded(playlist, 1_000_000);
  if (playlistBytes === 'too-large') {
    throw new LoomAudioError(LOOM_AUDIO_TOO_LARGE, 'loom_audio_too_large', 413);
  }
  if (looksLikeHtml(playlistBytes, playlistType)) return null;
  const text = new TextDecoder().decode(playlistBytes);
  const doc = parseHlsDocument(text);
  if (doc.segments.length === 0) {
    const next = doc.audioPlaylist ?? doc.variantPlaylists[0];
    if (!next) return null;
    return downloadHlsAudio(
      fetchImpl,
      assertPublic,
      resolveHlsReference(playlistUrl, next),
      depth + 1,
    );
  }
  const chunks: Uint8Array[] = [];
  let total = 0;
  for (const reference of doc.segments) {
    const segmentUrl = resolveHlsReference(playlistUrl, reference);
    let parsed: URL;
    try {
      parsed = new URL(segmentUrl);
    } catch (err) {
      console.error('loom hls segment URL rejected', err);
      return null;
    }
    if (!isLoomMediaHost(parsed.hostname)) return null;
    const segment = await fetchChecked(
      fetchImpl,
      assertPublic,
      segmentUrl,
      { method: 'GET', headers: { Referer: 'https://www.loom.com/' } },
      20_000,
    );
    if (!segment.ok) return null;
    const bytes = await readBounded(segment, LOOM_HLS_BYTE_CAP - total);
    if (bytes === 'too-large') {
      throw new LoomAudioError(LOOM_AUDIO_TOO_LARGE, 'loom_audio_too_large', 413);
    }
    if (looksLikeHtml(bytes, segment.headers.get('content-type'))) return null;
    chunks.push(bytes);
    total += bytes.byteLength;
  }
  const joined = new Uint8Array(total);
  let offset = 0;
  for (const chunk of chunks) {
    joined.set(chunk, offset);
    offset += chunk.byteLength;
  }
  const aac = extractAdtsAac(joined);
  if (aac.byteLength < 64) return null;
  return aac;
}

async function sessionUrl(
  fetchImpl: LoomFetch,
  assertPublic: (input: string) => Promise<URL>,
  videoId: string,
  endpoint: 'transcoded-url' | 'raw-url',
): Promise<string | null> {
  const posted = await postJson(
    fetchImpl,
    assertPublic,
    `https://www.loom.com/api/campaigns/sessions/${videoId}/${endpoint}`,
    {
      anonID: crypto.randomUUID(),
      deviceID: null,
      force_original: false,
      password: null,
    },
    loomPageHeaders(videoId),
  );
  if (posted.status === 401 || posted.status === 403) {
    throw new LoomAudioError(LOOM_AUDIO_PRIVATE, 'loom_private', 422);
  }
  if (isPrivateGraphql(posted.data)) {
    throw new LoomAudioError(LOOM_AUDIO_PRIVATE, 'loom_private', 422);
  }
  return readUrlField(posted.data);
}

async function graphqlMediaUrl(
  fetchImpl: LoomFetch,
  assertPublic: (input: string) => Promise<URL>,
  videoId: string,
  acceptableMimes: string[],
): Promise<string | null> {
  const posted = await postJson(
    fetchImpl,
    assertPublic,
    'https://www.loom.com/graphql',
    {
      operationName: 'GetVideoSource',
      variables: { videoId, password: null, acceptableMimes },
      query: GRAPHQL_SOURCE,
    },
    {
      ...loomPageHeaders(videoId),
      'x-loom-request-source': 'loom_web_45a5bd4',
      'apollographql-client-name': 'web',
      'apollographql-client-version': '45a5bd4',
      'graphql-operation-name': 'GetVideoSource',
    },
  );
  if (posted.status === 401 || posted.status === 403) {
    throw new LoomAudioError(LOOM_AUDIO_PRIVATE, 'loom_private', 422);
  }
  if (isPrivateGraphql(posted.data)) {
    throw new LoomAudioError(LOOM_AUDIO_PRIVATE, 'loom_private', 422);
  }
  return readUrlField(posted.data);
}

/**
 * Resolve a public Loom share to a direct media URL or AAC bytes.
 * The share/embed watch page is never returned as audio.
 */
export async function acquireLoomAudio(rawUrl: string, deps: AcquireDeps = {}): Promise<AcquiredLoomAudio> {
  const share = parseLoomShareInput(rawUrl);
  if (!share) {
    throw new LoomAudioError(LOOM_URL_INVALID, 'loom_url_invalid', 400);
  }
  const fetchImpl = deps.fetch ?? fetch;
  const assertPublic = deps.assertPublic ?? assertPublicHttpUrl;

  const loaders: Array<() => Promise<{ url: string | null; source: MediaCandidate['source'] }>> = [
    async () => ({ url: await sessionUrl(fetchImpl, assertPublic, share.videoId, 'transcoded-url'), source: 'transcoded-url' }),
    async () => ({ url: await graphqlMediaUrl(fetchImpl, assertPublic, share.videoId, ['MP4']), source: 'graphql-mp4' }),
    async () => ({ url: await graphqlMediaUrl(fetchImpl, assertPublic, share.videoId, ['WEBM']), source: 'graphql-webm' }),
    async () => ({ url: await sessionUrl(fetchImpl, assertPublic, share.videoId, 'raw-url'), source: 'raw-url' }),
  ];

  const playlists: string[] = [];
  for (const load of loaders) {
    let found: { url: string | null; source: MediaCandidate['source'] };
    try {
      found = await load();
    } catch (err) {
      if (err instanceof LoomAudioError) throw err;
      console.error('loom media lookup failed', err);
      continue;
    }
    if (!found.url) continue;
    const accepted = acceptCandidate(found.url);
    if (accepted === 'playlist') {
      playlists.push(found.url);
      continue;
    }
    if (!accepted) continue;
    try {
      const contentType = await probeDirectFile(fetchImpl, assertPublic, found.url);
      if (!contentType) continue;
      return {
        mode: 'url',
        mediaUrl: found.url,
        contentType,
        source: found.source,
        share,
      };
    } catch (err) {
      if (err instanceof LoomAudioError && err.code !== 'loom_audio_unavailable') throw err;
      console.error('loom direct file probe failed', err);
    }
  }

  for (const playlistUrl of playlists) {
    try {
      const bytes = await downloadHlsAudio(fetchImpl, assertPublic, playlistUrl);
      if (!bytes) continue;
      return {
        mode: 'file',
        bytes,
        filename: 'loom-audio.aac',
        contentType: 'audio/aac',
        source: 'hls-audio',
        share,
      };
    } catch (err) {
      if (err instanceof LoomAudioError && err.code === 'loom_audio_too_large') throw err;
      console.error('loom hls extract failed', err);
    }
  }

  throw new LoomAudioError(LOOM_AUDIO_UNAVAILABLE, 'loom_audio_unavailable', 422);
}
