import type { Redis } from '@upstash/redis';
import { resolveUpstashRedisCredentials } from './redis-credentials';

/**
 * Construct an Upstash REST client from either `UPSTASH_REDIS_REST_*` or
 * Vercel KV `KV_REST_API_*` environment variables, returning `null` when
 * neither pair is configured or the SDK fails to load.
 */
export async function createUpstashRedisClient(): Promise<Redis | null> {
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
  } catch {
    return null;
  }
}
