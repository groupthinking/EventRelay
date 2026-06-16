import { NextRequest, NextResponse } from 'next/server';

const WINDOW_SECONDS = 60;
const GENERAL_LIMIT = Number(process.env.UVAI_API_RATE_LIMIT_PER_MINUTE || 60);
const AI_LIMIT = Number(process.env.UVAI_AI_RATE_LIMIT_PER_MINUTE || 12);

const AI_ROUTE_PREFIXES = [
  '/api/agents/dispatch',
  '/api/chat',
  '/api/extract-events',
  '/api/pipeline',
  '/api/realtime',
  '/api/training',
  '/api/transcribe',
  '/api/video',
];

type RateLimitResult = {
  allowed: boolean;
  limit: number;
  remaining: number;
  resetAt: number;
};

type MemoryBucket = {
  count: number;
  resetAt: number;
};

/**
 * In-process memory cache is ONLY for local dev without Redis.
 * Per Vercel Functions best practices and the confirmed remediation outcome,
 * production MUST use Redis (Upstash) or explicitly fail-open with warning.
 * The global Map is unsuitable for serverless scaling.
 */
const memoryBuckets = new Map<string, MemoryBucket>();

let prodRedisWarned = false;

function isAiRoute(pathname: string): boolean {
  return AI_ROUTE_PREFIXES.some((prefix) => pathname.startsWith(prefix));
}

function getClientIp(request: NextRequest): string {
  const forwardedFor = request.headers.get('x-forwarded-for');
  if (forwardedFor) {
    return forwardedFor.split(',')[0]?.trim() || 'unknown';
  }

  return request.headers.get('x-real-ip') || 'unknown';
}

function getRateLimit(pathname: string): number {
  return isAiRoute(pathname) ? AI_LIMIT : GENERAL_LIMIT;
}

async function checkRedisLimit(redisClient: any, key: string, limit: number): Promise<RateLimitResult> {
  const now = Date.now();
  const bucket = Math.floor(now / (WINDOW_SECONDS * 1000));
  const resetAt = (bucket + 1) * WINDOW_SECONDS;
  const redisKey = `uvai:ratelimit:${key}:${bucket}`;
  const count = await redisClient.incr(redisKey);

  if (count === 1) {
    await redisClient.expire(redisKey, WINDOW_SECONDS + 5);
  }

  return {
    allowed: count <= limit,
    limit,
    remaining: Math.max(0, limit - count),
    resetAt,
  };
}

function checkMemoryLimit(key: string, limit: number): RateLimitResult {
  const now = Date.now();
  const existing = memoryBuckets.get(key);
  const resetAt =
    existing && existing.resetAt > now
      ? existing.resetAt
      : now + WINDOW_SECONDS * 1000;
  const count = existing && existing.resetAt > now ? existing.count + 1 : 1;

  memoryBuckets.set(key, { count, resetAt });

  return {
    allowed: count <= limit,
    limit,
    remaining: Math.max(0, limit - count),
    resetAt: Math.ceil(resetAt / 1000),
  };
}

async function checkRateLimit(request: NextRequest): Promise<RateLimitResult> {
  const pathname = request.nextUrl.pathname;
  const limit = getRateLimit(pathname);
  const clientIp = getClientIp(request);
  const routeClass = isAiRoute(pathname) ? 'ai' : 'api';
  const key = `${routeClass}:${clientIp}`;

  let redisClient = null;
  if (process.env.UPSTASH_REDIS_REST_URL && process.env.UPSTASH_REDIS_REST_TOKEN) {
    try {
      const { Redis } = await import('@upstash/redis');
      redisClient = new Redis({
        url: process.env.UPSTASH_REDIS_REST_URL,
        token: process.env.UPSTASH_REDIS_REST_TOKEN,
      });
    } catch (e) {
      // dynamic import failed; fall through to fallback
    }
  }

  if (!redisClient && process.env.NODE_ENV === 'production' && !prodRedisWarned) {
    console.warn(
      '[RateLimit] No UPSTASH_REDIS_* configured in production. Rate limiting is bypassed (fail-open) to avoid silent in-process state. ' +
      'Configure Upstash for enforcement. See src/proxy.ts and the rate-limit-middleware agent in config/agent_network.json.'
    );
    prodRedisWarned = true;
  }

  if (redisClient) {
    try {
      return await checkRedisLimit(redisClient, key, limit);
    } catch (error) {
      if (process.env.NODE_ENV !== 'production') {
        console.warn('Upstash rate limit check failed; using in-memory fallback.', error);
      } else {
        console.warn('Upstash rate limit check failed in production; failing open.', error);
      }
    }
  }

  // Memory fallback strictly for non-production (dev / local).
  if (process.env.NODE_ENV !== 'production') {
    return checkMemoryLimit(key, limit);
  }

  // Production without Redis: fail-open (allowed) with the warning already emitted above.
  return {
    allowed: true,
    limit,
    remaining: limit,
    resetAt: Math.ceil((Date.now() + WINDOW_SECONDS * 1000) / 1000),
  };
}

export async function proxy(request: NextRequest) {
  if (
    process.env.UVAI_RATE_LIMIT_DISABLED === '1' ||
    request.method === 'OPTIONS'
  ) {
    return NextResponse.next();
  }

  const result = await checkRateLimit(request);

  if (!result.allowed) {
    return NextResponse.json(
      { error: 'Rate limit exceeded. Please try again shortly.' },
      {
        status: 429,
        headers: {
          'Cache-Control': 'no-store',
          'Retry-After': String(WINDOW_SECONDS),
          'X-RateLimit-Limit': String(result.limit),
          'X-RateLimit-Remaining': '0',
          'X-RateLimit-Reset': String(result.resetAt),
        },
      },
    );
  }

  const response = NextResponse.next();
  response.headers.set('X-RateLimit-Limit', String(result.limit));
  response.headers.set('X-RateLimit-Remaining', String(result.remaining));
  response.headers.set('X-RateLimit-Reset', String(result.resetAt));
  return response;
}

// NOTE: The old `export const config` was moved to the real middleware.ts (apps/web/middleware.ts)
// so that the rate limiter is actually executed by Next.js for /api/* paths.
// This file now exports only the `proxy` logic (and the hardened dev-only memory behavior).
