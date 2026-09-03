import type { Redis } from '@upstash/redis';
import { resolveUpstashRedisCredentials } from '@/lib/billing/redis-credentials';
import type { VideoPackV0Json } from '@/lib/video-pack';

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

let redisPromise: Promise<Redis | null> | null = null;

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

async function getRedis(): Promise<Redis | null> {
  if (redisPromise) return redisPromise;
  redisPromise = (async () => {
    const creds = resolveUpstashRedisCredentials();
    if (!creds) {
      return null;
    }
    try {
      const { Redis } = await import('@upstash/redis');
      return new Redis({
        url: creds.url,
        token: creds.token,
      });
    } catch (error) {
      console.error('[video-pack-store] Redis client init failed:', error);
      return null;
    }
  })();
  return redisPromise;
}

function asRecord(value: unknown): VideoPackRecord | null {
  if (value === null || typeof value !== 'object') return null;
  const row = value as VideoPackRecord;
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

export async function getPackRecord(sourceHash: string): Promise<VideoPackRecord | null> {
  const key = packStoreKey(sourceHash);
  const redis = await getRedis();
  if (redis) {
    try {
      const raw = await redis.get<VideoPackRecord>(key);
      const parsed = asRecord(raw);
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
  memoryStore.set(key, record);
  const redis = await getRedis();
  if (redis) {
    try {
      await redis.set(key, record);
    } catch (error) {
      console.error('[video-pack-store] Redis set failed:', error);
    }
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
      if (!current || current.state === 'error' || isProcessingStale(current, now.getTime())) {
        await redis.set(key, processing);
        memoryStore.set(key, processing);
        return 'claimed';
      }
      return current;
    } catch (error) {
      console.error('[video-pack-store] Redis claim failed:', error);
    }
  }

  const local = memoryStore.get(key);
  if (
    local &&
    local.state === 'processing' &&
    !isProcessingStale(local, now.getTime()) &&
    local !== existing
  ) {
    return local;
  }
  memoryStore.set(key, processing);
  return 'claimed';
}

export function resetVideoPackStoreForTests(): void {
  memoryStore.clear();
  redisPromise = null;
}

export function seedVideoPackRecordForTests(record: VideoPackRecord): void {
  memoryStore.set(packStoreKey(recordHash(record)), record);
}
