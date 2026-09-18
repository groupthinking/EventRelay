import type { JWT } from 'next-auth/jwt';
import { getToken } from 'next-auth/jwt';

/** Request shape accepted by NextAuth `getToken` (NextRequest or compatible). */
export type NextAuthJwtRequest = NonNullable<Parameters<typeof getToken>[0]['req']>;

/**
 * Must stay aligned with `useSecureCookies` in `@/lib/auth.ts`.
 *
 * NextAuth's default `getToken()` secureCookie only checks `NEXTAUTH_URL` and
 * `VERCEL`. Our auth config also forces secure cookies whenever
 * `NODE_ENV === 'production'`, so callers must pass `secureCookie` explicitly
 * or session verification silently misses the cookie that was actually set.
 */
export function nextAuthUseSecureCookies(): boolean {
  return (
    process.env.NODE_ENV === 'production' ||
    (process.env.NEXTAUTH_URL?.startsWith('https://') ?? false)
  );
}

export async function getNextAuthJwtFromRequest(
  req: NextAuthJwtRequest,
  secret: string,
): Promise<JWT | null> {
  return getToken({
    req,
    secret,
    secureCookie: nextAuthUseSecureCookies(),
  });
}
