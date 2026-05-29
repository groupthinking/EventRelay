import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { useDashboardStore } from '@/store/dashboard-store';
import type { Video } from '@/store/dashboard-store';

// ── helpers ──

/** Reset only the data slice so the bound action functions stay intact. */
function resetStore() {
  useDashboardStore.setState({
    videos: [],
    activities: [],
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

/** Minimal Response-like object for mocking fetch. */
function jsonResponse(data: unknown, ok = true, status = 200): Response {
  return {
    ok,
    status,
    json: async () => data,
    text: async () => JSON.stringify(data),
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

  it('addActivity prepends newest first and caps history at 30', () => {
    for (let i = 0; i < 35; i++) store().addActivity(`event ${i}`, 'info');
    const activities = store().activities;
    expect(activities).toHaveLength(30);
    expect(activities[0].event).toBe('event 34');
    expect(typeof activities[0].time).toBe('string');
    expect(activities[0].time.length).toBeGreaterThan(0);
  });

  it('setLoading and setSearchQuery update their flags', () => {
    store().setLoading(true);
    expect(store().loading).toBe(true);
    store().setSearchQuery('q');
    expect(store().searchQuery).toBe('q');
  });
});

describe('dashboard-store · extractEvents', () => {
  it("derives action and topic events from a video's insights", () => {
    store().addVideo(
      makeVideo({
        id: 'v1',
        insights: {
          summary: 's',
          sentiment: 'Neutral',
          actions: [{ title: 'Build it', description: 'do the thing', category: 'build' }],
          topics: ['rust', 'wasm'],
        },
      }),
    );
    store().extractEvents('v1');
    const events = store().videos[0].events!;
    expect(events).toHaveLength(3); // 1 action + 2 topics

    const action = events.find((e) => e.type === 'action')!;
    expect(action.title).toBe('Build it');
    expect(action.confidence).toBe(0.85);
    expect(action.id).toBe('evt_v1_0');

    const topics = events.filter((e) => e.type === 'topic');
    expect(topics.map((t) => t.title)).toEqual(['rust', 'wasm']);
    expect(topics[0].confidence).toBe(0.9);
    expect(topics[0].id).toBe('evt_v1_t0');
  });

  it('is a no-op when the video does not exist', () => {
    expect(() => store().extractEvents('nope')).not.toThrow();
    expect(store().videos).toHaveLength(0);
  });

  it('produces an empty event list when there are no insights', () => {
    store().addVideo(makeVideo({ id: 'v1' }));
    store().extractEvents('v1');
    expect(store().videos[0].events).toEqual([]);
  });
});

describe('dashboard-store · dispatchAgents', () => {
  it('creates two agents per event and completes them on timers', () => {
    vi.useFakeTimers();
    const events = Array.from({ length: 3 }, (_, i) => ({
      id: `e${i}`,
      type: 'action' as const,
      title: `Event ${i}`,
      confidence: 0.8,
    }));
    store().addVideo(makeVideo({ id: 'v1', events }));

    store().dispatchAgents('v1');
    let agents = store().videos[0].agents!;
    expect(agents).toHaveLength(6); // 3 events × 2 agent types
    expect(agents.every((a) => a.status === 'running')).toBe(true);
    expect(new Set(agents.map((a) => a.agent_type))).toEqual(
      new Set(['analyzer', 'content_creator']),
    );

    vi.runAllTimers();
    agents = store().videos[0].agents!;
    expect(agents.every((a) => a.status === 'complete')).toBe(true);
    expect(agents.every((a) => a.progress === 100)).toBe(true);
    expect(agents[0].result).toBeDefined();
  });

  it('caps execution at the first 5 events', () => {
    vi.useFakeTimers();
    const events = Array.from({ length: 7 }, (_, i) => ({
      id: `e${i}`,
      type: 'action' as const,
      title: `Event ${i}`,
      confidence: 0.8,
    }));
    store().addVideo(makeVideo({ id: 'v1', events }));
    store().dispatchAgents('v1');
    expect(store().videos[0].agents).toHaveLength(10); // 5 events × 2
  });

  it('is a no-op when the video has no events', () => {
    store().addVideo(makeVideo({ id: 'v1' }));
    store().dispatchAgents('v1');
    expect(store().videos[0].agents).toBeUndefined();
  });
});

describe('dashboard-store · processVideo (mocked fetch)', () => {
  it('processes a video end-to-end and extracts events', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(
        jsonResponse({
          status: 'complete',
          result: {
            insights: { summary: 'Backend summary', actions: [], sentiment: 'Positive', topics: [] },
            transcript_segments: 3,
            raw_response: { transcript: { text: 'word '.repeat(60) } },
          },
        }),
      )
      .mockResolvedValueOnce(
        jsonResponse({
          success: true,
          data: {
            events: [{ type: 'action', title: 'E1', description: 'd', priority: 'high' }],
            actions: [{ title: 'A', description: 'd', category: 'build' }],
            summary: 'Final summary',
            topics: ['t2'],
          },
        }),
      );
    vi.stubGlobal('fetch', fetchMock);

    const id = await store().processVideo('https://youtu.be/abc');
    const video = store().videos.find((v) => v.id === id)!;

    expect(video.status).toBe('complete');
    expect(video.progress).toBe(100);
    expect(video.events).toHaveLength(1);
    expect(video.events![0].confidence).toBe(0.95); // priority 'high'
    expect(video.insights?.summary).toBe('Final summary');
    expect(video.insights?.actions).toHaveLength(1);
    expect(video.insights?.topics).toEqual(['t2']);

    expect(fetchMock).toHaveBeenNthCalledWith(1, '/api/video', expect.anything());
    expect(fetchMock).toHaveBeenNthCalledWith(2, '/api/extract-events', expect.anything());
  });

  it('marks the video failed when the backend responds with an error', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValueOnce(jsonResponse({}, false, 500)));
    const id = await store().processVideo('https://youtu.be/x');
    const video = store().videos.find((v) => v.id === id)!;
    expect(video.status).toBe('failed');
    expect(video.progress).toBe(0);
    expect(store().activities.some((a) => a.type === 'error')).toBe(true);
  });

  it('falls back to /api/transcribe when the primary transcript is too short', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(
        jsonResponse({ status: 'complete', result: { insights: { summary: 'S' }, raw_response: {} } }),
      )
      .mockResolvedValueOnce(
        jsonResponse({ success: true, transcript: 'y'.repeat(200), source: 'openai', wordCount: 120 }),
      )
      .mockResolvedValueOnce(
        jsonResponse({ success: true, data: { events: [], actions: [], summary: 'S2', topics: [] } }),
      );
    vi.stubGlobal('fetch', fetchMock);

    const id = await store().processVideo('https://youtu.be/x');
    const video = store().videos.find((v) => v.id === id)!;

    expect(fetchMock).toHaveBeenNthCalledWith(2, '/api/transcribe', expect.anything());
    expect(fetchMock).toHaveBeenNthCalledWith(3, '/api/extract-events', expect.anything());
    expect(video.transcript).toBe('y'.repeat(200));
    expect(video.status).toBe('complete');
  });
});

describe('dashboard-store · deployPipeline (mocked fetch)', () => {
  it('records the deployment result on success', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValueOnce(
        jsonResponse({
          status: 'success',
          result: {
            live_url: 'https://live.example',
            github_repo: 'octo/repo',
            build_status: 'passing',
            code_generation: { framework: 'next', files_created: ['index.ts'], entry_point: 'index.ts' },
            deployment: { status: 'ready', platforms: ['vercel'], urls: {} },
            features_implemented: [],
          },
        }),
      ),
    );
    await store().deployPipeline('https://youtu.be/x');
    const video = store().videos[0];
    expect(video.status).toBe('complete');
    expect(video.pipelineResult?.live_url).toBe('https://live.example');
    expect(video.pipelineResult?.github_repo).toBe('octo/repo');
    expect(store().activities.some((a) => a.event.includes('live.example'))).toBe(true);
  });

  it('marks the video failed when the pipeline call errors', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValueOnce(jsonResponse({}, false, 500)));
    await store().deployPipeline('https://youtu.be/x');
    expect(store().videos[0].status).toBe('failed');
  });
});

describe('dashboard-store · performSearch (mocked fetch)', () => {
  it('clears results and skips the request for an empty query', async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal('fetch', fetchMock);
    await store().performSearch('v1', '   ');
    expect(fetchMock).not.toHaveBeenCalled();
    expect(store().searchResults).toEqual([]);
  });

  it('stores results on a successful search', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValueOnce(
        jsonResponse({ results: [{ start: 0, duration: 2, text: 'hit', score: 0.9 }] }),
      ),
    );
    await store().performSearch('v1', 'query');
    expect(store().searchResults).toHaveLength(1);
    expect(store().searchResults[0].text).toBe('hit');
    expect(store().searchLoading).toBe(false);
  });

  it('records an error activity and clears results when the search fails', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValueOnce(jsonResponse('boom', false, 500)));
    await store().performSearch('v1', 'query');
    expect(store().searchResults).toEqual([]);
    expect(store().activities.some((a) => a.type === 'error')).toBe(true);
    expect(store().searchLoading).toBe(false);
  });
});
