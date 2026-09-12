import { afterEach, beforeEach, describe, expect, it } from 'vitest';

import { useDashboardStore, type Video } from '../dashboard-store';

const STORAGE_KEY = 'eventrelay-dashboard-v1';

type StoredDashboardState = {
  state: {
    videos: Video[];
    activities: Array<{ time: string; event: string; type: 'success' | 'info' | 'error' }>;
  };
  version: number;
};

function makeVideo(overrides: Partial<Video> = {}): Video {
  return {
    id: 'video-1',
    title: 'Stored video',
    url: 'https://www.youtube.com/watch?v=auJzb1D-fag',
    status: 'processing',
    progress: 25,
    ...overrides,
  };
}

function makeStorage() {
  const values = new Map<string, string>();
  return {
    getItem(key: string) {
      return values.has(key) ? values.get(key)! : null;
    },
    setItem(key: string, value: string) {
      values.set(key, value);
    },
    removeItem(key: string) {
      values.delete(key);
    },
    clear() {
      values.clear();
    },
  };
}

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

function readStoredState(storage: ReturnType<typeof makeStorage>): StoredDashboardState {
  const raw = storage.getItem(STORAGE_KEY);
  expect(raw).not.toBeNull();
  return JSON.parse(raw as string) as StoredDashboardState;
}

describe('dashboard-store persistence', () => {
  let storage: ReturnType<typeof makeStorage>;

  beforeEach(async () => {
    storage = makeStorage();
    Object.defineProperty(globalThis, 'window', {
      configurable: true,
      value: globalThis,
    });
    Object.defineProperty(globalThis, 'localStorage', {
      configurable: true,
      value: storage,
    });
    await useDashboardStore.persist.clearStorage();
    resetStore();
  });

  afterEach(async () => {
    await useDashboardStore.persist.clearStorage();
    delete (globalThis as { window?: typeof globalThis }).window;
    delete (globalThis as { localStorage?: typeof storage }).localStorage;
  });

  it('persists only videos and activities to localStorage', () => {
    const video = makeVideo();
    const activity = { time: '10:15', event: 'Stored event', type: 'info' as const };

    useDashboardStore.setState({
      videos: [video],
      activities: [activity],
      selectedVideoId: video.id,
      loading: true,
      searchQuery: 'ignored',
      searchResults: [{ start: 0, duration: 3, text: 'ignored', score: 1 }],
      searchLoading: true,
    });

    const stored = readStoredState(storage);
    expect(stored.state).toEqual({
      videos: [video],
      activities: [activity],
    });
    expect(stored.version).toBe(0);
    expect('selectedVideoId' in stored.state).toBe(false);
    expect('searchQuery' in stored.state).toBe(false);
  });

  it('rehydrates persisted videos and activities while leaving volatile fields at defaults', async () => {
    const video = makeVideo({ id: 'video-2', progress: 100, status: 'complete' });
    const activity = { time: '11:30', event: 'Hydrated event', type: 'success' as const };

    storage.setItem(
      STORAGE_KEY,
      JSON.stringify({
        state: {
          videos: [video],
          activities: [activity],
        },
        version: 0,
      } satisfies StoredDashboardState),
    );

    await useDashboardStore.persist.rehydrate();

    const state = useDashboardStore.getState();
    expect(state.videos).toEqual([video]);
    expect(state.activities).toEqual([activity]);
    expect(state.selectedVideoId).toBeNull();
    expect(state.loading).toBe(false);
    expect(state.searchQuery).toBe('');
    expect(state.searchResults).toEqual([]);
    expect(state.searchLoading).toBe(false);
  });

  it('ignores malformed localStorage payloads during rehydrate', async () => {
    storage.setItem(STORAGE_KEY, '{not-json');

    await useDashboardStore.persist.rehydrate();

    const state = useDashboardStore.getState();
    expect(state.videos).toEqual([]);
    expect(state.activities).toEqual([]);
  });
});
