import { afterEach, describe, expect, it } from 'vitest';
import { GOLDEN_IDENTITY_HASHES, applyExtractedSpec, buildIdentityPack } from '@/lib/video-pack';
import {
  PROCESSING_STALE_MS,
  claimPackProcessing,
  getPackRecord,
  putPackRecord,
  resetVideoPackStoreForTests,
  setVideoPackRedisForTests,
  type VideoPackRecord,
  type VideoPackRedisClient,
} from '@/lib/video-pack-store';

const CANON = 'jNQXAC9IVRw';
const HASH = GOLDEN_IDENTITY_HASHES[CANON];
const SOURCE_URL = `https://www.youtube.com/watch?v=${CANON}`;
const IDENTITY = {
  video_id: CANON,
  source_url: SOURCE_URL,
  source_hash: HASH,
  id: `vp:v0:${CANON}`,
};

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
    artifacts: [],
    stack: { tools: [] },
    visual_context: null,
  });
}

function decodeStored(value: unknown): VideoPackRecord | null {
  let decoded = value;
  for (let attempt = 0; attempt < 2 && typeof decoded === 'string'; attempt += 1) {
    try {
      decoded = JSON.parse(decoded) as unknown;
    } catch {
      return null;
    }
  }
  if (!decoded || typeof decoded !== 'object' || !('state' in decoded)) return null;
  return decoded as VideoPackRecord;
}

function createRedis(initial: unknown = null) {
  let stored = initial;
  let evalCalls = 0;
  let setCalls = 0;
  const client: VideoPackRedisClient = {
    async get<TData>() {
      return stored as TData | null;
    },
    async set(_key, value) {
      setCalls += 1;
      stored = value;
      return 'OK';
    },
    async eval<TResult>(_script, _keys, args) {
      evalCalls += 1;
      const processing = JSON.parse(String(args[0])) as VideoPackRecord;
      const staleBefore = String(args[1]);
      const current = decodeStored(stored);
      if (current?.state === 'ready') {
        return ['existing', JSON.stringify(current)] as unknown as TResult;
      }
      if (
        current?.state === 'processing' &&
        /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$/.test(current.started_at) &&
        current.started_at > staleBefore
      ) {
        return ['existing', JSON.stringify(current)] as unknown as TResult;
      }
      stored = processing;
      return ['claimed', JSON.stringify(processing)] as unknown as TResult;
    },
  };
  return {
    client,
    getStored: () => stored,
    getEvalCalls: () => evalCalls,
    getSetCalls: () => setCalls,
  };
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
    const first = await claimPackProcessing(IDENTITY);
    expect(first).toBe('claimed');
    const second = await claimPackProcessing(IDENTITY);
    expect(second).not.toBe('claimed');
    if (second === 'claimed') {
      throw new Error('second claim should see the in-flight record');
    }
    expect(second.state).toBe('processing');
  });

  it('reclaims after a stored extract error so a later POST can retry', async () => {
    await putPackRecord({
      state: 'error',
      ...IDENTITY,
      error: 'Gemini 3.8 Flash returned no extracted spec content.',
      failed_at: '2026-09-03T00:00:00.000Z',
    });
    const claimed = await claimPackProcessing(IDENTITY);
    expect(claimed).toBe('claimed');
    const next = await getPackRecord(HASH);
    expect(next?.state).toBe('processing');
  });

  it('atomically preserves an existing ready pack instead of clobbering it', async () => {
    const ready: VideoPackRecord = { state: 'ready', pack: readyPack() };
    const redis = createRedis(JSON.stringify(JSON.stringify(ready)));
    setVideoPackRedisForTests(redis.client);

    const result = await claimPackProcessing(IDENTITY, new Date('2026-09-05T06:00:00.000Z'));

    expect(result).toEqual(ready);
    expect(decodeStored(redis.getStored())).toEqual(ready);
    expect(redis.getEvalCalls()).toBe(1);
    expect(redis.getSetCalls()).toBe(0);
  });

  it('returns an active cross-isolate processing claim without scheduling duplicate work', async () => {
    const processing: VideoPackRecord = {
      state: 'processing',
      ...IDENTITY,
      started_at: '2026-09-05T05:59:30.000Z',
    };
    const redis = createRedis(JSON.stringify(processing));
    setVideoPackRedisForTests(redis.client);

    const result = await claimPackProcessing(IDENTITY, new Date('2026-09-05T06:00:00.000Z'));

    expect(result).toEqual(processing);
    expect(redis.getEvalCalls()).toBe(1);
  });

  it('atomically replaces stale and malformed values with a durable processing claim', async () => {
    const now = new Date('2026-09-05T06:00:00.000Z');
    const stale: VideoPackRecord = {
      state: 'processing',
      ...IDENTITY,
      started_at: new Date(now.getTime() - PROCESSING_STALE_MS).toISOString(),
    };
    const staleRedis = createRedis(stale);
    setVideoPackRedisForTests(staleRedis.client);
    expect(await claimPackProcessing(IDENTITY, now)).toBe('claimed');
    expect(decodeStored(staleRedis.getStored())?.state).toBe('processing');

    resetVideoPackStoreForTests();
    const malformedRedis = createRedis('{not-json');
    setVideoPackRedisForTests(malformedRedis.client);
    expect(await claimPackProcessing(IDENTITY, now)).toBe('claimed');
    expect(decodeStored(malformedRedis.getStored())?.state).toBe('processing');
  });

  it('does not acknowledge a ready record that Redis failed to persist', async () => {
    const redis = createRedis();
    redis.client.set = async () => {
      throw new Error('redis unavailable');
    };
    setVideoPackRedisForTests(redis.client);

    await expect(putPackRecord({ state: 'ready', pack: readyPack() })).rejects.toThrow(
      'redis unavailable',
    );
    setVideoPackRedisForTests(null);
    expect(await getPackRecord(HASH)).toBeNull();
  });

  it('does not fall back to an isolate-local claim when the atomic script fails', async () => {
    const redis = createRedis();
    redis.client.eval = async () => {
      throw new Error('eval unavailable');
    };
    setVideoPackRedisForTests(redis.client);

    await expect(claimPackProcessing(IDENTITY)).rejects.toThrow('eval unavailable');
  });
});
