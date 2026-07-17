import { NextResponse } from 'next/server';

/**
 * GET /api/health
 * Lightweight liveness probe for uptime monitors and load balancers.
 *
 * This path is allowlisted in `@/lib/auth-paths` (PUBLIC_API_PREFIXES) so it is
 * reachable without a session. It intentionally has no external dependencies —
 * it only confirms the Next.js runtime is serving requests. For richer service
 * metadata use `GET /api` instead.
 */
export function GET() {
  return NextResponse.json(
    {
      status: 'ok',
      timestamp: new Date().toISOString(),
    },
    {
      headers: { 'Cache-Control': 'no-store' },
    },
  );
}
