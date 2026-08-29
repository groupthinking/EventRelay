import { describe, expect, it } from 'vitest';
import {
  captionTracksFromPlayer,
  extractYtInitialPlayerResponse,
  parseCaptionXml,
  parseJson3Captions,
  pickCaptionTrack,
} from '@/lib/youtube-captions';

describe('youtube captions parser', () => {
  it('extracts ytInitialPlayerResponse JSON from a watch page', () => {
    const html =
      '<script>var ytInitialPlayerResponse = {"captions":{"playerCaptionsTracklistRenderer":{"captionTracks":[{"baseUrl":"https://www.youtube.com/api/timedtext?v=auJzb1D-fag\\u0026lang=en","languageCode":"en"}]}}};</script>';
    const player = extractYtInitialPlayerResponse(html);
    const tracks = captionTracksFromPlayer(player);
    expect(tracks).toHaveLength(1);
    expect(tracks[0].baseUrl).toContain('v=auJzb1D-fag');
    expect(tracks[0].languageCode).toBe('en');
  });

  it('prefers manual English captions over ASR', () => {
    const picked = pickCaptionTrack([
      { baseUrl: 'https://www.youtube.com/api/timedtext?v=x&kind=asr', languageCode: 'en', kind: 'asr' },
      { baseUrl: 'https://www.youtube.com/api/timedtext?v=x&lang=en', languageCode: 'en' },
    ]);
    expect(picked?.kind).toBeUndefined();
  });

  it('parses json3 caption events into timed segments', () => {
    const segments = parseJson3Captions({
      events: [
        { tStartMs: 1000, dDurationMs: 2000, segs: [{ utf8: 'Hello' }, { utf8: ' world' }] },
        { tStartMs: 4000, dDurationMs: 500, segs: [{ utf8: '\n' }] },
      ],
    });
    expect(segments).toEqual([{ start: 1, duration: 2, text: 'Hello world' }]);
  });

  it('parses Innertube caption XML', () => {
    const xml =
      '<?xml version="1.0"?><transcript><text start="0.8" dur="5.5">The way we interact with AI is changing.</text></transcript>';
    expect(parseCaptionXml(xml)).toEqual([
      { start: 0.8, duration: 5.5, text: 'The way we interact with AI is changing.' },
    ]);
  });
});
