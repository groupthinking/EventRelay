import { afterEach, describe, expect, it, vi } from 'vitest';
import {
  applyStudioQueryAutoStart,
  resolveStudioHandoff,
  studioVideoHref,
  submitHomePaste,
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

describe('submitHomePaste kicks pack emit then hands off to Studio', () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it('POSTs the watch URL to /api/video/pack and returns /studio?video=', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 202,
      json: async () => ({ status: 'processing' }),
    });
    vi.stubGlobal('fetch', fetchMock);

    const href = submitHomePaste(FIXTURE_ID);
    expect(href).toBe(`/studio?video=${encodeURIComponent(FIXTURE_WATCH)}`);

    await vi.waitFor(() => {
      expect(fetchMock).toHaveBeenCalled();
    });
    expect(fetchMock.mock.calls[0]?.[0]).toBe('/api/video/pack');
    const init = fetchMock.mock.calls[0]?.[1] as RequestInit;
    expect(init.method).toBe('POST');
    expect(String(init.body)).toContain(FIXTURE_WATCH);
  });

  it('does not emit a pack for junk input', () => {
    const fetchMock = vi.fn();
    vi.stubGlobal('fetch', fetchMock);
    expect(submitHomePaste('not a youtube url')).toBeNull();
    expect(fetchMock).not.toHaveBeenCalled();
  });
});

describe('applyStudioQueryAutoStart (?video= one-shot, Strict Mode safe)', () => {
  it('starts once with the canonical watch URL across a Strict Mode double effect', () => {
    const startedKey = { current: null as string | null };
    const start = vi.fn();
    const onResolved = vi.fn();

    const first = applyStudioQueryAutoStart({
      query: FIXTURE_ID,
      startedKey,
      start,
      onResolved,
    });
    const remount = applyStudioQueryAutoStart({
      query: FIXTURE_ID,
      startedKey,
      start,
      onResolved,
    });
    const sameQueryRerender = applyStudioQueryAutoStart({
      query: FIXTURE_WATCH,
      startedKey,
      start,
      onResolved,
    });

    expect(first).toBe('started');
    expect(remount).toBe('already');
    expect(sameQueryRerender).toBe('already');
    expect(start).toHaveBeenCalledTimes(1);
    expect(start).toHaveBeenCalledWith(FIXTURE_WATCH);
    expect(onResolved).toHaveBeenCalledWith(FIXTURE_WATCH);
    expect(startedKey.current).toBe(FIXTURE_ID);
  });

  it('does not start analysis for junk or empty query', () => {
    const startedKey = { current: null as string | null };
    const start = vi.fn();
    const onInvalidQuery = vi.fn();

    expect(
      applyStudioQueryAutoStart({ query: null, startedKey, start, onInvalidQuery }),
    ).toBe('skipped');
    expect(
      applyStudioQueryAutoStart({
        query: 'not a youtube url',
        startedKey,
        start,
        onInvalidQuery,
      }),
    ).toBe('invalid');
    expect(start).not.toHaveBeenCalled();
    expect(onInvalidQuery).toHaveBeenCalledWith('not a youtube url');
  });
});
