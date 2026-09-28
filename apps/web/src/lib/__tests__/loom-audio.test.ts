import { afterEach, describe, expect, it, vi } from 'vitest';
import {
  acquireLoomAudio,
  LOOM_AUDIO_PRIVATE,
  LOOM_AUDIO_UNAVAILABLE,
  LoomAudioError,
} from '@/lib/loom-audio';

const ID = 'c43a642f815f4378b6f80a889bb73d8d';
const SHARE = `https://www.loom.com/share/${ID}`;
const MP4 = `https://cdn.loom.com/sessions/transcoded/${ID}.mp4?Policy=test`;
const MASTER = `https://luna.loom.com/id/${ID}/resource/hls/playlist.m3u8?Policy=test`;

const assertPublic = async (input: string) => new URL(input);

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'content-type': 'application/json' },
  });
}

function adtsBytes(): Uint8Array<ArrayBuffer> {
  const payload = new Uint8Array(80).fill(0x22);
  const frameLength = 7 + payload.length;
  const frame = new Uint8Array(frameLength);
  frame[0] = 0xff;
  frame[1] = 0xf1;
  frame[2] = 0x50;
  frame[3] = (frameLength >> 11) & 0x03;
  frame[4] = (frameLength >> 3) & 0xff;
  frame[5] = (frameLength & 7) << 5;
  frame[6] = 0xfc;
  frame.set(payload, 7);
  return frame;
}

afterEach(() => {
  vi.restoreAllMocks();
});

describe('acquireLoomAudio', () => {
  it('returns a probed cdn mp4 and never the share page', async () => {
    const requested: string[] = [];
    const ftyp = new Uint8Array([0, 0, 0, 0x18, 0x66, 0x74, 0x79, 0x70, 0, 0, 0, 0]);
    const fetchImpl = vi.fn(async (input: string, init?: RequestInit) => {
      requested.push(`${init?.method ?? 'GET'} ${input}`);
      if (input.includes('/transcoded-url')) {
        return jsonResponse({ url: MP4 });
      }
      if (input.startsWith('https://cdn.loom.com/')) {
        return new Response(ftyp, { status: 206, headers: { 'content-type': 'video/mp4' } });
      }
      return new Response('', { status: 500 });
    });

    const audio = await acquireLoomAudio(SHARE, { fetch: fetchImpl, assertPublic });
    expect(audio.mode).toBe('url');
    if (audio.mode !== 'url') return;
    expect(audio.mediaUrl).toBe(MP4);
    expect(audio.contentType).toBe('video/mp4');
    expect(audio.mediaUrl).not.toContain('/share/');
    expect(requested.some((line) => line.startsWith('GET https://www.loom.com/share/'))).toBe(false);
    expect(requested.some((line) => line.includes('/graphql'))).toBe(false);
  });

  it('fails closed when the only body is the watch-page HTML', async () => {
    const fetchImpl = vi.fn(async (input: string) => {
      if (input.includes('/transcoded-url')) {
        return jsonResponse({ url: MP4 });
      }
      if (input.startsWith('https://cdn.loom.com/')) {
        return new Response('<!doctype html><html><title>Loom</title>', {
          status: 200,
          headers: { 'content-type': 'text/html' },
        });
      }
      if (input.includes('/graphql') || input.includes('/raw-url')) {
        return new Response(null, { status: 204 });
      }
      return new Response('', { status: 404 });
    });

    await expect(acquireLoomAudio(SHARE, { fetch: fetchImpl, assertPublic })).rejects.toMatchObject({
      message: LOOM_AUDIO_UNAVAILABLE,
      code: 'loom_audio_unavailable',
      status: 422,
    });
  });

  it('extracts AAC bytes from an HLS audio rendition when no direct file exists', async () => {
    const fetchImpl = vi.fn(async (input: string, init?: RequestInit) => {
      const method = init?.method ?? 'GET';
      const url = new URL(input);
      if (method === 'POST' && url.pathname.endsWith('/transcoded-url')) {
        return new Response(null, { status: 204 });
      }
      if (method === 'POST' && url.pathname === '/graphql') {
        const body = String(init?.body ?? '');
        if (body.includes('"MP4"')) {
          return jsonResponse({
            data: {
              getVideo: {
                __typename: 'RegularUserVideo',
                nullableRawCdnUrl: { url: MASTER },
              },
            },
          });
        }
        return jsonResponse({ data: { getVideo: { __typename: 'RegularUserVideo', nullableRawCdnUrl: null } } });
      }
      if (method === 'POST' && url.pathname.endsWith('/raw-url')) {
        return new Response(null, { status: 204 });
      }
      if (url.pathname.endsWith('/playlist.m3u8')) {
        return new Response(
          [
            '#EXTM3U',
            '#EXT-X-MEDIA:TYPE=AUDIO,GROUP-ID="audio",NAME="audio",URI="audio.m3u8"',
            '#EXT-X-STREAM-INF:BANDWIDTH=800000',
            'video.m3u8',
          ].join('\n'),
          { status: 200, headers: { 'content-type': 'application/vnd.apple.mpegurl' } },
        );
      }
      if (url.pathname.endsWith('/audio.m3u8')) {
        return new Response('#EXTM3U\n#EXTINF:4.0,\nseg0.ts\n#EXT-X-ENDLIST\n', {
          status: 200,
          headers: { 'content-type': 'application/vnd.apple.mpegurl' },
        });
      }
      if (url.pathname.endsWith('/seg0.ts')) {
        return new Response(adtsBytes(), { status: 200, headers: { 'content-type': 'video/MP2T' } });
      }
      return new Response('', { status: 404 });
    });

    const audio = await acquireLoomAudio(SHARE, { fetch: fetchImpl, assertPublic });
    expect(audio.mode).toBe('file');
    if (audio.mode !== 'file') return;
    expect(audio.contentType).toBe('audio/aac');
    expect(audio.bytes.byteLength).toBeGreaterThan(64);
    expect(audio.bytes[0]).toBe(0xff);
    expect(audio.share.shareUrl).toBe(SHARE);
  });

  it('fails closed on a private share', async () => {
    const fetchImpl = vi.fn(async (input: string) => {
      if (input.includes('/transcoded-url')) return new Response(null, { status: 204 });
      if (input.includes('/graphql')) {
        return jsonResponse({ data: { getVideo: { __typename: 'PrivateVideo' } } });
      }
      return new Response('', { status: 500 });
    });
    const error = await acquireLoomAudio(SHARE, { fetch: fetchImpl, assertPublic }).catch((err: unknown) => err);
    expect(error).toBeInstanceOf(LoomAudioError);
    expect(error).toMatchObject({ message: LOOM_AUDIO_PRIVATE, code: 'loom_private' });
  });
});

const live = process.env.LOOM_LIVE_PROBE === '1';

(live ? describe : describe.skip)('acquireLoomAudio live public shares', () => {
  it('resolves the known transcoded mp4 share to cdn.loom.com', async () => {
    const audio = await acquireLoomAudio('https://www.loom.com/share/c43a642f815f4378b6f80a889bb73d8d');
    expect(audio.mode).toBe('url');
    if (audio.mode !== 'url') return;
    const media = new URL(audio.mediaUrl);
    expect(media.hostname).toBe('cdn.loom.com');
    expect(media.pathname.endsWith('.mp4')).toBe(true);
    expect(media.pathname).not.toContain('/share/');
  }, 30_000);

  it('turns an HLS-only public share into AAC bytes', async () => {
    const audio = await acquireLoomAudio('https://www.loom.com/share/43d05f362f734614a2e81b4694a3a523');
    expect(audio.mode).toBe('file');
    if (audio.mode !== 'file') return;
    expect(audio.bytes.byteLength).toBeGreaterThan(64);
    expect(audio.bytes[0]).toBe(0xff);
  }, 30_000);
});
