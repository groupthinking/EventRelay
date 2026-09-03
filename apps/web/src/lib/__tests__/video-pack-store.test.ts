import { afterEach, describe, expect, it } from 'vitest';
import { GOLDEN_IDENTITY_HASHES, applyExtractedSpec, buildIdentityPack } from '@/lib/video-pack';
import {
  claimPackProcessing,
  clearVideoPackMemoryForTests,
  getPackRecord,
  packStoreKey,
  putPackRecord,
  resetVideoPackStoreForTests,
  setVideoPackRedisForTests,
  type VideoPackRecord,
  type VideoPackRedisClient,
} from '@/lib/video-pack-store';

const CANON = 'jNQXAC9IVRw';
const HASH = GOLDEN_IDENTITY_HASHES[CANON];
const SOURCE_URL = `https://www.youtube.com/watch?v=${CANON}`;

function readyPack() {
  const identity = buildIdentityPack(CANON, SOURCE_URL, '2026-09-03T00:00:00.000Z');
  return applyExtractedSpec(identity, {
    transcript: {
      language: 'en',
      full_text: 'Me at the zoo.',
      segments: [{ idx: 0, start_s: 0, end_s: 5, text: 'Me at the zoo.' }],
    },
    keyframes: [{ t_s: 1, desc: 'Elephants' }],
    concepts: ['zoo'],
    requirements: [],
    code_snippets: [],
    visual_context: null,
  });
}

afterEach(() => {
  resetVideoPackStoreForTests();
});

describe('video-pack store', () => {
  it('returns null for an unknown source_hash', async () => {
    expect(await getPackRecord(HASH)).toBeNull();
  });

  it('round-trips a ready spec pack keyed by source_hash', async () => {
    const pack = readyPack();
    expect(pack.provenance.source_hash).toBe(HASH);
    await putPackRecord({ state: 'ready', pack });
    const loaded = await getPackRecord(HASH);
    expect(loaded?.state).toBe('ready');
    if (loaded?.state !== 'ready') {
      throw new Error('expected ready pack');
    }
    expect(loaded.pack.provenance.source_hash).toBe(HASH);
    expect(loaded.pack.transcript.full_text).toBe('Me at the zoo.');
    expect(loaded.pack.concepts).toEqual(['zoo']);
  });

  it('claims processing once for the same hash', async () => {
    const first = await claimPackProcessing({
      video_id: CANON,
      source_url: SOURCE_URL,
      source_hash: HASH,
      id: `vp:v0:${CANON}`,
    });
    expect(first).toBe('claimed');
    const second = await claimPackProcessing({
      video_id: CANON,
      source_url: SOURCE_URL,
      source_hash: HASH,
      id: `vp:v0:${CANON}`,
    });
    expect(second).not.toBe('claimed');
    if (second === 'claimed') {
      throw new Error('second claim should see the in-flight record');
    }
    expect(second.state).toBe('processing');
  });

  it('reclaims after a stored extract error so a later POST can retry', async () => {
    await putPackRecord({
      state: 'error',
      video_id: CANON,
      source_url: SOURCE_URL,
      source_hash: HASH,
      id: `vp:v0:${CANON}`,
      error: 'Gemini 3.8 Flash returned no extracted spec content.',
      failed_at: '2026-09-03T00:00:00.000Z',
    });
    const claimed = await claimPackProcessing({
      video_id: CANON,
      source_url: SOURCE_URL,
      source_hash: HASH,
      id: `vp:v0:${CANON}`,
    });
    expect(claimed).toBe('claimed');
    const next = await getPackRecord(HASH);
    expect(next?.state).toBe('processing');
  });

  it('reads a ready pack when Redis GET returns a double-encoded JSON string', async () => {
    const pack = readyPack();
    const redis = new FakeRedis();
    redis.store.set(packStoreKey(HASH), JSON.stringify(JSON.stringify({ state: 'ready', pack })));
    setVideoPackRedisForTests(redis);

    const loaded = await getPackRecord(HASH);
    expect(loaded?.state).toBe('ready');
    if (loaded?.state !== 'ready') {
      throw new Error('expected ready pack from double-encoded Redis value');
    }
    expect(loaded.pack.provenance.source_hash).toBe(HASH);
  });

  it('reads a ready pack when Redis GET returns a JSON string', async () => {
    const pack = readyPack();
    const redis = new FakeRedis();
    redis.store.set(packStoreKey(HASH), JSON.stringify({ state: 'ready', pack }));
    setVideoPackRedisForTests(redis);

    const loaded = await getPackRecord(HASH);
    expect(loaded?.state).toBe('ready');
    if (loaded?.state !== 'ready') {
      throw new Error('expected ready pack from string Redis value');
    }
    expect(loaded.pack.provenance.source_hash).toBe(HASH);
    expect(loaded.pack.transcript.full_text).toBe('Me at the zoo.');
    expect(loaded.pack.provenance.created_at).toBe('2026-09-03T00:00:00.000Z');
  });

  it('does not claim processing when Redis already holds a ready pack', async () => {
    const pack = readyPack();
    const ready: VideoPackRecord = { state: 'ready', pack };
    const redis = new FakeRedis();
    redis.store.set(packStoreKey(HASH), ready);
    setVideoPackRedisForTests(redis);

    const claimed = await claimPackProcessing({
      video_id: CANON,
      source_url: SOURCE_URL,
      source_hash: HASH,
      id: `vp:v0:${CANON}`,
    });
    expect(claimed).not.toBe('claimed');
    if (claimed === 'claimed') {
      throw new Error('claim must be a no-op when Redis already has ready');
    }
    expect(claimed.state).toBe('ready');
    expect(redis.store.get(packStoreKey(HASH))).toEqual(ready);
    expect(redis.sets).toEqual([]);
  });

  it('does not clobber a ready Redis key after NX-fail plus GET/asRecord miss', async () => {
    const pack = readyPack();
    const ready: VideoPackRecord = { state: 'ready', pack };
    const redis = new FakeRedis();
    redis.store.set(packStoreKey(HASH), ready);
    redis.getMode = 'miss';
    setVideoPackRedisForTests(redis);

    const claimed = await claimPackProcessing({
      video_id: CANON,
      source_url: SOURCE_URL,
      source_hash: HASH,
      id: `vp:v0:${CANON}`,
    });

    expect(claimed).not.toBe('claimed');
    expect(redis.store.get(packStoreKey(HASH))).toEqual(ready);
    expect(redis.unconditionalSets).toEqual([]);
    redis.getMode = 'store';
    const reloaded = await getPackRecord(HASH);
    expect(reloaded).toEqual(ready);
  });

  it('returns the same ready pack from a second isolate when Redis holds it', async () => {
    const pack = readyPack();
    const redis = new FakeRedis();
    setVideoPackRedisForTests(redis);
    await putPackRecord({ state: 'ready', pack });
    clearVideoPackMemoryForTests();

    const loaded = await getPackRecord(HASH);
    expect(loaded?.state).toBe('ready');
    if (loaded?.state !== 'ready') {
      throw new Error('expected ready pack from Redis after memory isolate reset');
    }
    expect(loaded.pack.provenance.created_at).toBe('2026-09-03T00:00:00.000Z');
    expect(loaded.pack.provenance.source_hash).toBe(HASH);
  });

  it('surfaces a Redis ready-write failure as an error record instead of memory-only ready', async () => {
    const pack = readyPack();
    const redis = new FakeRedis();
    redis.setMode = 'throw';
    setVideoPackRedisForTests(redis);

    await expect(putPackRecord({ state: 'ready', pack })).rejects.toThrow(/Redis write of ready pack/i);

    const loaded = await getPackRecord(HASH);
    expect(loaded?.state).toBe('error');
    if (loaded?.state !== 'error') {
      throw new Error('expected error record after ready persist failure');
    }
    expect(loaded.error).toMatch(/Redis write of ready pack/i);
    expect(redis.store.get(packStoreKey(HASH))).not.toEqual({ state: 'ready', pack });
  });
});

class FakeRedis implements VideoPackRedisClient {
  readonly store = new Map<string, unknown>();
  readonly sets: Array<{ key: string; nx?: boolean }> = [];
  getMode: 'store' | 'miss' | 'throw' = 'store';
  setMode: 'store' | 'throw' = 'store';

  get unconditionalSets(): Array<{ key: string; nx?: boolean }> {
    return this.sets.filter((entry) => !entry.nx);
  }

  async get<T = unknown>(key: string): Promise<T | null> {
    if (this.getMode === 'throw') {
      throw new Error('redis get failed');
    }
    if (this.getMode === 'miss') {
      return null;
    }
    const value = this.store.get(key);
    return (value as T | undefined) ?? null;
  }

  async set(key: string, value: unknown, opts?: { nx?: boolean }): Promise<unknown> {
    this.sets.push({ key, nx: opts?.nx });
    if (this.setMode === 'throw') {
      throw new Error('redis set failed');
    }
    if (opts?.nx && this.store.has(key)) {
      return null;
    }
    this.store.set(key, value);
    return 'OK';
  }
}
