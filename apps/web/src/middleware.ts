import { NextRequest, NextResponse } from 'next/server';

/**
 * Legacy hostnames that should redirect to the canonical domain (uvai.io).
 * This middleware enforces the redirect at the Next.js runtime layer as a
 * complement to the Vercel edge-level redirects configured in vercel.json.
 */
const LEGACY_HOSTS = new Set([
  'event-relay-web.vercel.app',
  'v0-uvai.vercel.app',
  'youtube-extension.vercel.app',
  'uvai-io.pages.dev',
  'sell.solutions',
  'www.sell.solutions',
  'myai.directory',
  'www.myai.directory',
]);

const CANONICAL_ORIGIN = 'https://uvai.io';

export function middleware(request: NextRequest): NextResponse {
  const host = request.headers.get('host') ?? '';

  if (LEGACY_HOSTS.has(host)) {
    const url = request.nextUrl.clone();
    const destination = `${CANONICAL_ORIGIN}${url.pathname}${url.search}`;
    return NextResponse.redirect(destination, { status: 308 });
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    /*
     * Match every path except:
     * - _next/static  (Next.js static assets)
     * - _next/image   (Next.js image optimisation)
     * - favicon.ico
     */
    '/((?!_next/static|_next/image|favicon.ico).*)',
  ],
};
