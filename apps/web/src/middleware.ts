import type { NextRequest } from 'next/server';
import { NextResponse } from 'next/server';

const CANONICAL_HOST = 'uvai.io';

const allowedHosts = new Set<string>([
  CANONICAL_HOST,
  `www.${CANONICAL_HOST}`,
  'localhost:3000',
  '127.0.0.1:3000',
  '0.0.0.0:3000',
]);

export function middleware(request: NextRequest) {
  const host = request.headers.get('host');
  const isDev = process.env.NODE_ENV !== 'production';

  if (!host || isDev || allowedHosts.has(host)) {
    return NextResponse.next();
  }

  const url = new URL(request.url);
  url.hostname = CANONICAL_HOST;
  url.protocol = 'https:';
  url.port = '';

  return NextResponse.redirect(url, 308);
}

export const config = {
  matcher: '/:path*',
};
