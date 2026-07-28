import { NextRequest, NextResponse } from 'next/server';
import type { Redis } from '@upstash/redis';
import { getToken } from 'next-auth/jwt';
import {
  needsAuthentication,
  safeCallbackPath,
  shouldSkipRateLimit,
} from '@/lib/auth-paths';

/**
 * Frontend proxy (Next.js 16 middleware): rate limiting (always) + login gating
 * (only when NEXTAUTH_SECRET is configured, so the app keeps working until OAuth
 * is set up — safe rollout). When enabled, /dashboard and non-public /api/* require
 * a valid NextAuth session. Server-to-server loopback calls carrying a matching
 * `x-eventrelay-internal` header (INTERNAL_REQUEST_TOKEN) bypass both.
 *
 * Path policy lives in `@/lib/auth-paths` so unit tests can cover it offline.
 */

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

// Login gating (activate-when-configured) + server-to-server bypass.
const INTERNAL_TOKEN = process.env.INTERNAL_REQUEST_TOKEN;
const AUTH_SECRET = process.env.NEXTAUTH_SECRET;
const AUTH_ENABLED = !!AUTH_SECRET;

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

let redisClientPromise: Promise<Redis | null> | null = null;

/**
 * Lazily construct the Upstash Redis client once and reuse it across requests.
 * The `@upstash/redis` client is HTTP/REST-based (no connection pool), so a
 * single module-scoped instance is safe and avoids the latency, allocation, and
 * GC overhead of constructing a new client on every request. The dynamic import
 * keeps the dependency out of the statically-bundled middleware entrypoint.
 *
 * The initialization promise is memoized so concurrent callers await the same
 * in-flight construction rather than racing — without this, a request arriving
 * while the dynamic import is still pending could observe a half-initialized
 * state and incorrectly fall open.
 */
function getRedisClient(): Promise<Redis | null> {
  if (redisClientPromise) {
    return redisClientPromise;
  }

  redisClientPromise = (async () => {
    if (process.env.UPSTASH_REDIS_REST_URL && process.env.UPSTASH_REDIS_REST_TOKEN) {
      try {
        const { Redis } = await import('@upstash/redis');
        return new Redis({
          url: process.env.UPSTASH_REDIS_REST_URL,
          token: process.env.UPSTASH_REDIS_REST_TOKEN,
        });
      } catch {
        // dynamic import failed; fall back to null below
        return null;
      }
    }
    return null;
  })();

  return redisClientPromise;
}

function isAiRoute(pathname: string): boolean {
  return AI_ROUTE_PREFIXES.some((prefix) => pathname.startsWith(prefix));
}

function getClientIp(request: NextRequest): string {
  // Prefer x-real-ip: set by Vercel's edge network and not client-controllable.
  const realIp = request.headers.get('x-real-ip');
  if (realIp) {
    return realIp.trim();
  }

  // Fallback: the LAST (rightmost) entry of x-forwarded-for is the one added by
  // the trusted proxy closest to us. The leftmost entry is client-supplied and
  // can be spoofed to bypass per-IP rate limiting.
  const forwardedFor = request.headers.get('x-forwarded-for');
  if (forwardedFor) {
    const entries = forwardedFor.split(',');
    return entries[entries.length - 1]?.trim() || 'unknown';
  }

  return 'unknown';
}

function getRateLimit(pathname: string): number {
  return isAiRoute(pathname) ? AI_LIMIT : GENERAL_LIMIT;
}

async function checkRedisLimit(redisClient: Redis, key: string, limit: number): Promise<RateLimitResult> {
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

  const redisClient = await getRedisClient();

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

// Surface a loud warning at module init if rate limiting is fully disabled in
// production. Combined with the Redis fail-open path, this could otherwise leave
// expensive AI routes entirely unprotected with no signal.
if (
  process.env.UVAI_RATE_LIMIT_DISABLED === '1' &&
  process.env.NODE_ENV === 'production'
) {
  console.warn(
    '[RateLimit] UVAI_RATE_LIMIT_DISABLED=1 — rate limiting is OFF in production.',
  );
}

export async function proxy(request: NextRequest): Promise<NextResponse> {
  const pathname = request.nextUrl.pathname;

  // Server-to-server loopback calls bypass both rate limiting and auth.
  if (INTERNAL_TOKEN && request.headers.get('x-eventrelay-internal') === INTERNAL_TOKEN) {
    return NextResponse.next();
  }

  // Login gating — enforced only when NEXTAUTH_SECRET is set; CORS preflight is exempt.
  if (AUTH_ENABLED && request.method !== 'OPTIONS' && needsAuthentication(pathname)) {
    // next-auth resolves `NextRequest` from a second hoisted copy of `next` in this
    // monorepo; the types are structurally identical, so bridge them.
    const token = await getToken({ req: request as any, secret: AUTH_SECRET });
    if (!token) {
      if (pathname.startsWith('/api/')) {
        return NextResponse.json({ error: 'Authentication required' }, { status: 401 });
      }
      const signin = new URL('/api/auth/signin', request.url);
      // Relative same-origin path only — blocks open-redirect callback abuse.
      signin.searchParams.set(
        'callbackUrl',
        safeCallbackPath(request.nextUrl.pathname, request.nextUrl.search),
      );
      return NextResponse.redirect(signin);
    }
  }

  if (
    process.env.UVAI_RATE_LIMIT_DISABLED === '1' ||
    request.method === 'OPTIONS' ||
    // Page routes (e.g. /dashboard) are matched only for auth gating above.
    // They must not be rate-limited: a JSON 429 would render as a raw blob in
    // the browser and page navigation would burn the shared api:<ip> quota.
    !pathname.startsWith('/api/') ||
    shouldSkipRateLimit(pathname)
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
