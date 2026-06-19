import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';

// Mock the backend client: the store is a pure consumer of this module, so the
// tests drive the job lifecycle entirely through these fakes. No fetch, no SSE.
// `vi.hoisted` runs before the hoisted `vi.mock` factory so the fakes exist
// when the factory references them.
const { submitJob, getJob, getTranscript, getEvents, getArtifacts, FakeEventRelayError } =
  vi.hoisted(() => {
    class FakeEventRelayError extends Error {
      constructor(
        message: string,
        readonly status?: number,
      ) {
        super(message);
        this.name = 'EventRelayError';
      }
    }
    return {
      submitJob: vi.fn(),
      getJob: vi.fn(),
      getTranscript: vi.fn(),
      getEvents: vi.fn(),
      getArtifacts: vi.fn(),
      FakeEventRelayError,
    };
  });

vi.mock('@/lib/eventrelay-client', () => ({
  EventRelayError: FakeEventRelayError,
  eventRelay: { submitJob, getJob, getTranscript, getEvents, getArtifacts },
}));

import { useDashboardStore } from '@/store/dashboard-store';
import type { Video } from '@/store/dashboard-store';

// ── helpers ──

function resetStore() {
  useDashboardStore.setState({
    videos: [],
    activities: [],
    selectedVideoId: null,
    loading: false,
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

beforeEach(() => {
  resetStore();
  submitJob.mockReset();
  getJob.mockReset();
  getTranscript.mockReset();
  getEvents.mockReset();
  getArtifacts.mockReset();
});

afterEach(() => {
  vi.restoreAllMocks();
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

  it('selectVideo sets the id', () => {
    store().selectVideo('v1');
    expect(store().selectedVideoId).toBe('v1');
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

  it('setLoading updates its flag', () => {
    store().setLoading(true);
    expect(store().loading).toBe(true);
  });
});

describe('dashboard-store · processVideo (pure SDK consumer)', () => {
  it('drives the job lifecycle and maps the contract into the video', async () => {
    submitJob.mockResolvedValueOnce({ job_id: 'job_1', status: 'queued' });
    getJob.mockResolvedValueOnce({ job_id: 'job_1', status: 'succeeded' });
    getTranscript.mockResolvedValueOnce('hello world');
    getEvents.mockResolvedValueOnce([
      { type: 'youtube.action.created', ts: '2026-01-01T00:00:00Z', payload: { title: 'Do X', description: 'd', confidence: 0.95 } },
      { type: 'youtube.topic.detected', ts: '2026-01-01T00:00:01Z', payload: { name: 'rust' } },
    ]);
    getArtifacts.mockResolvedValueOnce({
      summary: 'A great tutorial',
      tasks: ['Build it', 'Ship it'],
      insights: { sentiment: 'Positive', topics: ['rust', 'wasm'] },
    });

    const id = await store().processVideo('https://youtu.be/abc');
    const video = store().videos.find((v) => v.id === id)!;

    expect(submitJob).toHaveBeenCalledWith({ video_url: 'https://youtu.be/abc' });
    expect(video.status).toBe('complete');
    expect(video.progress).toBe(100);
    expect(video.transcript).toBe('hello world');

    // events → ExtractedEvent (type taken from the <…>.<…>.<action> segment)
    expect(video.events).toHaveLength(2);
    expect(video.events![0].type).toBe('action');
    expect(video.events![0].title).toBe('Do X');
    expect(video.events![0].confidence).toBe(0.95);
    expect(video.events![1].type).toBe('topic');
    expect(video.events![1].title).toBe('rust');

    // artifacts → insights
    expect(video.insights?.summary).toBe('A great tutorial');
    expect(video.insights?.actions.map((a) => a.title)).toEqual(['Build it', 'Ship it']);
    expect(video.insights?.sentiment).toBe('Positive');
    expect(video.insights?.topics).toEqual(['rust', 'wasm']);
  });

  it('marks the video failed when the backend job fails', async () => {
    submitJob.mockResolvedValueOnce({ job_id: 'job_2', status: 'queued' });
    getJob.mockResolvedValueOnce({ job_id: 'job_2', status: 'failed' });

    const id = await store().processVideo('https://youtu.be/x');
    const video = store().videos.find((v) => v.id === id)!;

    expect(video.status).toBe('failed');
    expect(video.progress).toBe(0);
    expect(getTranscript).not.toHaveBeenCalled();
    expect(store().activities.some((a) => a.type === 'error')).toBe(true);
  });

  it('marks the video failed (never falls back to a model) when the backend is unreachable', async () => {
    submitJob.mockRejectedValueOnce(new FakeEventRelayError('backend unreachable'));

    const id = await store().processVideo('https://youtu.be/x');
    const video = store().videos.find((v) => v.id === id)!;

    expect(video.status).toBe('failed');
    expect(store().activities.some((a) => a.type === 'error' && a.event.includes('unreachable'))).toBe(true);
  });
});
