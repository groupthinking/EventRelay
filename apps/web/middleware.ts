import type { NextRequest, NextResponse } from 'next/server';
import { proxy } from '@/proxy';

/**
 * Standard Next.js middleware that activates the rate limiting logic from src/proxy.ts
 * for all /api/* routes. This makes the rate limiter "active" as claimed in runbooks.
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
  matcher: ['/api/:path*'],
};
