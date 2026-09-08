import { NextRequest, NextResponse } from 'next/server';
import { getToken } from 'next-auth/jwt';
import {
  canonicalStudioPath,
  isAiRoute,
  isLegacyDashboardPath,
  needsAuthentication,
  resolveAuthGateMode,
  safeCallbackPath,
  shouldSkipRateLimit,
} from '@/lib/auth-paths';

/**
 * Frontend proxy (Next.js 16): rate limiting + login gating.
 *
 * Login gating activates when NEXTAUTH_SECRET is configured. When it is *not*
 * configured the behaviour depends on the environment (see resolveAuthGateMode):
 * outside production the gate is simply off (safe rollout / local dev), but in
 * production the request fails closed with 503 instead of being served
 * anonymously (issue #1058). Set AUTH_ALLOW_UNAUTHENTICATED=1 to deliberately
 * run a public production deployment.
 *
 * When enforcing, non-public /api/* require a valid NextAuth session.
 * `/dashboard` is a retired skin and 308s to the public studio — it is not
 * a login gate. Server-to-server loopback calls carrying a matching
 * `x-eventrelay-internal` header (INTERNAL_REQUEST_TOKEN) bypass both.
 *
 * Path policy lives in `@/lib/auth-paths` so unit tests can cover it offline.
 */

const WINDOW_SECONDS = 60;
const GENERAL_LIMIT = Number(process.env.UVAI_API_RATE_LIMIT_PER_MINUTE || 60);
const AI_LIMIT = Number(process.env.UVAI_AI_RATE_LIMIT_PER_MINUTE || 12);

// Login gating (activate-when-configured) + server-to-server bypass.
const INTERNAL_TOKEN = process.env.INTERNAL_REQUEST_TOKEN;
const AUTH_SECRET = process.env.NEXTAUTH_SECRET;
const AUTH_GATE_MODE = resolveAuthGateMode({
  secret: AUTH_SECRET,
  nodeEnv: process.env.NODE_ENV,
  allowUnauthenticated: process.env.AUTH_ALLOW_UNAUTHENTICATED,
});
const AUTH_ENABLED = AUTH_GATE_MODE === 'enforce';

if (AUTH_GATE_MODE === 'misconfigured') {
  // Logged once at module init rather than per request: this is a boot-time
  // deployment fault, and per-request logging would flood the sink.
  console.error(
    '[auth] NEXTAUTH_SECRET is not set in production — sessions cannot be verified. ' +
      'Protected routes will return 503 until it is configured. ' +
      'Set AUTH_ALLOW_UNAUTHENTICATED=1 only if this deployment is intentionally public.',
  );
}

type RateLimitResult = {
  allowed: boolean;
  limit: number;
  remaining: number;
  resetAt: number;
  unavailable?: boolean;
};

type MemoryBucket = {
  count: number;
  resetAt: number;
};

type DistributedRedisClient = {
  incr(key: string): Promise<number>;
  expire(key: string, seconds: number): Promise<number | boolean>;
};

/**
 * In-process memory cache is ONLY for local dev without Redis.
 * Per Vercel Functions best practices and the confirmed remediation outcome,
 * production MUST use distributed Redis. Expensive AI routes fail closed when
 * distributed enforcement is unavailable; other API routes fail open with a
 * warning so a Redis outage does not take down unrelated product surfaces.
 * The global Map is unsuitable for serverless scaling.
 */
const memoryBuckets = new Map<string, MemoryBucket>();

let prodRedisWarned = false;

let redisClientPromise: Promise<DistributedRedisClient | null> | null = null;

/**
 * Lazily construct one distributed Redis client and reuse it across requests.
 * Upstash REST is preferred when configured. Vercel Marketplace integrations
 * that expose a standard `STORAGE_REDIS_URL` are supported through node-redis.
 * Both clients are memoized at module scope so warm Vercel instances reuse the
 * transport instead of reconnecting for every request.
 *
 * The initialization promise is memoized so concurrent callers await the same
 * in-flight construction rather than racing — without this, a request arriving
 * while the dynamic import is still pending could observe a half-initialized
 * state and incorrectly fall open.
 */
function getRedisClient(): Promise<DistributedRedisClient | null> {
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

    if (process.env.STORAGE_REDIS_URL) {
      try {
        const { createClient } = await import('redis');
        const client = createClient({ url: process.env.STORAGE_REDIS_URL });
        client.on('error', () => {
          // Commands are guarded below and fail closed for paid AI routes.
        });
        await client.connect();
        return client;
      } catch {
        return null;
      }
    }

    return null;
  })();

  return redisClientPromise;
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

function getRateLimit(pathname: string, method: string): number {
  return isAiRoute(pathname, method) ? AI_LIMIT : GENERAL_LIMIT;
}

async function checkRedisLimit(
  redisClient: DistributedRedisClient,
  key: string,
  limit: number,
): Promise<RateLimitResult> {
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
  const method = request.method;
  const limit = getRateLimit(pathname, method);
  const clientIp = getClientIp(request);
  const routeClass = isAiRoute(pathname, method) ? 'ai' : 'api';
  const key = `${routeClass}:${clientIp}`;

  const redisClient = await getRedisClient();

  if (!redisClient && process.env.NODE_ENV === 'production' && !prodRedisWarned) {
    console.warn(
      '[RateLimit] No distributed Redis configured in production. Expensive AI routes will fail closed; other APIs remain available. ' +
      'Configure Upstash REST or STORAGE_REDIS_URL for distributed enforcement.',
    );
    prodRedisWarned = true;
  }

  if (redisClient) {
    try {
      return await checkRedisLimit(redisClient, key, limit);
    } catch (error) {
      if (process.env.NODE_ENV !== 'production') {
        console.warn('Distributed rate limit check failed; using in-memory fallback.', error);
      } else {
        console.warn('Distributed rate limit check failed in production.', error);
      }
    }
  }

  // Memory fallback strictly for non-production (dev / local).
  if (process.env.NODE_ENV !== 'production') {
    return checkMemoryLimit(key, limit);
  }

  // Do not expose paid model/video operations without a distributed limiter.
  if (isAiRoute(pathname, method)) {
    return {
      allowed: false,
      limit,
      remaining: 0,
      resetAt: Math.ceil((Date.now() + WINDOW_SECONDS * 1000) / 1000),
      unavailable: true,
    };
  }

  // Non-AI production routes remain available during a Redis outage.
  return {
    allowed: true,
    limit,
    remaining: limit,
    resetAt: Math.ceil((Date.now() + WINDOW_SECONDS * 1000) / 1000),
  };
}

// Surface a loud warning at module init if the general API limiter is disabled.
if (
  process.env.UVAI_RATE_LIMIT_DISABLED === '1' &&
  process.env.NODE_ENV === 'production'
) {
  console.warn(
    '[RateLimit] UVAI_RATE_LIMIT_DISABLED=1 — general API limiting is off; paid AI routes still require Redis.',
  );
}

export async function proxy(request: NextRequest): Promise<NextResponse> {
  const pathname = request.nextUrl.pathname;

  // Server-to-server loopback calls bypass both rate limiting and auth.
  if (INTERNAL_TOKEN && request.headers.get('x-eventrelay-internal') === INTERNAL_TOKEN) {
    return NextResponse.next();
  }

  // Retired library skin: stay in OneLoopStudio instead of login or the
  // old dashboard chrome. Query (e.g. ?video=) is preserved.
  if (isLegacyDashboardPath(pathname)) {
    const dest = request.nextUrl.clone();
    dest.pathname = canonicalStudioPath();
    return NextResponse.redirect(dest, 308);
  }

  // Fail closed: in production without NEXTAUTH_SECRET a session cannot be
  // verified, so protected routes must not be served anonymously (issue #1058).
  // 503 (not 401/redirect) is deliberate — sign-in also cannot succeed without
  // the secret, so redirecting to /login would loop forever. Public paths stay
  // reachable so an operator can still complete OAuth setup.
  if (
    AUTH_GATE_MODE === 'misconfigured' &&
    request.method !== 'OPTIONS' &&
    needsAuthentication(pathname)
  ) {
    const body = 'Authentication is not configured on this deployment.';
    return pathname.startsWith('/api/')
      ? NextResponse.json({ error: body }, { status: 503 })
      : new NextResponse(body, {
          status: 503,
          headers: { 'content-type': 'text/plain; charset=utf-8' },
        });
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
      const signin = new URL('/login', request.url);
      // Relative same-origin path only — blocks open-redirect callback abuse.
      signin.searchParams.set(
        'callbackUrl',
        safeCallbackPath(request.nextUrl.pathname, request.nextUrl.search),
      );
      return NextResponse.redirect(signin);
    }
  }

  if (
    (process.env.UVAI_RATE_LIMIT_DISABLED === '1' &&
      (process.env.NODE_ENV !== 'production' || !isAiRoute(pathname, request.method))) ||
    request.method === 'OPTIONS' ||
    // Page routes under the matcher are handled above (legacy dashboard 308).
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
      {
        error: result.unavailable
          ? 'AI processing is temporarily unavailable because distributed rate limiting is not configured.'
          : 'Rate limit exceeded. Please try again shortly.',
      },
      {
        status: result.unavailable ? 503 : 429,
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

// Next 16 discovers this file directly. The explicit allowlist means Workflow's
// internal `/.well-known/workflow/*` requests are never intercepted.
export const config = {
  matcher: [
    '/dashboard',
    '/dashboard/:path*',
    '/api/:path*',
  ],
};
