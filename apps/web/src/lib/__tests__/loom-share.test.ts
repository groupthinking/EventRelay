import { describe, expect, it } from 'vitest';
import {
  contentTypeForMediaUrl,
  extractAdtsAac,
  looksLikeHtml,
  looksLikeMediaContainer,
  loomMediaKind,
  parseHlsDocument,
  parseLoomShareInput,
  resolveHlsReference,
} from '@/lib/loom-share';

const ID = 'c43a642f815f4378b6f80a889bb73d8d';

describe('parseLoomShareInput', () => {
  it('canonicalizes share and embed URLs', () => {
    expect(parseLoomShareInput(`https://loom.com/share/${ID}?sid=1`)).toEqual({
      videoId: ID,
      shareUrl: `https://www.loom.com/share/${ID}`,
    });
    expect(parseLoomShareInput(`https://www.loom.com/embed/${ID.toUpperCase()}/`)).toEqual({
      videoId: ID,
      shareUrl: `https://www.loom.com/share/${ID}`,
    });
  });

  it('rejects watch-page lookalikes, folders, and non-Loom hosts', () => {
    expect(parseLoomShareInput(`http://www.loom.com/share/${ID}`)).toBeNull();
    expect(parseLoomShareInput(`https://www.loom.com/share/folder/${ID}`)).toBeNull();
    expect(parseLoomShareInput('https://www.loom.com/share/not-an-id')).toBeNull();
    expect(parseLoomShareInput('https://cdn.loom.com/sessions/raw/clip.mp4')).toBeNull();
    expect(parseLoomShareInput('https://www.youtube.com/watch?v=auJzb1D-fag')).toBeNull();
  });
});

describe('loom media classification', () => {
  it('treats the share page as HTML and cdn mp4 as a file', () => {
    expect(loomMediaKind(`https://www.loom.com/share/${ID}`)).toBe('page');
    expect(loomMediaKind(`https://cdn.loom.com/sessions/transcoded/${ID}.mp4?Policy=x`)).toBe('file');
    expect(loomMediaKind('https://luna.loom.com/id/x/playlist.m3u8')).toBe('playlist');
    expect(contentTypeForMediaUrl(`https://cdn.loom.com/sessions/transcoded/${ID}.mp4`)).toBe('video/mp4');
  });

  it('rejects an HTML body even when the URL says mp4', () => {
    const html = new TextEncoder().encode('<!doctype html><html>');
    expect(looksLikeHtml(html, 'video/mp4')).toBe(true);
    expect(looksLikeMediaContainer(html)).toBe(false);
    const ftyp = new Uint8Array([0, 0, 0, 0x18, 0x66, 0x74, 0x79, 0x70]);
    expect(looksLikeHtml(ftyp, 'video/mp4')).toBe(false);
    expect(looksLikeMediaContainer(ftyp)).toBe(true);
  });
});

describe('HLS audio references', () => {
  it('prefers the audio rendition and copies the signed query onto relative URIs', () => {
    const master = [
      '#EXTM3U',
      '#EXT-X-MEDIA:TYPE=AUDIO,GROUP-ID="audio",NAME="audio",DEFAULT=YES,URI="mediaplaylist-audio.m3u8"',
      '#EXT-X-STREAM-INF:BANDWIDTH=1500000',
      'mediaplaylist-video.m3u8',
    ].join('\n');
    const parsed = parseHlsDocument(master);
    expect(parsed.audioPlaylist).toBe('mediaplaylist-audio.m3u8');
    expect(parsed.variantPlaylists).toEqual(['mediaplaylist-video.m3u8']);
    const base = 'https://luna.loom.com/id/x/playlist-split.m3u8?Policy=abc&Signature=def';
    expect(resolveHlsReference(base, parsed.audioPlaylist!)).toBe(
      'https://luna.loom.com/id/x/mediaplaylist-audio.m3u8?Policy=abc&Signature=def',
    );
  });

  it('extracts ADTS frames and ignores a bare HTML document', () => {
    const payload = new Uint8Array(80).fill(0x11);
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
    const wrapped = new Uint8Array(188);
    wrapped[0] = 0x47;
    wrapped.set(frame, 20);
    const extracted = extractAdtsAac(wrapped.subarray(0, 20 + frameLength));
    expect(extracted.byteLength).toBe(frameLength);
    expect(extracted[0]).toBe(0xff);
    expect(extractAdtsAac(new TextEncoder().encode('<!doctype html>')).byteLength).toBe(0);
  });
});
