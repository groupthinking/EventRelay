import type { NextRequest } from 'next/server';
import { proxy } from './src/proxy';

/**
 * Standard Next.js middleware that activates the rate limiting logic from src/proxy.ts
 * for all /api/* routes. This makes the rate limiter "active" as claimed in runbooks.
 *
 * See config/agent_network.json (rate-limit-middleware agent) and the confirmed
 * remediation outcome + verification methods for full context.
 */
export async function middleware(request: NextRequest) {
  return proxy(request);
}

export const config = {
  matcher: ['/api/:path*'],
};
