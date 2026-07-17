/**
 * Path policy for the frontend proxy/middleware, extracted so it can be unit
 * tested offline (no NextRequest / runtime env required).
 *
 * These helpers replicate the previously-inline logic in `src/proxy.ts`:
 *  - which paths require an authenticated session when auth is enabled,
 *  - how to build a safe (same-origin, relative) post-login callback path,
 *  - which API paths are exempt from rate limiting.
 */

// API paths that stay public even when auth is enabled (auth flow + health + billing webhooks).
const PUBLIC_API_PREFIXES = ['/api/auth', '/api/health', '/api/billing'];

// API paths that must never be rate limited (auth flow + health checks).
const RATE_LIMIT_SKIP_PREFIXES = ['/api/health', '/api/auth'];

function matchesPrefix(pathname: string, prefix: string): boolean {
  return pathname === prefix || pathname.startsWith(prefix + '/');
}

/**
 * True when a request to `pathname` requires a valid session (auth enabled).
 * Mirrors the pre-refactor rule:
 *   (isApi && !isPublicApi) || pathname === '/dashboard' || pathname.startsWith('/dashboard/')
 */
export function needsAuthentication(pathname: string): boolean {
  const isApi = pathname.startsWith('/api/');
  const isPublicApi = PUBLIC_API_PREFIXES.some((p) => matchesPrefix(pathname, p));
  return (
    (isApi && !isPublicApi) ||
    pathname === '/dashboard' ||
    pathname.startsWith('/dashboard/')
  );
}

/**
 * Build a same-origin, RELATIVE callback path from a pathname + search string.
 * Guards against open-redirect abuse: the result always starts with a single
 * '/', is never protocol-relative ('//') and never an absolute URL. Falls back
 * to '/' when the input cannot be normalized safely.
 */
export function safeCallbackPath(pathname: string, search = ''): string {
  // Reject anything that isn't a plain path (absolute URLs, protocol-relative).
  if (typeof pathname !== 'string' || pathname.length === 0) {
    return '/';
  }

  // Normalize the path portion: must begin with exactly one '/'.
  let path = pathname;
  if (!path.startsWith('/')) {
    path = '/' + path;
  }
  // Collapse leading slashes to a single '/' to block '//host' protocol-relative
  // redirects that browsers treat as absolute (open-redirect vector).
  path = path.replace(/^\/+/, '/');

  // A backslash can be normalized to '/' by browsers; treat it as unsafe.
  if (path.includes('\\')) {
    return '/';
  }

  const query = typeof search === 'string' && search.startsWith('?') ? search : '';
  return path + query;
}

/**
 * True when an API path should be exempt from rate limiting (auth flow + health
 * checks). Used in addition to the caller's `!pathname.startsWith('/api/')`
 * check, so page routes are already excluded.
 */
export function shouldSkipRateLimit(pathname: string): boolean {
  return RATE_LIMIT_SKIP_PREFIXES.some((p) => matchesPrefix(pathname, p));
}
