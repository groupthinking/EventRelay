import { resolveUpstashRedisCredentials } from '@/lib/billing/redis-credentials';
import type { VideoPackV0Json } from '@/lib/video-pack';

export type VideoPackRedisClient = {
  get: <T = unknown>(key: string) => Promise<T | null>;
  set: (key: string, value: unknown, opts?: { nx?: boolean }) => Promise<unknown>;
};

export const VIDEO_PACK_STORE_PREFIX = 'er:videopack:v0:';
export const PROCESSING_STALE_MS = 180_000;

export type PackProcessingIdentity = {
  video_id: string;
  source_url: string;
  source_hash: string;
  id: string;
};

export type VideoPackRecord =
  | {
      state: 'processing';
      video_id: string;
      source_url: string;
      source_hash: string;
      id: string;
      started_at: string;
    }
  | {
      state: 'ready';
      pack: VideoPackV0Json;
    }
  | {
      state: 'error';
      video_id: string;
      source_url: string;
      source_hash: string;
      id: string;
      error: string;
      failed_at: string;
    };

const memoryStore = new Map<string, VideoPackRecord>();

let redisPromise: Promise<VideoPackRedisClient | null> | null = null;

export function packStoreKey(sourceHash: string): string {
  return `${VIDEO_PACK_STORE_PREFIX}${sourceHash}`;
}

export function isProcessingStale(
  record: VideoPackRecord,
  nowMs: number = Date.now(),
): boolean {
  if (record.state !== 'processing') return false;
  const started = Date.parse(record.started_at);
  if (Number.isNaN(started)) return true;
  return nowMs - started >= PROCESSING_STALE_MS;
}

function recordHash(record: VideoPackRecord): string {
  return record.state === 'ready' ? record.pack.provenance.source_hash : record.source_hash;
}

async function getRedis(): Promise<VideoPackRedisClient | null> {
  if (redisPromise) return redisPromise;
  redisPromise = (async () => {
    const creds = resolveUpstashRedisCredentials();
    if (!creds) {
      return null;
    }
    try {
      const { Redis } = await import('@upstash/redis');
      const client = new Redis({
        url: creds.url,
        token: creds.token,
      });
      return {
        get: <T = unknown>(key: string) => client.get<T>(key),
        set: (key: string, value: unknown, opts?: { nx?: boolean }) =>
          opts?.nx ? client.set(key, value, { nx: true }) : client.set(key, value),
      };
    } catch (error) {
      console.error('[video-pack-store] Redis client init failed:', error);
      return null;
    }
  })();
  return redisPromise;
}

function decodeStoreValue(value: unknown): unknown {
  let current = value;
  for (let attempt = 0; attempt < 2; attempt += 1) {
    if (typeof current !== 'string') {
      return current;
    }
    const trimmed = current.trim();
    if (!trimmed.startsWith('{') && !trimmed.startsWith('"')) {
      return current;
    }
    try {
      current = JSON.parse(trimmed) as unknown;
    } catch {
      return value;
    }
  }
  return current;
}

function asRecord(value: unknown): VideoPackRecord | null {
  const decoded = decodeStoreValue(value);
  if (decoded === null || typeof decoded !== 'object') return null;
  const row = decoded as VideoPackRecord;
  if (row.state === 'ready' && row.pack && typeof row.pack === 'object') {
    return row;
  }
  if (
    (row.state === 'processing' || row.state === 'error') &&
    typeof row.source_hash === 'string' &&
    row.source_hash.length === 64
  ) {
    return row;
  }
  return null;
}

function readyPersistErrorRecord(
  pack: VideoPackV0Json,
  failedAt: string = new Date().toISOString(),
): Extract<VideoPackRecord, { state: 'error' }> {
  return {
    state: 'error',
    video_id: pack.video_id,
    source_url: pack.source_url,
    source_hash: pack.provenance.source_hash,
    id: pack.id,
    error: 'Video pack persist failed: Redis write of ready pack failed.',
    failed_at: failedAt,
  };
}

async function readRedisRecord(
  redis: VideoPackRedisClient,
  key: string,
): Promise<VideoPackRecord | null> {
  const first = asRecord(await redis.get(key));
  if (first) {
    return first;
  }
  return asRecord(await redis.get(key));
}

export async function getPackRecord(sourceHash: string): Promise<VideoPackRecord | null> {
  const key = packStoreKey(sourceHash);
  const redis = await getRedis();
  if (redis) {
    try {
      const parsed = await readRedisRecord(redis, key);
      if (parsed) {
        memoryStore.set(key, parsed);
        return parsed;
      }
    } catch (error) {
      console.error('[video-pack-store] Redis get failed:', error);
    }
  }
  return memoryStore.get(key) ?? null;
}

export async function putPackRecord(record: VideoPackRecord): Promise<void> {
  const key = packStoreKey(recordHash(record));
  const redis = await getRedis();
  if (!redis) {
    memoryStore.set(key, record);
    return;
  }
  try {
    await redis.set(key, record);
    memoryStore.set(key, record);
  } catch (error) {
    console.error('[video-pack-store] Redis set failed:', error);
    if (record.state === 'ready') {
      const errorRecord = readyPersistErrorRecord(record.pack);
      try {
        await redis.set(key, errorRecord);
      } catch (persistError) {
        console.error('[video-pack-store] Redis error-record persist failed:', persistError);
      }
      memoryStore.set(key, errorRecord);
      throw new Error('Video pack persist failed: Redis write of ready pack failed.');
    }
    memoryStore.set(key, record);
  }
}

export async function claimPackProcessing(
  identity: PackProcessingIdentity,
  now: Date = new Date(),
): Promise<'claimed' | VideoPackRecord> {
  const existing = await getPackRecord(identity.source_hash);
  if (existing?.state === 'ready') {
    return existing;
  }
  if (existing?.state === 'processing' && !isProcessingStale(existing, now.getTime())) {
    return existing;
  }

  const processing: Extract<VideoPackRecord, { state: 'processing' }> = {
    state: 'processing',
    video_id: identity.video_id,
    source_url: identity.source_url,
    source_hash: identity.source_hash,
    id: identity.id,
    started_at: now.toISOString(),
  };

  const key = packStoreKey(identity.source_hash);
  const redis = await getRedis();
  if (redis) {
    try {
      const created = await redis.set(key, processing, { nx: true });
      if (created) {
        memoryStore.set(key, processing);
        return 'claimed';
      }
      const current = (await getPackRecord(identity.source_hash)) ?? existing;
      if (current?.state === 'ready') {
        return current;
      }
      if (current?.state === 'processing' && !isProcessingStale(current, now.getTime())) {
        return current;
      }
      if (current?.state === 'error' || (current != null && isProcessingStale(current, now.getTime()))) {
        const latest = await getPackRecord(identity.source_hash);
        if (latest?.state === 'ready') {
          return latest;
        }
        if (latest?.state === 'processing' && !isProcessingStale(latest, now.getTime())) {
          return latest;
        }
        await redis.set(key, processing);
        memoryStore.set(key, processing);
        return 'claimed';
      }
      // NX lost and the existing value could not be parsed. Leave Redis untouched.
      return current ?? existing ?? processing;
    } catch (error) {
      console.error('[video-pack-store] Redis claim failed:', error);
      const localAfterFailure = memoryStore.get(key);
      if (localAfterFailure) {
        return localAfterFailure;
      }
      return processing;
    }
  }

  const local = memoryStore.get(key);
  if (local?.state === 'ready') {
    return local;
  }
  if (local?.state === 'processing' && !isProcessingStale(local, now.getTime())) {
    return local;
  }
  memoryStore.set(key, processing);
  return 'claimed';
}

export function resetVideoPackStoreForTests(): void {
  memoryStore.clear();
  redisPromise = Promise.resolve(null);
}

export function clearVideoPackMemoryForTests(): void {
  memoryStore.clear();
}

export function setVideoPackRedisForTests(redis: VideoPackRedisClient | null): void {
  redisPromise = Promise.resolve(redis);
}

export function seedVideoPackRecordForTests(record: VideoPackRecord): void {
  memoryStore.set(packStoreKey(recordHash(record)), record);
}
