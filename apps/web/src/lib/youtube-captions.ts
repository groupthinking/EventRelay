import 'server-only';

import { ProxyAgent, fetch as undiciFetch } from 'undici';
import {
  resolveCaptionTransport,
  timedtextLooksBlocked,
} from '@/lib/caption-transport';
import { extractVideoId } from '@/lib/youtube-metadata';

const ANDROID_UA = 'com.google.android.youtube/20.10.38 (Linux; U; Android 10)';

export interface CaptionSegment {
  start: number;
  duration: number;
  text: string;
}

export interface CaptionTrack {
  baseUrl: string;
  languageCode?: string;
  kind?: string;
}

export function extractYtInitialPlayerResponse(html: string): Record<string, unknown> | null {
  const marker = 'ytInitialPlayerResponse';
  const idx = html.indexOf(marker);
  if (idx < 0) return null;
  const brace = html.indexOf('{', idx);
  if (brace < 0) return null;
  let depth = 0;
  for (let i = brace; i < html.length; i++) {
    const ch = html[i];
    if (ch === '{') depth += 1;
    else if (ch === '}') {
      depth -= 1;
      if (depth === 0) {
        try {
          return JSON.parse(html.slice(brace, i + 1)) as Record<string, unknown>;
        } catch {
          return null;
        }
      }
    }
  }
  return null;
}

export function captionTracksFromPlayer(player: Record<string, unknown> | null): CaptionTrack[] {
  const captions = player?.captions as Record<string, unknown> | undefined;
  const list = captions?.playerCaptionsTracklistRenderer as Record<string, unknown> | undefined;
  const tracks = list?.captionTracks;
  if (!Array.isArray(tracks)) return [];
  return tracks.flatMap((raw) => {
    if (!raw || typeof raw !== 'object') return [];
    const row = raw as Record<string, unknown>;
    const baseUrl = typeof row.baseUrl === 'string' ? row.baseUrl.replace(/\\u0026/g, '&') : '';
    if (!baseUrl.startsWith('https://www.youtube.com/api/timedtext')) return [];
    return [{
      baseUrl,
      languageCode: typeof row.languageCode === 'string' ? row.languageCode : undefined,
      kind: typeof row.kind === 'string' ? row.kind : undefined,
    }];
  });
}

export function pickCaptionTrack(tracks: CaptionTrack[], language = 'en'): CaptionTrack | null {
  if (tracks.length === 0) return null;
  const lang = language.toLowerCase();
  const manualEn = tracks.find(
    (track) => (track.languageCode || '').toLowerCase().startsWith(lang) && track.kind !== 'asr',
  );
  if (manualEn) return manualEn;
  const anyEn = tracks.find((track) => (track.languageCode || '').toLowerCase().startsWith(lang));
  return anyEn || tracks[0];
}

export function parseJson3Captions(payload: unknown): CaptionSegment[] {
  if (!payload || typeof payload !== 'object') return [];
  const events = (payload as { events?: unknown }).events;
  if (!Array.isArray(events)) return [];
  const segments: CaptionSegment[] = [];
  for (const event of events) {
    if (!event || typeof event !== 'object') continue;
    const row = event as { tStartMs?: unknown; dDurationMs?: unknown; segs?: unknown };
    const segs = Array.isArray(row.segs) ? row.segs : [];
    const text = segs
      .map((seg) =>
        seg && typeof seg === 'object' && typeof (seg as { utf8?: unknown }).utf8 === 'string'
          ? (seg as { utf8: string }).utf8
          : '',
      )
      .join('')
      .replace(/\n/g, ' ')
      .trim();
    if (!text) continue;
    const startMs = typeof row.tStartMs === 'number' ? row.tStartMs : 0;
    const durationMs = typeof row.dDurationMs === 'number' ? row.dDurationMs : 0;
    segments.push({
      start: startMs / 1000,
      duration: durationMs / 1000,
      text,
    });
  }
  return segments;
}

export function parseCaptionXml(xml: string): CaptionSegment[] {
  if (!xml.trim()) return [];
  const segments: CaptionSegment[] = [];
  const node = /<text\b([^>]*)>([\s\S]*?)<\/text>/gi;
  let match: RegExpExecArray | null;
  while ((match = node.exec(xml))) {
    const attrs = match[1];
    const start = Number(/start="([^"]+)"/.exec(attrs)?.[1] ?? 0);
    const duration = Number(/dur="([^"]+)"/.exec(attrs)?.[1] ?? 0);
    const text = decodeCaptionText(match[2]);
    if (!text) continue;
    segments.push({
      start: Number.isFinite(start) ? start : 0,
      duration: Number.isFinite(duration) ? duration : 0,
      text,
    });
  }
  return segments;
}

function decodeCaptionText(raw: string): string {
  return raw
    .replace(/<!\[CDATA\[([\s\S]*?)\]\]>/g, '$1')
    .replace(/&amp;/g, '&')
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'")
    .replace(/\n/g, ' ')
    .trim();
}

function innertubeKeyFromHtml(html: string): string | null {
  return html.match(/"INNERTUBE_API_KEY":"([^"]+)"/)?.[1] || null;
}

type CaptionFetch = {
  transcript: string;
  segments: CaptionSegment[];
  source: string;
};

/**
 * Pull timed YouTube captions the same way a local agent would:
 * watch page → Innertube ANDROID player → timedtext XML.
 *
 * WEB player timedtext URLs come back empty. ANDROID caption URLs return
 * the spoken transcript. Vercel IPs are blocked, so hosted runs tunnel the
 * three requests through the same Webshare rotating residential proxy as
 * the Python backend.
 */
export async function fetchYouTubeCaptions(
  url: string,
  language = 'en',
): Promise<CaptionFetch | null> {
  const videoId = extractVideoId(url);
  if (!videoId) return null;

  const transport = resolveCaptionTransport();
  const attempts = transport.proxyUrl ? 3 : 1;
  for (let attempt = 1; attempt <= attempts; attempt += 1) {
    const result = await fetchYouTubeCaptionsOnce(videoId, language, transport.proxyUrl);
    if (result) return result;
    console.warn(
      `[youtube-captions] ${transport.kind} attempt ${attempt}/${attempts} missed`,
    );
  }
  return null;
}

async function fetchYouTubeCaptionsOnce(
  videoId: string,
  language: string,
  proxyUrl: string | null,
): Promise<CaptionFetch | null> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 25_000);
  const headers = {
    'User-Agent': ANDROID_UA,
    'Accept-Language': 'en-US,en;q=0.9',
  };
  const dispatcher = proxyUrl
    ? new ProxyAgent({ uri: proxyUrl, connections: 1, pipelining: 0 })
    : undefined;

  const youtubeFetch = async (input: string, init?: Parameters<typeof undiciFetch>[1]) =>
    undiciFetch(input, {
      ...init,
      headers: { ...headers, ...(init?.headers as Record<string, string> | undefined) },
      signal: controller.signal,
      ...(dispatcher ? { dispatcher } : {}),
    });

  try {
    const watch = await youtubeFetch(`https://www.youtube.com/watch?v=${videoId}`);
    if (!watch.ok) return null;
    const html = await watch.text();
    const apiKey = innertubeKeyFromHtml(html);
    if (!apiKey) return null;

    const playerRes = await youtubeFetch(
      `https://www.youtube.com/youtubei/v1/player?key=${apiKey}`,
      {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({
          context: {
            client: {
              clientName: 'ANDROID',
              clientVersion: '20.10.38',
              hl: 'en',
              gl: 'US',
            },
          },
          videoId,
        }),
      },
    );
    if (!playerRes.ok) return null;
    const player = (await playerRes.json()) as Record<string, unknown>;
    const track = pickCaptionTrack(captionTracksFromPlayer(player), language);
    if (!track) return null;
    const captionUrl = track.baseUrl.replace(/&fmt=\w+$/, '');

    const xmlRes = await youtubeFetch(captionUrl, {
      headers: { accept: 'application/xml' },
    });
    if (!xmlRes.ok) return null;
    const xmlType = xmlRes.headers.get('content-type') || '';
    const xmlBody = await xmlRes.text();
    if (!timedtextLooksBlocked(xmlType, xmlBody)) {
      const segments = parseCaptionXml(xmlBody);
      const transcript = segments.map((segment) => segment.text).join(' ').replace(/\s+/g, ' ').trim();
      if (transcript.length >= 40) {
        return { transcript, segments, source: 'youtube-captions' };
      }
    }

    const jsonRes = await youtubeFetch(
      captionUrl.includes('fmt=') ? captionUrl : `${captionUrl}&fmt=json3`,
      { headers: { accept: 'application/json' } },
    );
    if (!jsonRes.ok) return null;
    const jsonType = jsonRes.headers.get('content-type') || '';
    const jsonBody = await jsonRes.text();
    if (timedtextLooksBlocked(jsonType, jsonBody)) return null;
    try {
      const segments = parseJson3Captions(JSON.parse(jsonBody) as unknown);
      const transcript = segments.map((segment) => segment.text).join(' ').replace(/\s+/g, ' ').trim();
      if (transcript.length < 40) return null;
      return { transcript, segments, source: 'youtube-captions' };
    } catch {
      return null;
    }
  } catch (error) {
    console.warn('[youtube-captions] fetch failed:', error);
    return null;
  } finally {
    clearTimeout(timeout);
    if (dispatcher) {
      try {
        await dispatcher.close();
      } catch {
        // ignore close races after abort
      }
    }
  }
}
