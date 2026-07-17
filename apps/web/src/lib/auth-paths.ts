/**
 * Shared auth path policy for middleware/proxy and unit tests.
 * Keep this free of Next.js request types so vitest can import it offline.
 */

/** API routes that must stay reachable without a session when auth is enabled. */
const PUBLIC_API_PREFIXES = [
  '/api/auth', // NextAuth sign-in / callback / csrf / session
  '/api/health', // ops probes (if present)
] as const;

/** Exact public API paths (prefix match would over-expose siblings). */
const PUBLIC_API_EXACT = new Set([
  // Stripe webhook verifies signature itself — must not require a user session.
  '/api/billing/webhook',
  // Free-tier status + acquisition checkout are pre-login surfaces.
  // Checkout is additionally protected by Turnstile inside the route handler.
  '/api/billing/status',
  '/api/billing/checkout',
  // Post-checkout activation: a brand-new payer has no NextAuth session yet.
  // The route establishes identity from the Stripe checkout sessionId (verified
  // against Stripe / the checkout store), so gating it behind a NextAuth token
  // would 401 legitimate first-time activations. It cannot be forged without a
  // real Stripe session id, so it is safe to keep session-optional here.
  '/api/billing/activate',
  // Returning-user renewal: identity comes from the HMAC-signed billing cookie
  // (or anonymous), not a NextAuth session; it only opens a Stripe checkout, so
  // it is the same pre-payment surface class as /api/billing/checkout.
  '/api/billing/renew',
  // Core pipeline SSE endpoint — the primary public entry point for the
  // EventRelay workflow (YouTube link → transcript → events → agents).
  // Must be accessible without a session so anonymous users can run the
  // pipeline; the route handler applies its own rate limiting via proxy.ts.
  '/api/pipeline/stream',
]);

/** App routes that require a session when NEXTAUTH_SECRET is configured. */
const PROTECTED_PAGE_PREFIXES = ['/dashboard'] as const;

export function isPublicApiPath(pathname: string): boolean {
  if (PUBLIC_API_EXACT.has(pathname)) return true;
  return PUBLIC_API_PREFIXES.some(
    (prefix) => pathname === prefix || pathname.startsWith(`${prefix}/`),
  );
}

export function isProtectedPagePath(pathname: string): boolean {
  return PROTECTED_PAGE_PREFIXES.some(
    (prefix) => pathname === prefix || pathname.startsWith(`${prefix}/`),
  );
}

export function needsAuthentication(pathname: string): boolean {
  if (pathname.startsWith('/api/')) {
    return !isPublicApiPath(pathname);
  }
  return isProtectedPagePath(pathname);
}

/**
 * Build a same-origin relative callback path for NextAuth.
 * Rejects protocol-relative and absolute external URLs to prevent open redirects.
 */
export function safeCallbackPath(pathname: string, search = ''): string {
  const candidate = `${pathname}${search}`;
  if (!candidate.startsWith('/') || candidate.startsWith('//')) {
    return '/dashboard';
  }
  // Block backslash tricks and encoded schemes
  if (candidate.includes('\\') || /^\/[a-z]+:/i.test(candidate)) {
    return '/dashboard';
  }
  return candidate;
}

/** Skip rate limiting for auth handshake traffic (csrf, callback, session). */
export function shouldSkipRateLimit(pathname: string): boolean {
  return pathname === '/api/auth' || pathname.startsWith('/api/auth/');
}
