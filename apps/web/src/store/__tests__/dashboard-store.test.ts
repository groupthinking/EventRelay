import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { useDashboardStore } from '@/store/dashboard-store';
import type { Video } from '@/store/dashboard-store';

// ── helpers ──

/** Reset only the data slice so the bound action functions stay intact. */
function resetStore() {
  useDashboardStore.setState({
    videos: [],
    selectedVideoId: null,
    loading: false,
    searchQuery: '',
    searchResults: [],
    searchLoading: false,
  });
}

const store = () => useDashboardStore.getState();

function makeVideo(over: Partial<Video> = {}): Video {
  return {
    id: 'v1',
    title: 'Test video',
    url: 'https://youtu.be/abc',
    status: 'processing',
    progress: 0,
    ...over,
  };
}

/** Minimal JSON Response-like object for mocking fetch. */
function jsonResponse(data: unknown, ok = true, status = 200): Response {
  return {
    ok,
    status,
    json: async () => data,
    text: async () => JSON.stringify(data),
  } as unknown as Response;
}

/** Build a fake SSE Response whose body streams the given events as `data:` lines. */
function sseResponse(events: Array<Record<string, unknown>>, ok = true): Response {
  const encoder = new TextEncoder();
  const body = ok
    ? new ReadableStream<Uint8Array>({
        start(controller) {
          for (const e of events) {
            controller.enqueue(encoder.encode(`data: ${JSON.stringify(e)}\n\n`));
          }
          controller.close();
        },
      })
    : null;
  return {
    ok,
    status: ok ? 200 : 503,
    body,
    headers: {
      get: (name: string) => (name === 'X-Pipeline-Mode' ? 'gemini-direct' : null),
    },
    json: async () => ({}),
    text: async () => '',
  } as unknown as Response;
}

beforeEach(() => {
  resetStore();
});

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
  vi.useRealTimers();
});

describe('dashboard-store · synchronous reducers', () => {
  it('addVideo prepends newest first', () => {
    store().addVideo(makeVideo({ id: 'a' }));
    store().addVideo(makeVideo({ id: 'b' }));
    expect(store().videos.map((v) => v.id)).toEqual(['b', 'a']);
  });

  it('updateVideo patches the matching video and leaves others untouched', () => {
    store().addVideo(makeVideo({ id: 'a', progress: 0 }));
    store().addVideo(makeVideo({ id: 'b', progress: 0 }));
    store().updateVideo('a', { progress: 80, status: 'complete' });
    const a = store().videos.find((v) => v.id === 'a')!;
    const b = store().videos.find((v) => v.id === 'b')!;
    expect(a.progress).toBe(80);
    expect(a.status).toBe('complete');
    expect(b.progress).toBe(0);
  });

  it('updateVideo is a no-op for an unknown id', () => {
    store().addVideo(makeVideo({ id: 'a', progress: 10 }));
    store().updateVideo('missing', { progress: 99 });
    expect(store().videos[0].progress).toBe(10);
  });

  it('removeVideo removes the video and clears selection when it was selected', () => {
    store().addVideo(makeVideo({ id: 'a' }));
    store().selectVideo('a');
    store().removeVideo('a');
    expect(store().videos).toHaveLength(0);
    expect(store().selectedVideoId).toBeNull();
  });

  it('removeVideo keeps selection when a different video is removed', () => {
    store().addVideo(makeVideo({ id: 'a' }));
    store().addVideo(makeVideo({ id: 'b' }));
    store().selectVideo('a');
    store().removeVideo('b');
    expect(store().selectedVideoId).toBe('a');
  });

  it('selectVideo sets the id and resets search state', () => {
    store().setSearchQuery('hello');
    useDashboardStore.setState({
      searchResults: [{ start: 0, duration: 1, text: 't', score: 1 }],
    });
    store().selectVideo('v1');
    expect(store().selectedVideoId).toBe('v1');
    expect(store().searchQuery).toBe('');
    expect(store().searchResults).toEqual([]);
  });

  it('selectedVideo selector returns the selected video or undefined', () => {
    store().addVideo(makeVideo({ id: 'a', title: 'Alpha' }));
    expect(store().selectedVideo()).toBeUndefined();
    store().selectVideo('a');
    expect(store().selectedVideo()?.title).toBe('Alpha');
  });

  it('setLoading and setSearchQuery update their flags', () => {
    store().setLoading(true);
    expect(store().loading).toBe(true);
    store().setSearchQuery('q');
    expect(store().searchQuery).toBe('q');
  });
});

const VIDEO_PACK_BODY = {
  status: 'success',
  data: {
    version: 'v0',
    id: 'vp:v0:auJzb1D-fag',
    video_id: 'auJzb1D-fag',
    source_url: 'https://www.youtube.com/watch?v=auJzb1D-fag',
    transcript: { full_text: 'cite:youtube:auJzb1D-fag', segments: [] },
    provenance: {
      source_hash: '2778c5fc08a1b7f19fe0a83bca959e24ecf20040c3cc1a3b6edd244d68c5e4ea',
    },
  },
};

const VIDEO_PACK_CITATION = {
  version: 'v0',
  videoId: 'auJzb1D-fag',
  packId: 'vp:v0:auJzb1D-fag',
  sourceUrl: 'https://www.youtube.com/watch?v=auJzb1D-fag',
  sourceHash: '2778c5fc08a1b7f19fe0a83bca959e24ecf20040c3cc1a3b6edd244d68c5e4ea',
  pack: {
    version: 'v0',
    id: 'vp:v0:auJzb1D-fag',
    video_id: 'auJzb1D-fag',
    source_url: 'https://www.youtube.com/watch?v=auJzb1D-fag',
    provenance: {
      source_hash: '2778c5fc08a1b7f19fe0a83bca959e24ecf20040c3cc1a3b6edd244d68c5e4ea',
    },
    transcript: {
      language: null,
      full_text: 'cite:youtube:auJzb1D-fag',
      segments: [],
    },
  },
};

describe('dashboard-store · processVideo (durable evidence workflow)', () => {
  const provenance = {
    sourceUrl: 'https://www.youtube.com/watch?v=auJzb1D-fag',
    sourceHost: 'www.youtube.com',
    acquisitionMethod: 'backend-caption-api',
    transcriptSource: 'youtube-captions',
    transcriptVerified: true,
    acquiredAt: '2026-08-16T12:00:00.000Z',
    segmentCount: 1,
    timedSegmentCount: 1,
    durationCoverageSeconds: 12,
    contentSha256: 'abc123',
    warnings: [],
  };
  const quality = {
    state: 'verified',
    passed: true,
    issues: [],
    transcriptCharacters: 70,
    segmentCount: 1,
    timedSegmentCount: 1,
    checkedAt: '2026-08-16T12:00:02.000Z',
  };

  it('persists the run id and maps only a verified result to complete', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse(VIDEO_PACK_BODY))
      .mockResolvedValueOnce(jsonResponse({
        ok: true,
        runId: 'wrun_verified',
        statusUrl: '/api/workflows/video-to-actions/wrun_verified',
      }))
      .mockResolvedValueOnce(jsonResponse({
        ok: true,
        runId: 'wrun_verified',
        runStatus: 'completed',
        result: {
          url: provenance.sourceUrl,
          transcriptChars: 70,
          actionCount: 1,
          provider: 'gateway:google/gemini-2.5-flash',
          actions: [{ tool: 'review_action', status: 'proposed', result: 'Review evidence' }],
          provenance,
          quality,
          analysis: {
            title: 'Verified Video',
            summary: 'A source-backed summary.',
            transcript: [{
              start: 0,
              duration: 12,
              text: 'This is verified source speech with enough content for the quality gate.',
            }],
            events: [{
              timestamp: 4,
              label: 'Key point',
              description: 'A traceable event.',
              codeMapping: 'review()',
              cloudService: 'none',
            }],
            actions: [
              'Review the verified caption evidence.',
              { title: 'Review evidence', description: 'Inspect it.', category: 'research', estimatedMinutes: 5 },
            ],
            topics: ['evidence'],
            architectureCode: '',
            ingestScript: '',
            e22Snippets: [],
            provenance,
            quality,
          },
        },
      }));
    vi.stubGlobal('fetch', fetchMock);

    const id = await store().processVideo(provenance.sourceUrl);
    const video = store().videos.find((item) => item.id === id)!;

    expect(fetchMock).toHaveBeenNthCalledWith(
      1,
      '/api/video/pack',
      expect.objectContaining({ method: 'POST' }),
    );
    expect(fetchMock).toHaveBeenNthCalledWith(
      2,
      '/api/workflows/video-to-actions',
      expect.objectContaining({ method: 'POST' }),
    );
    expect(fetchMock).toHaveBeenNthCalledWith(
      3,
      '/api/workflows/video-to-actions/wrun_verified',
      expect.objectContaining({ method: 'GET' }),
    );
    expect(video.videoPack).toEqual(VIDEO_PACK_CITATION);
    expect(video.status).toBe('complete');
    expect(video.runId).toBe('wrun_verified');
    expect(video.quality?.passed).toBe(true);
    expect(video.provenance?.contentSha256).toBe('abc123');
    expect(video.transcript).toContain('[0:00]');
    expect(video.events?.[0].confidence).toBeUndefined();
    expect(video.agents).toHaveLength(3);
    expect(video.insights?.actions).toEqual([
      {
        title: 'Review the verified caption evidence.',
        description: '',
        category: 'recommended',
        estimatedMinutes: null,
      },
      { title: 'Review evidence', description: 'Inspect it.', category: 'research', estimatedMinutes: 5 },
    ]);
    expect(video.insights?.linkedSop?.steps[0]?.title).toBe('Key point');
    expect(video.insights?.linkedSop?.checklist.some((item) => item.source === 'video-sop')).toBe(true);
  });

  it('keeps a failed workflow failed and preserves a recovery record', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse(VIDEO_PACK_BODY))
      .mockResolvedValueOnce(jsonResponse({
        ok: true,
        runId: 'wrun_failed',
        statusUrl: '/api/workflows/video-to-actions/wrun_failed',
      }))
      .mockResolvedValueOnce(jsonResponse({
        ok: true,
        runId: 'wrun_failed',
        runStatus: 'failed',
        error: 'Verified captions or speech-to-text were unavailable.',
      }));
    vi.stubGlobal('fetch', fetchMock);

    const id = await store().processVideo(provenance.sourceUrl);
    const video = store().videos.find((item) => item.id === id)!;

    expect(video.status).toBe('failed');
    expect(video.videoPack?.sourceHash).toBe(
      '2778c5fc08a1b7f19fe0a83bca959e24ecf20040c3cc1a3b6edd244d68c5e4ea',
    );
    expect(video.runId).toBe('wrun_failed');
    expect(video.failure?.stage).toBe('acquisition');
    expect(video.quality?.passed).toBe(false);
    expect(video.insights?.actions).toEqual([]);
    expect(video.title).toContain('Analysis blocked');
  });

  it('emits the identity pack even when the workflow has no transcript', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse(VIDEO_PACK_BODY))
      .mockResolvedValueOnce(jsonResponse({
        ok: true,
        runId: 'wrun_no_speech',
        statusUrl: '/api/workflows/video-to-actions/wrun_no_speech',
      }))
      .mockResolvedValueOnce(jsonResponse({
        ok: true,
        runId: 'wrun_no_speech',
        runStatus: 'failed',
        error: 'No usable transcript. Try another public video.',
      }));
    vi.stubGlobal('fetch', fetchMock);

    const id = await store().processVideo(provenance.sourceUrl);
    const video = store().videos.find((item) => item.id === id)!;

    expect(fetchMock).toHaveBeenNthCalledWith(
      1,
      '/api/video/pack',
      expect.objectContaining({ method: 'POST' }),
    );
    expect(video.videoPack).toEqual(VIDEO_PACK_CITATION);
    expect(video.videoPack?.sourceUrl).toBe('https://www.youtube.com/watch?v=auJzb1D-fag');
    expect(video.transcript).toBeUndefined();
    expect(video.status).toBe('failed');
    expect(video.insights?.summary).toBe(
      'Analysis was not generated because source evidence could not be verified.',
    );
  });

  it('fails closed when no durable run id is created', async () => {
    vi.stubGlobal('fetch', vi.fn()
      .mockResolvedValueOnce(jsonResponse(VIDEO_PACK_BODY))
      .mockResolvedValueOnce(
        jsonResponse({ ok: false, error: 'world not configured' }, false, 500),
      ));

    const id = await store().processVideo(provenance.sourceUrl);
    const video = store().videos.find((item) => item.id === id)!;

    expect(video.status).toBe('failed');
    expect(video.runId).toBeUndefined();
    expect(video.failure?.stage).toBe('start');
  });
});
