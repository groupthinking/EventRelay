import type { Redis } from '@upstash/redis';

const memoryCounts = new Map<string, number>();

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

function dayKey(subject: string): string {
  const day = new Date().toISOString().slice(0, 10);
  return `er:chatquota:${subject}:${day}`;
}

export type QuotaResult = {
  allowed: boolean;
  used: number;
  limit: number;
};

export async function checkFreeChatQuota(
  subject: string,
  limit: number,
): Promise<QuotaResult> {
  const key = dayKey(subject);
  const redis = await getRedis();
  if (redis) {
    try {
      const used = await redis.incr(key);
      if (used === 1) {
        await redis.expire(key, 86_400 + 300);
      }
      return { allowed: used <= limit, used, limit };
    } catch {
      // fall through
    }
  }
  const used = (memoryCounts.get(key) ?? 0) + 1;
  memoryCounts.set(key, used);
  return { allowed: used <= limit, used, limit };
}

export function resetChatQuotaForTests(): void {
  memoryCounts.clear();
  redisPromise = null;
}