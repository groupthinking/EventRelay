import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

/**
 * Best-effort rate limiting for the frontend BFF API routes (`/api/*`).
 *
 * IMPORTANT — what this is and is not:
 * - It caps request bursts per client IP against a single warm serverless
 *   instance. Instances are ephemeral and distributed, so a determined or
 *   distributed attacker is NOT fully stopped by this alone.
 * - It is NOT authentication. `next-auth` is a dependency but is currently
 *   unconfigured (no provider, no session), so these routes have no user auth.
 *
 * For production-grade protection, layer on:
 *   - Vercel Firewall / BotID (dashboard config), and/or
 *   - a KV-backed limiter (e.g. @upstash/ratelimit) for distributed counting, and
 *   - real auth (wire next-auth) once the access model is decided.
 *
 * Tunables (env): API_RATE_LIMIT_PER_MIN (default 60; <=0 disables),
 *   INTERNAL_REQUEST_TOKEN (server-to-server calls that send a matching
 *   `x-eventrelay-internal` header bypass the limit).
 */

const WINDOW_MS = 60_000;
const MAX_REQ = Number(process.env.API_RATE_LIMIT_PER_MIN ?? '60');
const INTERNAL_TOKEN = process.env.INTERNAL_REQUEST_TOKEN;

const hits = new Map<string, { count: number; reset: number }>();

function clientIp(req: NextRequest): string {
  const xff = req.headers.get('x-forwarded-for');
  if (xff) return xff.split(',')[0]!.trim();
  return req.headers.get('x-real-ip') ?? 'unknown';
}

export function middleware(req: NextRequest) {
  // Server-to-server loopback calls (e.g. /api/video → /api/transcribe) bypass.
  if (INTERNAL_TOKEN && req.headers.get('x-eventrelay-internal') === INTERNAL_TOKEN) {
    return NextResponse.next();
  }
  if (!Number.isFinite(MAX_REQ) || MAX_REQ <= 0) {
    return NextResponse.next(); // limiter disabled
  }

  const ip = clientIp(req);
  const now = Date.now();
  const rec = hits.get(ip);

  if (!rec || now > rec.reset) {
    hits.set(ip, { count: 1, reset: now + WINDOW_MS });
    // Opportunistic cleanup so the Map cannot grow unbounded on a warm instance.
    if (hits.size > 10_000) {
      for (const [k, v] of hits) if (now > v.reset) hits.delete(k);
    }
    return NextResponse.next();
  }

  rec.count += 1;
  if (rec.count > MAX_REQ) {
    const retryAfter = Math.ceil((rec.reset - now) / 1000);
    return new NextResponse(
      JSON.stringify({ error: 'Too many requests', retryAfter }),
      {
        status: 429,
        headers: {
          'content-type': 'application/json',
          'retry-after': String(retryAfter),
        },
      },
    );
  }
  return NextResponse.next();
}

export const config = {
  matcher: '/api/:path*',
};
