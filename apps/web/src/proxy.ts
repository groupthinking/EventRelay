import { NextRequest, NextResponse } from 'next/server';
import type { Redis } from '@upstash/redis';
import { getToken } from 'next-auth/jwt';
import { resolveUpstashRedisCredentials } from '@/lib/billing/redis-credentials';

/**
 * Frontend proxy (Next.js 16 middleware): rate limiting (always) + login gating
 * (only when NEXTAUTH_SECRET is configured, so the app keeps working until OAuth
 * is set up — safe rollout). When enabled, /dashboard and non-public /api/* require
 * a valid NextAuth session. Server-to-server loopback calls carrying a matching
 * `x-eventrelay-internal` header (INTERNAL_REQUEST_TOKEN) bypass both.
 */

const WINDOW_SECONDS = 60;
const GENERAL_LIMIT = Number(process.env.UVAI_API_RATE_LIMIT_PER_MINUTE || 60);
const AI_LIMIT = Number(process.env.UVAI_AI_RATE_LIMIT_PER_MINUTE || 12);

const AI_ROUTE_PREFIXES = [
  // Both /api/agents/actions (runActionAgent) and /api/agents/dispatch invoke an
  // LLM per request, so both must fail closed on a limiter outage. The sibling
  // /api/agents/status is a cheap GET and is intentionally left off (fails open).
  '/api/agents/actions',
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
// API paths that stay public even when auth is enabled (auth flow + health).
const PUBLIC_API_PREFIXES = ['/api/auth', '/api/health', '/api/billing'];

type RateLimitResult = {
  allowed: boolean;
  limit: number;
  remaining: number;
  resetAt: number;
  // Set only when `allowed` is false. `exceeded` = a genuine per-client overage
  // (→ 429); `limiter_unavailable` = the limiter itself could not run, e.g. no
  // Redis in production on an AI route (→ 503, this is an outage not a quota).
  reason?: 'exceeded' | 'limiter_unavailable';
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
    // Accept either the canonical `UPSTASH_REDIS_REST_*` names or the
    // `KV_REST_API_*` names that Vercel's Upstash/KV integration injects.
    // Production only provisions the latter, so hardcoding the former left the
    // limiter permanently client-less — the same helper the /api/video/generate
    // route already uses.
    const creds = resolveUpstashRedisCredentials();
    if (creds) {
      try {
        const { Redis } = await import('@upstash/redis');
        return new Redis({ url: creds.url, token: creds.token });
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

// AI-prefixed GET endpoints that are NOT cheap reads: each incurs a paid
// external AI call per request, so they must fail CLOSED on a limiter outage
// exactly like the writes.
//   - GET /api/realtime/session  → mints an OpenAI Realtime client secret
//   - GET /api/video/search      → runs a Gemini embedding of the query
// Every other GET under an AI prefix (e.g. GET /api/video, GET /api/pipeline,
// GET /api/training/status, GET /api/agents/{actions,dispatch}) is a cheap
// status/health/info read and fails OPEN so a Redis outage can't 503 it.
const PAID_AI_GET_ROUTES = ['/api/realtime/session', '/api/video/search'];

function pathMatches(pathname: string, base: string): boolean {
  return pathname === base || pathname.startsWith(base + '/');
}

/**
 * Is THIS request one that incurs a paid AI provider call, and therefore must
 * fail CLOSED when the rate limiter is unavailable (denial-of-wallet)? True for
 * every write to an AI route, plus the handful of AI GETs that are themselves
 * paid calls. Cheap AI GETs (status/health/info) return false and fail open.
 */
function isPaidAiRequest(pathname: string, method: string): boolean {
  if (!isAiRoute(pathname)) {
    return false;
  }
  // Writes to an AI route always trigger the paid model call.
  if (method !== 'GET' && method !== 'HEAD') {
    return true;
  }
  // A small, explicit allowlist of GETs that are paid calls despite being reads.
  return PAID_AI_GET_ROUTES.some((base) => pathMatches(pathname, base));
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

  const allowed = count <= limit;
  return {
    allowed,
    limit,
    remaining: Math.max(0, limit - count),
    resetAt,
    reason: allowed ? undefined : 'exceeded',
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

  const allowed = count <= limit;
  return {
    allowed,
    limit,
    remaining: Math.max(0, limit - count),
    resetAt: Math.ceil(resetAt / 1000),
    reason: allowed ? undefined : 'exceeded',
  };
}

async function checkRateLimit(request: NextRequest): Promise<RateLimitResult> {
  const pathname = request.nextUrl.pathname;
  const limit = getRateLimit(pathname);
  const clientIp = getClientIp(request);
  const routeClass = isAiRoute(pathname) ? 'ai' : 'api';
  const key = `${routeClass}:${clientIp}`;
  // Narrower than routeClass: only requests that actually incur a paid AI call
  // (all AI writes + the paid AI GETs) fail closed on a limiter outage.
  const expensiveOnOutage = isPaidAiRequest(pathname, request.method);

  const redisClient = await getRedisClient();

  if (!redisClient && process.env.NODE_ENV === 'production' && !prodRedisWarned) {
    console.error(
      '[RateLimit] No Upstash/KV Redis configured in production (checked UPSTASH_REDIS_REST_* and KV_REST_API_*). ' +
      'Failing CLOSED for requests that incur a paid AI call (all AI-route writes + the paid AI GETs ' +
      '/api/realtime/session and /api/video/search — denial-of-wallet protection) and OPEN for everything ' +
      'else (non-AI routes AND cheap AI status/health GETs) so a limiter outage cannot take down the API. ' +
      'Configure Upstash or Vercel KV for full enforcement. ' +
      'See src/proxy.ts and the rate-limit-middleware agent in config/agent_network.json.'
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
        console.error(
          'Upstash rate limit check failed in production; failing closed for expensive AI routes.',
          error,
        );
      }
    }
  }

  // Memory fallback strictly for non-production (dev / local).
  if (process.env.NODE_ENV !== 'production') {
    return checkMemoryLimit(key, limit);
  }

  const allowResult: RateLimitResult = {
    allowed: true,
    limit,
    remaining: limit,
    resetAt: Math.ceil((Date.now() + WINDOW_SECONDS * 1000) / 1000),
  };

  // Production without a working Redis limiter. Fail CLOSED only for requests
  // that actually incur a paid AI call — every AI-route write plus the two paid
  // AI GETs (`GET /api/realtime/session` mints an OpenAI Realtime client secret,
  // `GET /api/video/search` runs a Gemini embedding). Failing those open would
  // reopen the denial-of-wallet vector (audit findings #4/#7). Everything else
  // fails OPEN so a limiter outage can't take the API down: not just non-AI
  // routes (billing, auth, health, general API) but also cheap AI status/health
  // GETs (`GET /api/video`, `GET /api/pipeline`, `GET /api/training/status`,
  // `GET /api/agents/{actions,dispatch}`), which are free reads and so should
  // stay available during a Redis outage. The emergency override forces open
  // even for the paid requests.
  if (!expensiveOnOutage || process.env.UVAI_RATE_LIMIT_FAIL_OPEN === '1') {
    if (expensiveOnOutage) {
      console.warn(
        '[RateLimit] UVAI_RATE_LIMIT_FAIL_OPEN=1 — production paid-AI rate limit failing open (emergency).',
      );
    }
    return allowResult;
  }

  // Paid AI request, no Redis, no override: deny. This is a limiter *outage*,
  // not a genuine per-client overage, so it surfaces as 503 (see proxy handler).
  return {
    allowed: false,
    limit,
    remaining: 0,
    resetAt: Math.ceil((Date.now() + WINDOW_SECONDS * 1000) / 1000),
    reason: 'limiter_unavailable',
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
  if (AUTH_ENABLED && request.method !== 'OPTIONS') {
    const isApi = pathname.startsWith('/api/');
    const isPublicApi = PUBLIC_API_PREFIXES.some(
      (p) => pathname === p || pathname.startsWith(p + '/'),
    );
    const needsAuth =
      (isApi && !isPublicApi) || pathname === '/dashboard' || pathname.startsWith('/dashboard/');
    if (needsAuth) {
      // next-auth resolves `NextRequest` from a second hoisted copy of `next` in this
      // monorepo; the types are structurally identical, so bridge them.
      const token = await getToken({ req: request as any, secret: AUTH_SECRET });
      if (!token) {
        if (isApi) {
          return NextResponse.json({ error: 'Authentication required' }, { status: 401 });
        }
        const signin = new URL('/api/auth/signin', request.url);
        signin.searchParams.set('callbackUrl', request.url);
        return NextResponse.redirect(signin);
      }
    }
  }

  if (
    process.env.UVAI_RATE_LIMIT_DISABLED === '1' ||
    request.method === 'OPTIONS'
  ) {
    return NextResponse.next();
  }

  const result = await checkRateLimit(request);

  if (!result.allowed) {
    const outage = result.reason === 'limiter_unavailable';
    return NextResponse.json(
      outage
        ? {
            error: 'Rate limiter temporarily unavailable. Please try again shortly.',
            code: 'rate_limit_unavailable',
          }
        : { error: 'Rate limit exceeded. Please try again shortly.' },
      {
        status: outage ? 503 : 429,
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
