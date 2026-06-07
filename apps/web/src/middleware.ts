import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';
import { getToken } from 'next-auth/jwt';

/**
 * Frontend edge middleware: rate limiting (always) + login gating (when configured).
 *
 * Rate limiting is best-effort/per-instance on serverless — it caps bursts per IP
 * against a warm instance but does not defeat distributed attackers. For production
 * use Vercel Firewall/BotID and/or a KV-backed limiter.
 *
 * Login gating is enforced ONLY when NEXTAUTH_SECRET is set, so the app keeps
 * working until OAuth is configured (safe rollout). When enabled, /dashboard and
 * /api/* require a valid NextAuth session, except the public API prefixes below.
 *
 * Tunables (env): API_RATE_LIMIT_PER_MIN (default 60; <=0 disables),
 *   INTERNAL_REQUEST_TOKEN (server-to-server calls sending a matching
 *   `x-eventrelay-internal` header bypass both rate limiting and auth),
 *   NEXTAUTH_SECRET (presence activates gating).
 */

const WINDOW_MS = 60_000;
const MAX_REQ = Number(process.env.API_RATE_LIMIT_PER_MIN ?? '60');
const INTERNAL_TOKEN = process.env.INTERNAL_REQUEST_TOKEN;
const AUTH_SECRET = process.env.NEXTAUTH_SECRET;
const AUTH_ENABLED = !!AUTH_SECRET;

// API paths that stay public even when auth is enabled (auth flow + health).
const PUBLIC_API_PREFIXES = ['/api/auth', '/api/health'];

const hits = new Map<string, { count: number; reset: number }>();

function clientIp(req: NextRequest): string {
  const xff = req.headers.get('x-forwarded-for');
  if (xff) return xff.split(',')[0]!.trim();
  return req.headers.get('x-real-ip') ?? 'unknown';
}

function rateLimited(req: NextRequest): NextResponse | null {
  if (!Number.isFinite(MAX_REQ) || MAX_REQ <= 0) return null;
  const ip = clientIp(req);
  const now = Date.now();
  const rec = hits.get(ip);
  if (!rec || now > rec.reset) {
    hits.set(ip, { count: 1, reset: now + WINDOW_MS });
    if (hits.size > 10_000) {
      for (const [k, v] of hits) if (now > v.reset) hits.delete(k);
    }
    return null;
  }
  rec.count += 1;
  if (rec.count > MAX_REQ) {
    const retryAfter = Math.ceil((rec.reset - now) / 1000);
    return new NextResponse(JSON.stringify({ error: 'Too many requests', retryAfter }), {
      status: 429,
      headers: { 'content-type': 'application/json', 'retry-after': String(retryAfter) },
    });
  }
  return null;
}

export async function middleware(req: NextRequest) {
  const path = req.nextUrl.pathname;

  // Server-to-server loopback calls bypass both rate limiting and auth.
  if (INTERNAL_TOKEN && req.headers.get('x-eventrelay-internal') === INTERNAL_TOKEN) {
    return NextResponse.next();
  }

  const limited = rateLimited(req);
  if (limited) return limited;

  if (AUTH_ENABLED) {
    const isApi = path.startsWith('/api/');
    const isPublicApi = PUBLIC_API_PREFIXES.some((p) => path === p || path.startsWith(p + '/'));
    const needsAuth =
      (isApi && !isPublicApi) || path === '/dashboard' || path.startsWith('/dashboard/');
    if (needsAuth) {
      // next-auth resolves `NextRequest` from a second hoisted copy of `next`
      // in this monorepo; the types are structurally identical, so bridge them.
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const token = await getToken({ req: req as any, secret: AUTH_SECRET });
      if (!token) {
        if (isApi) {
          return new NextResponse(JSON.stringify({ error: 'Authentication required' }), {
            status: 401,
            headers: { 'content-type': 'application/json' },
          });
        }
        const signin = new URL('/api/auth/signin', req.url);
        signin.searchParams.set('callbackUrl', req.url);
        return NextResponse.redirect(signin);
      }
    }
  }

  return NextResponse.next();
}

export const config = {
  matcher: ['/api/:path*', '/dashboard', '/dashboard/:path*'],
};
