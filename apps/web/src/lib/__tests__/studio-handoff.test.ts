import { afterEach, describe, expect, it, vi } from 'vitest';
import {
  applyStudioQueryAutoStart,
  resetStudioQueryAutoStart,
  resolveStudioHandoff,
  studioQueryFromSearchParams,
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
  afterEach(() => {
    // Release the module-level Strict Mode guard so tests stay isolated.
    resetStudioQueryAutoStart();
  });

  it('re-starts the same video after a genuine unmount clears the guard', () => {
    const start = vi.fn();
    const firstMountKey = { current: null as string | null };
    const first = applyStudioQueryAutoStart({
      query: FIXTURE_WATCH,
      startedKey: firstMountKey,
      start,
    });
    expect(first).toBe('started');

    // Genuine unmount releases the module-level guard.
    resetStudioQueryAutoStart();

    // Fresh mount (fresh ref) re-navigates to the same video.
    const remountKey = { current: null as string | null };
    const remount = applyStudioQueryAutoStart({
      query: FIXTURE_WATCH,
      startedKey: remountKey,
      start,
    });
    expect(remount).toBe('started');
    expect(start).toHaveBeenCalledTimes(2);
  });

  it('suppresses duplicate start when a Strict Mode remount gets a fresh ref object', () => {
    const remountWatchUrl = 'https://www.youtube.com/watch?v=pBsT6v-ciO8';
    const firstMountKey = { current: null as string | null };
    const remountKey = { current: null as string | null };
    const start = vi.fn();
    const first = applyStudioQueryAutoStart({
      query: remountWatchUrl,
      startedKey: firstMountKey,
      start,
    });
    const remount = applyStudioQueryAutoStart({
      query: remountWatchUrl,
      startedKey: remountKey,
      start,
    });
    expect(first).toBe('started');
    expect(remount).toBe('already');
    expect(start).toHaveBeenCalledTimes(1);
  });

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

describe('studioQueryFromSearchParams (unencoded Home/share handoff)', () => {
  const HAYDEN_ID = 'pBsT6v-ciO8';
  const HAYDEN_WATCH = `https://www.youtube.com/watch?v=${HAYDEN_ID}`;

  it('reads Hayden\'s unencoded /studio?video= watch URL as one video param', () => {
    const params = new URL(
      `https://uvai.io/studio?video=https://www.youtube.com/watch?v=${HAYDEN_ID}`,
    ).searchParams;
    expect(params.get('video')).toBe(HAYDEN_WATCH);
    expect(params.get('v')).toBeNull();
    expect(studioQueryFromSearchParams(params)).toBe(HAYDEN_WATCH);
  });

  it('reconstructs watch?v= when a proxy splits video and v onto sibling params', () => {
    const split = new URLSearchParams(`video=https://www.youtube.com/watch&v=${HAYDEN_ID}`);
    expect(split.get('video')).toBe('https://www.youtube.com/watch');
    expect(split.get('v')).toBe(HAYDEN_ID);
    expect(studioQueryFromSearchParams(split)).toBe(HAYDEN_WATCH);
  });

  it('keeps an encoded ?video= watch URL intact', () => {
    const encoded = new URLSearchParams(`video=${encodeURIComponent(HAYDEN_WATCH)}`);
    expect(encoded.get('video')).toBe(HAYDEN_WATCH);
    expect(studioQueryFromSearchParams(encoded)).toBe(HAYDEN_WATCH);
  });

  it('starts analysis from the Hayden URL via searchParams', () => {
    const startedKey = { current: null as string | null };
    const start = vi.fn();
    const onResolved = vi.fn();
    const params = new URL(
      `https://uvai.io/studio?video=https://www.youtube.com/watch?v=${HAYDEN_ID}`,
    ).searchParams;

    const result = applyStudioQueryAutoStart({
      searchParams: params,
      startedKey,
      start,
      onResolved,
    });

    expect(result).toBe('started');
    expect(start).toHaveBeenCalledWith(HAYDEN_WATCH);
    expect(onResolved).toHaveBeenCalledWith(HAYDEN_WATCH);
  });
});
