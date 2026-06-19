import { getToken } from 'next-auth/jwt';
import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

/**
 * Auth middleware — gate API routes behind a valid NextAuth JWT session.
 *
 * Behavior:
 * - /api/auth/* is always public (NextAuth's own handlers).
 * - /api/* returns 401 unless the request carries a valid session token.
 * - When AUTH_DISABLED=true or NEXTAUTH_SECRET is unset, middleware is bypassed
 *   entirely (dev mode / environments without OAuth configured).
 *
 * This runs on the Edge runtime for performance.
 */

const AUTH_DISABLED =
  process.env.AUTH_DISABLED === 'true' || !process.env.NEXTAUTH_SECRET;

export async function middleware(request: NextRequest) {
  // Skip auth enforcement when not configured (dev / preview deploys)
  if (AUTH_DISABLED) {
    return NextResponse.next();
  }

  const token = await getToken({
    req: request,
    secret: process.env.NEXTAUTH_SECRET,
  });

  if (!token) {
    return NextResponse.json(
      { error: 'Authentication required' },
      { status: 401 },
    );
  }

  return NextResponse.next();
}

/**
 * Match all /api/* routes EXCEPT /api/auth/* (NextAuth's own endpoints).
 */
export const config = {
  matcher: ['/api/((?!auth).*)'],
};
