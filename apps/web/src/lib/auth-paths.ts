/**
 * Shared auth and rate-limit path policy for middleware/proxy and unit tests.
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

/** Routes backed by model work, metered against the tighter AI budget. */
const AI_ROUTE_PREFIXES = [
  '/api/agents/dispatch',
  '/api/chat',
  '/api/extract-events',
  '/api/pipeline',
  '/api/realtime',
  '/api/training',
  '/api/transcribe',
  '/api/video',
  '/api/workflows',
] as const;

/**
 * Methods that perform no model work on an otherwise AI-class prefix.
 *
 * `/api/workflows` covers both `POST .../video-to-actions` (starts a run:
 * transcript fetch + action agent, genuinely AI-class) and
 * `GET .../video-to-actions/:runId` (reads stored run state, no model call).
 * Prefix matching alone cannot separate them, so the method has to reach the
 * classifier.
 *
 * This matters more than "one endpoint is metered too tightly", because the
 * rate-limit bucket is keyed by *class*, not by path — every AI prefix shares
 * one `ai:<ip>` counter. A Studio run polls its status ~40x/min against an
 * AI budget defaulting to 12/min, so without this exemption a single run
 * exhausts the shared allowance in ~17s and 429s /api/chat, /api/transcribe
 * and /api/pipeline along with itself.
 *
 * Deliberately keyed per-prefix rather than exempting GET globally: the other
 * prefixes have no polling client, and a blanket GET exemption would be an
 * abuse vector the moment any of them serves model work over GET.
 */
const AI_ROUTE_METHOD_EXEMPT: Record<string, ReadonlySet<string>> = {
  '/api/workflows': new Set(['GET', 'HEAD']),
};

/**
 * Whether a request should be metered against the AI budget rather than the
 * general one.
 *
 * `method` defaults to POST so an omitted argument fails *safe* (stricter
 * limit) rather than silently widening the budget.
 */
export function isAiRoute(pathname: string, method: string = 'POST'): boolean {
  const prefix = AI_ROUTE_PREFIXES.find((candidate) =>
    pathname.startsWith(candidate),
  );
  if (!prefix) return false;
  return !AI_ROUTE_METHOD_EXEMPT[prefix]?.has(method.toUpperCase());
}

/**
 * How the login gate should behave for a given environment.
 *
 * - `enforce`      — NEXTAUTH_SECRET present; validate the session normally.
 * - `misconfigured`— production with no secret: sessions *cannot* be validated,
 *                    so protected routes must fail closed rather than be served
 *                    to anonymous visitors.
 * - `disabled`     — gate intentionally off (local dev, or an explicit opt-out).
 */
export type AuthGateMode = 'enforce' | 'misconfigured' | 'disabled';

function isTruthyFlag(value: string | null | undefined): boolean {
  if (!value) return false;
  return ['1', 'true', 'yes', 'on'].includes(value.trim().toLowerCase());
}

/**
 * Resolve the login-gate mode.
 *
 * Historically this was `!!process.env.NEXTAUTH_SECRET`, which fails *open*: a
 * single missing env var in production silently served /dashboard and every
 * non-public /api/* route to anonymous visitors, with no error (issue #1058).
 *
 * The rollout convenience (app keeps working before OAuth is configured) is
 * preserved for non-production, and remains available in production only as an
 * explicit, auditable declaration via AUTH_ALLOW_UNAUTHENTICATED.
 */
export function resolveAuthGateMode(env: {
  secret?: string | null;
  nodeEnv?: string | null;
  allowUnauthenticated?: string | null;
}): AuthGateMode {
  if (env.secret && env.secret.trim().length > 0) return 'enforce';
  if (isTruthyFlag(env.allowUnauthenticated)) return 'disabled';
  if (env.nodeEnv === 'production') return 'misconfigured';
  return 'disabled';
}
