import type { NextRequest, NextResponse } from 'next/server';
import { proxy } from '@/proxy';

/**
 * Next.js middleware entrypoint.
 *
 * Runs login gating + rate limiting from `src/proxy.ts` for:
 * - /dashboard and nested product routes (session required)
 * - /api/* (session required except public allowlist in `@/lib/auth-paths`)
 *
 * Gating is resolved by `resolveAuthGateMode` (see `@/lib/auth-paths`):
 * - `enforce`      — NEXTAUTH_SECRET set: sessions are required.
 * - `misconfigured`— production with no secret: fail CLOSED with 503. A login
 *                    cannot succeed without the secret, so redirecting would
 *                    loop; 503 surfaces the operator error instead.
 * - `disabled`     — non-production, or an explicit AUTH_ALLOW_UNAUTHENTICATED
 *                    opt-out: routes are open.
 *
 * See config/agent_network.json (rate-limit-middleware agent) and the confirmed
 * remediation outcome + verification methods for full context.
 *
 * NOTE: The explicit `Promise<NextResponse>` return type is required. Without it,
 * Next.js 16 Turbopack NFT (Node File Trace) generation fails during the production
 * build with "ENOENT: ... middleware.js.nft.json".
 */
export async function middleware(request: NextRequest): Promise<NextResponse> {
  return proxy(request);
}

export const config = {
  matcher: [
    '/dashboard',
    '/dashboard/:path*',
    '/api/:path*',
  ],
};
