import 'server-only';

/**
 * Single source of truth for "can we reach the FastAPI build backend, and how?"
 *
 * ## Why this module exists (audit findings F1–F3)
 *
 * Three modules independently re-implemented backend resolution:
 *   - `action-tools.resolveBackendBaseUrl()`
 *   - `pipeline-backend-health.getBackendConfig()`
 *   - `pipeline-backend.backendHeaders()`
 *
 * All three read `process.env.BACKEND_URL` **only**. That variable is not set in
 * this project — the deployed backend is exposed as `NEXT_PUBLIC_BACKEND_URL`
 * (and is already whitelisted in the `next.config.js` CSP `connect-src`). The
 * result: every agent-dispatch, build, and deploy tool returned
 * `isError: true` in production against a backend that was reachable the whole
 * time. The product's entire "agents build it" half was dead on a naming bug.
 *
 * This is the *same* class of bug the repo already solved once for Redis, where
 * `resolveUpstashRedisCredentials()` accepts both the canonical
 * `UPSTASH_REDIS_REST_*` names and the `KV_REST_API_*` names that Vercel's
 * marketplace integration injects. This module applies that proven pattern to
 * the backend URL: **accept every name the platform might supply, in a defined
 * precedence order, and resolve to one typed capability object.**
 *
 * ## Capability, not configuration
 *
 * Callers receive a `BackendCapability` describing what is actually possible
 * right now. Nothing in the delivery pipeline may read `process.env.BACKEND_URL`
 * directly again — a step either has a capability object or it does not, which
 * makes degradation explicit and the tools unit-testable.
 */

import { resolveUpstashRedisCredentials } from '@/lib/billing/redis-credentials';

/** Env var names checked, in precedence order. Server-only names come first. */
const URL_ENV_CANDIDATES = [
  'BACKEND_URL',
  'NEXT_PUBLIC_BACKEND_URL',
  'NEXT_PUBLIC_API_URL',
] as const;

export type BackendUrlSource = (typeof URL_ENV_CANDIDATES)[number];

export interface BackendCapability {
  /** True when a usable backend origin was resolved. */
  configured: boolean;
  /** Normalised origin with no trailing slash, or null when unresolved. */
  url: string | null;
  /** Which env var supplied the value — surfaced in diagnostics and the UI. */
  source: BackendUrlSource | null;
  /** Host only, for logging without leaking a full URL with any credentials. */
  host: string | null;
  /** Why resolution failed, when `configured` is false. */
  reason?: string;
}

export interface BackendHealth {
  configured: boolean;
  available: boolean;
  host: string | null;
  source: BackendUrlSource | null;
  /** True when this result came from the KV cache rather than a live probe. */
  cached?: boolean;
  reason?: string;
}

export const BACKEND_HEALTH_TIMEOUT_MS = 5_000;
/** Short TTL: long enough that a multi-step run probes once, short enough to notice recovery. */
const HEALTH_CACHE_TTL_SECONDS = 30;
const HEALTH_CACHE_KEY = 'backend:health:v1';

/**
 * Reject a backend origin that points somewhere a production deployment can
 * never legitimately reach. This is config authored by us rather than
 * user-supplied input, so the full DNS-resolving `assertPublicHttpUrl` guard is
 * not warranted here — but a value left pointing at localhost is a real and
 * common deploy mistake, and silently accepting it produces confusing
 * connection failures deep inside a run instead of one clear reason up front.
 */
function isUnreachableInProduction(hostname: string): boolean {
  const host = hostname.toLowerCase().replace(/\.$/, '').replace(/^\[|\]$/g, '');
  return (
    host === 'localhost' ||
    host === '::1' ||
    host === '0.0.0.0' ||
    host.startsWith('127.') ||
    host.endsWith('.internal') ||
    host.endsWith('.local') ||
    // RFC1918 / link-local, the ranges a Vercel function cannot route to.
    host.startsWith('10.') ||
    host.startsWith('192.168.') ||
    host.startsWith('169.254.') ||
    /^172\.(1[6-9]|2\d|3[01])\./.test(host)
  );
}

/**
 * Resolve the backend capability from the environment.
 *
 * Pure and synchronous — safe to call per-step without I/O. Use
 * {@link checkBackendHealth} when liveness matters.
 */
export function resolveBackendCapability(
  // Typed as a plain string map rather than `NodeJS.ProcessEnv`: this function
  // only ever reads string-valued keys, and requiring the full ProcessEnv shape
  // forced callers (tests especially) into an unsafe `as NodeJS.ProcessEnv`
  // cast just to pass a two-key object.
  env: Readonly<Record<string, string | undefined>> = process.env,
): BackendCapability {
  const unreachable: string[] = [];

  for (const name of URL_ENV_CANDIDATES) {
    const raw = env[name]?.trim();
    if (!raw) continue;

    let parsed: URL;
    try {
      parsed = new URL(raw);
    } catch {
      unreachable.push(`${name} is not a valid URL`);
      continue;
    }

    if (parsed.protocol !== 'http:' && parsed.protocol !== 'https:') {
      unreachable.push(`${name} has unsupported scheme ${parsed.protocol}`);
      continue;
    }

    // Only enforce the production reachability rule in production; local dev
    // legitimately points at 127.0.0.1.
    if (env.NODE_ENV === 'production' && isUnreachableInProduction(parsed.hostname)) {
      unreachable.push(`${name} points at non-routable host ${parsed.hostname}`);
      continue;
    }

    return {
      configured: true,
      url: raw.replace(/\/+$/, ''),
      source: name,
      host: parsed.host,
    };
  }

  return {
    configured: false,
    url: null,
    source: null,
    host: null,
    reason: unreachable.length
      ? `No usable backend URL: ${unreachable.join('; ')}`
      : `No backend URL configured (checked ${URL_ENV_CANDIDATES.join(', ')})`,
  };
}

/**
 * Shared headers for Next.js → FastAPI calls.
 * Trims `EVENTRELAY_API_KEY` to avoid Secret Manager newline mismatches.
 */
export function backendHeaders(extra?: Record<string, string>): Record<string, string> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...extra,
  };
  const apiKey = process.env.EVENTRELAY_API_KEY?.trim();
  if (apiKey) headers['X-API-Key'] = apiKey;
  return headers;
}

/**
 * Resolve and validate a backend-supplied job status URL before we send it our
 * API key. The backend hands back a `status_url` that we then poll; if that
 * value were ever attacker-influenced, blindly following it would leak the
 * `X-API-Key` header to another origin. Pinning to the known backend origin
 * closes that. Preserved verbatim from `pipeline-backend.ts`.
 */
export function resolveBackendStatusUrl(statusUrl: string, backendUrl: string): string {
  const backendOrigin = new URL(backendUrl).origin;
  const base = backendUrl.replace(/\/$/, '');
  const resolved = statusUrl.startsWith('http')
    ? statusUrl
    : `${base}${statusUrl.startsWith('/') ? statusUrl : `/${statusUrl}`}`;

  const parsed = new URL(resolved);
  if (parsed.origin !== backendOrigin) {
    throw new Error(
      `Refusing to poll job status at untrusted origin ${parsed.origin} (expected ${backendOrigin})`,
    );
  }
  return parsed.toString();
}

/** Parse backend JSON safely; returns null when the body is HTML or malformed. */
export async function parseBackendJson<T>(response: Response): Promise<T | null> {
  const text = await response.text();
  const trimmed = text.trim();
  if (!trimmed.startsWith('{') && !trimmed.startsWith('[')) return null;
  try {
    return JSON.parse(trimmed) as T;
  } catch {
    return null;
  }
}

// ── Health, with a short KV cache ──

/**
 * The KV cache is disabled under test. Unit tests stub global `fetch` to assert
 * on the health probe; if the cache also went through that stub it would consume
 * the mock and make results depend on call ordering.
 */
function cacheEnabled(): boolean {
  return process.env.NODE_ENV !== 'test';
}

async function readCachedHealth(): Promise<BackendHealth | null> {
  if (!cacheEnabled()) return null;
  const creds = resolveUpstashRedisCredentials();
  if (!creds) return null;
  try {
    const res = await fetch(`${creds.url}/get/${HEALTH_CACHE_KEY}`, {
      headers: { Authorization: `Bearer ${creds.token}` },
      cache: 'no-store',
      signal: AbortSignal.timeout(2_000),
    });
    if (!res.ok) return null;
    const body = (await res.json()) as { result?: string | null };
    if (!body.result) return null;
    return { ...(JSON.parse(body.result) as BackendHealth), cached: true };
  } catch {
    // A cache miss must never fail the caller — fall through to a live probe.
    return null;
  }
}

async function writeCachedHealth(health: BackendHealth): Promise<void> {
  if (!cacheEnabled()) return;
  const creds = resolveUpstashRedisCredentials();
  if (!creds) return;
  try {
    await fetch(
      `${creds.url}/set/${HEALTH_CACHE_KEY}?EX=${HEALTH_CACHE_TTL_SECONDS}`,
      {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${creds.token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(health),
        signal: AbortSignal.timeout(2_000),
      },
    );
  } catch {
    // Best-effort only.
  }
}

/**
 * Probe the backend's `/api/v1/health`.
 *
 * Cached in KV for {@link HEALTH_CACHE_TTL_SECONDS} so a multi-step delivery run
 * does not re-probe on every step. Pass `{ fresh: true }` to bypass the cache.
 */
export async function checkBackendHealth(
  options: { timeoutMs?: number; fresh?: boolean } = {},
): Promise<BackendHealth> {
  const { timeoutMs = BACKEND_HEALTH_TIMEOUT_MS, fresh = false } = options;
  const capability = resolveBackendCapability();

  if (!capability.configured || !capability.url) {
    return {
      configured: false,
      available: false,
      host: null,
      source: null,
      reason: capability.reason,
    };
  }

  if (!fresh) {
    const cached = await readCachedHealth();
    // Only trust the cache if it describes the same host we resolve today.
    if (cached && cached.host === capability.host) return cached;
  }

  let health: BackendHealth;
  try {
    const response = await fetch(`${capability.url}/api/v1/health`, {
      cache: 'no-store',
      headers: backendHeaders(),
      signal: AbortSignal.timeout(timeoutMs),
    });
    health = {
      configured: true,
      available: response.ok,
      host: capability.host,
      source: capability.source,
      reason: response.ok ? undefined : `Backend health returned ${response.status}`,
    };
  } catch (error) {
    health = {
      configured: true,
      available: false,
      host: capability.host,
      source: capability.source,
      reason: error instanceof Error ? error.message : String(error),
    };
  }

  await writeCachedHealth(health);
  return health;
}

/**
 * Module-scope backend config: whether a backend is configured and its URL.
 *
 * Preserves the `pipeline-backend-health.getBackendConfig()` shape so existing
 * call sites keep working, but resolves through the shared candidate list.
 */
export function getBackendConfig(): { configured: boolean; url: string | null } {
  const capability = resolveBackendCapability();
  return { configured: capability.configured, url: capability.url };
}

/**
 * A `BackendHealth` for the "never probed" case.
 *
 * Call sites that skip the probe (because no backend is configured) previously
 * hand-wrote an object literal here. Those literals omitted `source` and
 * `reason`, which widened the inferred union and made `backendHealth.reason`
 * a type error at the use site. Constructing it here keeps every branch on one
 * shape.
 */
export function unprobedHealth(reason = 'No backend configured.'): BackendHealth {
  return {
    configured: false,
    available: false,
    host: null,
    source: null,
    reason,
  };
}

/**
 * Adapter for the legacy module-scope idiom that was copy-pasted across six
 * route/service files:
 *
 * ```ts
 * const rawBackendUrl = process.env.BACKEND_URL || '';
 * const BACKEND_URL = rawBackendUrl.startsWith('http') ? rawBackendUrl : 'http://localhost:8000';
 * const BACKEND_AVAILABLE = rawBackendUrl.startsWith('http');
 * ```
 *
 * Two problems it had, beyond reading the wrong env var: the `localhost:8000`
 * placeholder is a live URL that only stays harmless while every call site
 * remembers to check `BACKEND_AVAILABLE` first, and each copy could drift from
 * the others. This helper keeps the same two-value shape so call sites need a
 * one-line change, while routing resolution through the shared candidate list.
 *
 * `url` is non-null only when `available` is true; callers that ignored the
 * availability flag now get an empty string instead of a plausible-looking
 * localhost URL that silently fails in production.
 */
export function resolveLegacyBackend(): { url: string; available: boolean } {
  const capability = resolveBackendCapability();
  return {
    url: capability.url ?? '',
    available: capability.configured,
  };
}

/**
 * Convenience for build steps: the capability plus live health in one call, so a
 * step can decide between delegating to FastAPI and running the in-process
 * fallback without duplicating the branch.
 */
export async function resolveBuildTarget(): Promise<{
  capability: BackendCapability;
  health: BackendHealth;
  /** True only when the backend is configured AND currently answering. */
  canDelegate: boolean;
}> {
  const capability = resolveBackendCapability();
  const health = await checkBackendHealth();
  return {
    capability,
    health,
    canDelegate: capability.configured && health.available,
  };
}
