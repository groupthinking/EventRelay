import { describe, expect, it } from 'vitest';
import {
  resolveStudioHandoff,
  studioVideoHref,
  youtubeWatchUrlFromInput,
} from '@/lib/studio-handoff';
import { CANONICAL_STUDIO_PATH } from '@/lib/auth-paths';

const FIXTURE_ID = 'auJzb1D-fag';
const FIXTURE_WATCH = `https://www.youtube.com/watch?v=${FIXTURE_ID}`;

describe('studio handoff from Home paste', () => {
  it('builds a watch URL and /studio?video= path from a YouTube URL', () => {
    const handoff = resolveStudioHandoff(FIXTURE_WATCH);
    expect(handoff).not.toBeNull();
    expect(handoff?.videoId).toBe(FIXTURE_ID);
    expect(handoff?.watchUrl).toBe(FIXTURE_WATCH);
    expect(handoff?.href).toBe(`/studio?video=${encodeURIComponent(FIXTURE_WATCH)}`);
    expect(CANONICAL_STUDIO_PATH).toBe('/studio');
  });

  it('accepts a raw video id and youtu.be URLs', () => {
    expect(youtubeWatchUrlFromInput(FIXTURE_ID)).toBe(FIXTURE_WATCH);
    expect(youtubeWatchUrlFromInput(`https://youtu.be/${FIXTURE_ID}`)).toBe(FIXTURE_WATCH);
    expect(studioVideoHref(`  ${FIXTURE_ID}  `)).toBe(
      `/studio?video=${encodeURIComponent(FIXTURE_WATCH)}`,
    );
  });

  it('rejects junk so Home cannot invent a toy destination', () => {
    expect(resolveStudioHandoff('not a youtube url')).toBeNull();
    expect(resolveStudioHandoff('https://example.com/watch?v=nope')).toBeNull();
    expect(studioVideoHref('')).toBeNull();
  });
});
