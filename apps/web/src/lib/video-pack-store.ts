import { resolveUpstashRedisCredentials } from '@/lib/billing/redis-credentials';
import type { VideoPackV0Json } from '@/lib/video-pack';

/**
 * Durable Video Pack key schema (Upstash REST only in production).
 *
 * Full key: `{VIDEO_PACK_STORE_PREFIX}{source_hash}`
 * Example: `er:videopack:v0:` + 64-char hex SHA-256 from identity pack provenance.
 *
 * Value: JSON {@link VideoPackRecord} (`processing` | `ready` | `error`).
 */
export const VIDEO_PACK_STORE_VERSION = 'v0';
export const VIDEO_PACK_STORE_PREFIX = `er:videopack:${VIDEO_PACK_STORE_VERSION}:`;
export const PROCESSING_STALE_MS = 180_000;

/** Active persistence layer for pack reads (surfaced on `/d/{id}/health`). */
export type PackStoreBackend = 'upstash' | 'memory' | 'unavailable';

export type PackStoreSignal = {
  backend: PackStoreBackend;
  ok: boolean;
};

export type PackLookupResult =
  | { outcome: 'hit'; record: VideoPackRecord; store: PackStoreSignal }
  | { outcome: 'miss'; store: PackStoreSignal }
  | { outcome: 'store_error'; store: PackStoreSignal; error: string };

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

export type VideoPackRedisClient = {
  get<TData = unknown>(key: string): Promise<TData | null>;
  set(key: string, value: unknown, opts?: { nx?: boolean }): Promise<unknown>;
  eval<TResult = unknown>(
    script: string,
    keys: string[],
    args: Array<string | number>,
  ): Promise<TResult>;
};

export const CLAIM_PROCESSING_SCRIPT = `
local key = KEYS[1]
local processing = ARGV[1]
local stale_before = ARGV[2]
local source_hash = ARGV[3]
local raw = redis.call('GET', key)

local function claim()
  redis.call('SET', key, processing)
  return { 'claimed', processing }
end

if not raw then
  return claim()
end

local ok, current = pcall(cjson.decode, raw)
if ok and type(current) == 'string' then
  ok, current = pcall(cjson.decode, current)
end
if not ok or type(current) ~= 'table' then
  return claim()
end

local allow_ready_reclaim = ARGV[4] == '1'

if current['state'] == 'ready'
  and allow_ready_reclaim ~= true
  and type(current['pack']) == 'table'
  and type(current['pack']['provenance']) == 'table'
  and type(current['pack']['transcript']) == 'table'
  and type(current['pack']['transcript']['full_text']) == 'string'
  and current['pack']['provenance']['source_hash'] == source_hash then
  return { 'existing', raw }
end

if current['state'] == 'processing' and current['source_hash'] == source_hash then
  local started_at = current['started_at']
  local valid_iso = type(started_at) == 'string'
    and string.match(started_at, '^%d%d%d%d%-%d%d%-%d%dT%d%d:%d%d:%d%d%.%d%d%dZ$')
  if valid_iso and started_at > stale_before then
    return { 'existing', raw }
  end
end

return claim()
`;

const memoryStore = new Map<string, VideoPackRecord>();

let redisPromise: Promise<VideoPackRedisClient | null> | null = null;

function assertDurableVideoPackStorageConfigured(): void {
  if (process.env.NODE_ENV !== 'production') return;
  if (resolveUpstashRedisCredentials()) return;
  throw new Error(
    'Durable video pack storage is not configured in production. Set UPSTASH_REDIS_REST_URL + UPSTASH_REDIS_REST_TOKEN (or KV_REST_API_URL + KV_REST_API_TOKEN).',
  );
}

/** Redis/KV key for a pack row keyed by canonical 64-char `source_hash`. */
export function packStoreKey(sourceHash: string): string {
  return `${VIDEO_PACK_STORE_PREFIX}${sourceHash}`;
}

function logPackStoreEvent(payload: Record<string, unknown>): void {
  console.log(JSON.stringify({ scope: 'video-pack-store', ...payload }));
}

async function packStoreSignalFromRedis(
  redis: VideoPackRedisClient | null,
): Promise<PackStoreSignal> {
  if (resolveUpstashRedisCredentials()) {
    if (redis) {
      return { backend: 'upstash', ok: true };
    }
    return { backend: 'unavailable', ok: false };
  }
  if (process.env.NODE_ENV === 'production') {
    return { backend: 'unavailable', ok: false };
  }
  return { backend: 'memory', ok: true };
}

/** Probe configured backend without reading a pack key (for health JSON). */
export async function getPackStoreSignal(): Promise<PackStoreSignal> {
  const redis = await getRedis();
  return packStoreSignalFromRedis(redis);
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
  const promise = (async (): Promise<VideoPackRedisClient | null> => {
    const creds = resolveUpstashRedisCredentials();
    if (!creds) {
      return null;
    }
    try {
      const { Redis } = await import('@upstash/redis');
      return new Redis({
        url: creds.url,
        token: creds.token,
      }) as unknown as VideoPackRedisClient;
    } catch (error) {
      console.error('[video-pack-store] Redis client init failed:', error);
      // Clear the memoized promise so a transient init failure does not
      // permanently poison the client, and fall back to the in-memory store.
      redisPromise = null;
      return null;
    }
  })();
  redisPromise = promise;
  return promise;
}

export async function getVideoPackRedisForServer(): Promise<VideoPackRedisClient | null> {
  return getRedis();
}

function asRecord(value: unknown): VideoPackRecord | null {
  if (value === null || typeof value !== 'object') return null;
  const row = value as VideoPackRecord;
  if (
    row.state === 'ready' &&
    row.pack &&
    typeof row.pack === 'object' &&
    typeof row.pack.provenance?.source_hash === 'string' &&
    row.pack.provenance.source_hash.length === 64 &&
    row.pack.transcript &&
    typeof row.pack.transcript === 'object' &&
    typeof row.pack.transcript.full_text === 'string'
  ) {
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

function decodeRecord(value: unknown): VideoPackRecord | null {
  let decoded = value;
  for (let attempt = 0; attempt < 2 && typeof decoded === 'string'; attempt += 1) {
    try {
      decoded = JSON.parse(decoded) as unknown;
    } catch {
      return null;
    }
  }
  return asRecord(decoded);
}

function readLocalPackRecord(key: string, sourceHash: string): VideoPackRecord | null {
  const local = memoryStore.get(key);
  if (local && recordHash(local) === sourceHash) {
    return local;
  }
  return null;
}

/**
 * Load a pack by `source_hash`, distinguishing a true miss from a durable store failure.
 */
export async function getPackRecordWithMeta(sourceHash: string): Promise<PackLookupResult> {
  const key = packStoreKey(sourceHash);
  const started = Date.now();
  const redis = await getRedis();
  const baseSignal = await packStoreSignalFromRedis(redis);

  if (redis) {
    try {
      const raw = await redis.get<unknown>(key);
      const parsed = decodeRecord(raw);
      if (parsed && recordHash(parsed) === sourceHash) {
        memoryStore.set(key, parsed);
        logPackStoreEvent({
          event: 'pack_get',
          source_hash: sourceHash,
          outcome: 'hit',
          backend: baseSignal.backend,
          duration_ms: Date.now() - started,
        });
        return { outcome: 'hit', record: parsed, store: baseSignal };
      }
      const local = readLocalPackRecord(key, sourceHash);
      if (local) {
        logPackStoreEvent({
          event: 'pack_get',
          source_hash: sourceHash,
          outcome: 'hit',
          backend: baseSignal.backend,
          cache: 'memory',
          duration_ms: Date.now() - started,
        });
        return { outcome: 'hit', record: local, store: baseSignal };
      }
      logPackStoreEvent({
        event: 'pack_get',
        source_hash: sourceHash,
        outcome: 'miss',
        backend: baseSignal.backend,
        duration_ms: Date.now() - started,
      });
      return { outcome: 'miss', store: baseSignal };
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      logPackStoreEvent({
        event: 'pack_get',
        source_hash: sourceHash,
        outcome: 'store_error',
        backend: baseSignal.backend,
        error: message,
        duration_ms: Date.now() - started,
      });
      const cached = readLocalPackRecord(key, sourceHash);
      if (cached) {
        return {
          outcome: 'hit',
          record: cached,
          store: { backend: baseSignal.backend, ok: false },
        };
      }
      return {
        outcome: 'store_error',
        store: { backend: baseSignal.backend, ok: false },
        error: message,
      };
    }
  }

  const local = readLocalPackRecord(key, sourceHash);
  if (local) {
    logPackStoreEvent({
      event: 'pack_get',
      source_hash: sourceHash,
      outcome: 'hit',
      backend: 'memory',
      duration_ms: Date.now() - started,
    });
    return { outcome: 'hit', record: local, store: { backend: 'memory', ok: true } };
  }
  logPackStoreEvent({
    event: 'pack_get',
    source_hash: sourceHash,
    outcome: 'miss',
    backend: baseSignal.backend,
    duration_ms: Date.now() - started,
  });
  return { outcome: 'miss', store: baseSignal };
}

export async function getPackRecord(sourceHash: string): Promise<VideoPackRecord | null> {
  const result = await getPackRecordWithMeta(sourceHash);
  if (result.outcome === 'hit') {
    return result.record;
  }
  return null;
}

export async function putPackRecord(record: VideoPackRecord): Promise<void> {
  const key = packStoreKey(recordHash(record));
  const redis = await getRedis();
  if (redis) {
    try {
      await redis.set(key, record);
    } catch (error) {
      console.error('[video-pack-store] Redis set failed:', error);
      throw error;
    }
  }
  memoryStore.set(key, record);
}

export type ClaimPackProcessingOptions = {
  /** When true, replace a ready pack so Studio Run can re-extract (structured schema upgrade). */
  reclaimReady?: boolean;
};

export async function claimPackProcessing(
  identity: PackProcessingIdentity,
  now: Date = new Date(),
  options: ClaimPackProcessingOptions = {},
): Promise<'claimed' | VideoPackRecord> {
  assertDurableVideoPackStorageConfigured();
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
  if (process.env.NODE_ENV === 'production' && !redis) {
    throw new Error('Durable video pack storage is unavailable in production.');
  }
  const reclaimReady = options.reclaimReady === true ? '1' : '0';
  if (redis) {
    try {
      const result = await redis.eval<unknown>(
        CLAIM_PROCESSING_SCRIPT,
        [key],
        [
          JSON.stringify(processing),
          new Date(now.getTime() - PROCESSING_STALE_MS).toISOString(),
          identity.source_hash,
          reclaimReady,
        ],
      );
      if (!Array.isArray(result) || result.length < 2) {
        throw new Error('Redis claim script returned an invalid result.');
      }
      if (result[0] === 'claimed') {
        memoryStore.set(key, processing);
        return 'claimed';
      }
      const current = decodeRecord(result[1]);
      if (result[0] === 'existing' && current) {
        memoryStore.set(key, current);
        return current;
      }
      throw new Error('Redis claim script returned an invalid record.');
    } catch (error) {
      console.error('[video-pack-store] Redis claim failed:', error);
      throw error;
    }
  }

  const local = memoryStore.get(key);
  if (local?.state === 'ready' && !options.reclaimReady) {
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
  redisPromise = null;
}

export function setVideoPackRedisForTests(redis: VideoPackRedisClient | null): void {
  redisPromise = Promise.resolve(redis);
}

export function seedVideoPackRecordForTests(record: VideoPackRecord): void {
  memoryStore.set(packStoreKey(recordHash(record)), record);
}
