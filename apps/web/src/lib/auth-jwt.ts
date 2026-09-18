import type { JWT } from 'next-auth/jwt';
import { getToken } from 'next-auth/jwt';

/** Request shape accepted by NextAuth `getToken` (NextRequest or compatible). */
export type NextAuthJwtRequest = NonNullable<Parameters<typeof getToken>[0]['req']>;

type CookieCarrier = {
  headers: Headers | { get(name: string): string | null } | Record<string, string | string[] | undefined>;
  cookies?: {
    getAll?: () => Array<{ name: string; value: string }>;
  } | Record<string, string | undefined> | Map<string, string>;
};

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

function cookieHeaderValue(headers: CookieCarrier['headers']): string {
  if (headers instanceof Headers) return headers.get('cookie') ?? '';
  if (typeof headers.get === 'function') return headers.get('cookie') ?? '';
  if (!('cookie' in headers)) return '';
  const value = headers.cookie;
  return Array.isArray(value) ? value.join('; ') : (value ?? '');
}

function hasReadableCookies(cookies: CookieCarrier['cookies']): boolean {
  if (!cookies) return false;
  if (typeof (cookies as { getAll?: unknown }).getAll === 'function') return true;
  if (cookies instanceof Map) return true;
  return Object.keys(cookies).length > 0;
}

function parseCookieHeader(header: string): Record<string, string> {
  const parsed: Record<string, string> = {};
  if (!header) return parsed;
  for (const chunk of header.split(';')) {
    const entry = chunk.trim();
    if (!entry) continue;
    const separator = entry.indexOf('=');
    if (separator <= 0) continue;
    const key = entry.slice(0, separator).trim();
    const value = entry.slice(separator + 1).trim();
    if (!key || !value) continue;
    try {
      parsed[key] = decodeURIComponent(value);
    } catch {
      parsed[key] = value;
    }
  }
  return parsed;
}

export async function getNextAuthJwtFromRequest(
  req: NextAuthJwtRequest | Request,
  secret: string,
): Promise<JWT | null> {
  const candidate = req as unknown as CookieCarrier;
  const normalizedReq =
    hasReadableCookies(candidate.cookies) || !('headers' in candidate)
      ? req
      : ({
          ...candidate,
          cookies: parseCookieHeader(cookieHeaderValue(candidate.headers)),
        } as unknown as NextAuthJwtRequest);

  return getToken({
    req: normalizedReq as NextAuthJwtRequest,
    secret,
    secureCookie: nextAuthUseSecureCookies(),
  });
}
