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

describe('dashboard-store · processVideo (real SSE pipeline)', () => {
  it('streams agent updates, insights, and transcript into the video', async () => {
    const events = [
      { type: 'pipeline_status', status: 'running', data: { mode: 'gemini-sse' }, timestamp: 't' },
      { type: 'agent_update', agentId: 'orchestrator', agentName: 'Orchestrator', status: 'running', timestamp: 't' },
      { type: 'agent_update', agentId: 'orchestrator', agentName: 'Orchestrator', status: 'complete', duration: 1.2, data: { title: 'My Video' }, timestamp: 't' },
      { type: 'agent_update', agentId: 'action_gen', agentName: 'ActionGenerator', status: 'complete', data: {}, timestamp: 't' },
      { type: 'consensus', data: { votes: [], finalClassification: 'tutorial', agreementRatio: 0.67 }, timestamp: 't' },
      {
        type: 'workflow',
        data: {
          title: 'My Video',
          summary: 'A great tutorial',
          actions: [{ title: 'Do X', description: 'd', category: 'build' }],
          topics: ['rust'],
          events: [{ type: 'action', title: 'Step 1', priority: 'high' }],
          transcript: [{ text: 'hello' }, { text: 'world' }],
        },
        timestamp: 't',
      },
      { type: 'pipeline_status', status: 'complete', duration: 5, data: { totalAgents: 2, completedAgents: 2 }, timestamp: 't' },
    ];
    const fetchMock = vi.fn().mockResolvedValueOnce(sseResponse(events));
    vi.stubGlobal('fetch', fetchMock);

    const id = await store().processVideo('https://youtu.be/abc');
    const video = store().videos.find((v) => v.id === id)!;

    expect(fetchMock).toHaveBeenNthCalledWith(1, '/api/pipeline/stream', expect.anything());
    expect(video.status).toBe('complete');
    expect(video.progress).toBe(100);

    // Real streamed agents (orchestrator de-duped to one complete entry)
    expect(video.agents).toHaveLength(2);
    expect(video.agents!.every((a) => a.status === 'complete')).toBe(true);
    expect(video.agents!.map((a) => a.agent_type)).toContain('Orchestrator');

    // Insights + events + transcript from the workflow event
    expect(video.insights?.summary).toBe('A great tutorial');
    expect(video.insights?.actions).toHaveLength(1);
    expect(video.insights?.topics).toEqual(['rust']);
    expect(video.events).toHaveLength(1);
    expect(video.events![0].id).toBe(`evt_${id}_0`);
    expect(video.events![0].confidence).toBe(0.95); // priority 'high'
    expect(video.transcript).toBe('hello world');

    expect(store().activities.some((a) => a.event.includes('Consensus'))).toBe(true);
  });

  it('falls back to /api/video when the stream is unavailable', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(sseResponse([], false)) // stream 503
      .mockResolvedValueOnce(
        jsonResponse({
          status: 'complete',
          result: {
            insights: { summary: 'Legacy summary', actions: [], sentiment: 'Neutral', topics: [] },
            transcript_segments: 2,
            raw_response: { transcript: { text: 'x'.repeat(200) } },
          },
        }),
      )
      .mockResolvedValueOnce(
        jsonResponse({
          success: true,
          data: { events: [], actions: [{ title: 'A', description: 'd', category: 'build' }], summary: 'Legacy final', topics: ['t'] },
        }),
      );
    vi.stubGlobal('fetch', fetchMock);

    const id = await store().processVideo('https://youtu.be/x');
    const video = store().videos.find((v) => v.id === id)!;

    expect(fetchMock).toHaveBeenNthCalledWith(1, '/api/pipeline/stream', expect.anything());
    expect(fetchMock).toHaveBeenNthCalledWith(2, '/api/video', expect.anything());
    expect(video.status).toBe('complete');
    expect(video.insights?.summary).toBe('Legacy final');
    expect(video.transcript).toBe('x'.repeat(200));
  });

  it('falls back when the stream emits an error event', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(
        sseResponse([
          { type: 'pipeline_status', status: 'running', timestamp: 't' },
          { type: 'error', data: { message: 'boom' }, timestamp: 't' },
        ]),
      )
      .mockResolvedValueOnce(
        jsonResponse({
          status: 'complete',
          result: {
            insights: { summary: 'Recovered', actions: [], sentiment: 'Neutral', topics: [] },
            raw_response: { transcript: { text: 'y'.repeat(200) } },
          },
        }),
      )
      .mockResolvedValueOnce(jsonResponse({ success: false, error: 'no key' }));
    vi.stubGlobal('fetch', fetchMock);

    const id = await store().processVideo('https://youtu.be/x');
    const video = store().videos.find((v) => v.id === id)!;

    expect(fetchMock).toHaveBeenNthCalledWith(2, '/api/video', expect.anything());
    expect(video.status).toBe('complete');
    expect(video.insights?.summary).toBe('Recovered');
  });

  it('marks the video failed when both the stream and direct analysis fail', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(sseResponse([], false)) // stream 503
      .mockResolvedValueOnce(jsonResponse({}, false, 500)); // /api/video 500
    vi.stubGlobal('fetch', fetchMock);

    const id = await store().processVideo('https://youtu.be/x');
    const video = store().videos.find((v) => v.id === id)!;

    expect(video.status).toBe('failed');
    expect(video.progress).toBe(0);
    expect(store().activities.some((a) => a.type === 'error')).toBe(true);
  });
});

describe('dashboard-store · dispatchToAgents / refreshAgentStatus', () => {
  it('dispatches the video events and stores returned executions', async () => {
    store().addVideo(
      makeVideo({ id: 'v1', events: [{ id: 'e1', type: 'action', title: 'Do X', confidence: 0.9 }] }),
    );
    const fetchMock = vi.fn().mockResolvedValueOnce(
      jsonResponse({
        dispatch_id: 'dsp_1',
        executions: [{ agent_id: 'a1', agent_type: 'analyzer', status: 'running', progress: 0 }],
      }),
    );
    vi.stubGlobal('fetch', fetchMock);

    await store().dispatchToAgents('v1');

    expect(fetchMock).toHaveBeenCalledWith('/api/agents/dispatch', expect.objectContaining({ method: 'POST' }));
    expect(store().videos[0].agents).toHaveLength(1);
    expect(store().videos[0].agents![0].agent_id).toBe('a1');
    expect(store().activities.some((a) => a.event.includes('Dispatched 1 agents'))).toBe(true);
  });

  it('reports honestly when the agent backend is offline (503)', async () => {
    store().addVideo(
      makeVideo({ id: 'v1', events: [{ id: 'e1', type: 'action', title: 'Do X', confidence: 0.9 }] }),
    );
    vi.stubGlobal('fetch', vi.fn().mockResolvedValueOnce(jsonResponse({ error: 'nope' }, false, 503)));

    await store().dispatchToAgents('v1');

    expect(store().videos[0].agents).toBeUndefined();
    expect(store().activities.some((a) => a.event.includes('Agent backend offline'))).toBe(true);
  });

  it('skips dispatch when the video has no events', async () => {
    store().addVideo(makeVideo({ id: 'v1' }));
    const fetchMock = vi.fn();
    vi.stubGlobal('fetch', fetchMock);
    await store().dispatchToAgents('v1');
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it('refreshAgentStatus polls only running agents and merges updates', async () => {
    store().addVideo(
      makeVideo({
        id: 'v1',
        agents: [
          { agent_id: 'a1', agent_type: 'analyzer', status: 'running', progress: 30 },
          { agent_id: 'a2', agent_type: 'content_creator', status: 'complete', progress: 100 },
        ],
      }),
    );
    const fetchMock = vi.fn().mockResolvedValueOnce(
      jsonResponse({ agent_id: 'a1', status: 'complete', progress: 100, result: { output: 'done' } }),
    );
    vi.stubGlobal('fetch', fetchMock);

    await store().refreshAgentStatus('v1');

    expect(fetchMock).toHaveBeenCalledTimes(1); // only the running agent is polled
    const a1 = store().videos[0].agents!.find((a) => a.agent_id === 'a1')!;
    expect(a1.status).toBe('complete');
    expect(a1.progress).toBe(100);
  });

  it('refreshAgentStatus is a no-op when nothing is running', async () => {
    store().addVideo(
      makeVideo({ id: 'v1', agents: [{ agent_id: 'a1', agent_type: 'x', status: 'complete', progress: 100 }] }),
    );
    const fetchMock = vi.fn();
    vi.stubGlobal('fetch', fetchMock);
    await store().refreshAgentStatus('v1');
    expect(fetchMock).not.toHaveBeenCalled();
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
