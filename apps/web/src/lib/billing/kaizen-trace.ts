import type { Redis } from '@upstash/redis';
import { appendFile } from 'node:fs/promises';

export type KaizenTraceEntry = {
  ts: string;
  flow: string;
  stage: string;
  observation: string;
  decision?: string;
  fix?: string;
};

const traceLog: KaizenTraceEntry[] = [];
const KAIZEN_REDIS_KEY = 'er:kaizen:traces';

let redisPromise: Promise<Redis | null> | null = null;

async function getRedis(): Promise<Redis | null> {
  if (redisPromise) return redisPromise;
  redisPromise = (async () => {
    if (!process.env.UPSTASH_REDIS_REST_URL || !process.env.UPSTASH_REDIS_REST_TOKEN) {
      return null;
    }
    try {
      const { Redis } = await import('@upstash/redis');
      return new Redis({
        url: process.env.UPSTASH_REDIS_REST_URL,
        token: process.env.UPSTASH_REDIS_REST_TOKEN,
      });
    } catch {
      return null;
    }
  })();
  return redisPromise;
}

async function persistEntry(entry: KaizenTraceEntry): Promise<void> {
  const line = JSON.stringify(entry);
  const path = process.env.KAIZEN_TRACE_PATH;
  if (path) {
    try {
      await appendFile(path, `${line}\n`, 'utf8');
    } catch {
      // non-fatal
    }
  }
  const redis = await getRedis();
  if (redis) {
    try {
      await redis.rpush(KAIZEN_REDIS_KEY, line);
      await redis.ltrim(KAIZEN_REDIS_KEY, -500, -1);
    } catch {
      // non-fatal
    }
  }
}

export function kaizenObserve(
  flow: string,
  stage: string,
  observation: string,
  extra?: Pick<KaizenTraceEntry, 'decision' | 'fix'>,
): KaizenTraceEntry {
  const entry: KaizenTraceEntry = {
    ts: new Date().toISOString(),
    flow,
    stage,
    observation,
    ...extra,
  };
  traceLog.push(entry);
  if (process.env.KAIZEN_TRACE_LOG !== '0') {
    console.info('[kaizen]', JSON.stringify(entry));
  }
  void persistEntry(entry);
  return entry;
}

export function getKaizenTraces(flow?: string): KaizenTraceEntry[] {
  return flow ? traceLog.filter((e) => e.flow === flow) : [...traceLog];
}

export async function loadKaizenTracesFromRedis(limit = 50): Promise<string[]> {
  const redis = await getRedis();
  if (!redis) return [];
  try {
    return (await redis.lrange(KAIZEN_REDIS_KEY, -limit, -1)) as string[];
  } catch {
    return [];
  }
}

export function resetKaizenTracesForTests(): void {
  traceLog.length = 0;
  redisPromise = null;
}