import 'server-only';

/** Documented env names that may hold the FastAPI origin. First http(s) wins. */
export const BACKEND_URL_ENV_KEYS = [
  'BACKEND_URL',
  'NEXT_PUBLIC_BACKEND_URL',
  'NEXT_PUBLIC_API_URL',
] as const;

/**
 * Resolve the configured EventRelay backend origin.
 * Production Studio Attempt deploy reads these names — do not invent a host.
 */
export function resolveConfiguredBackendUrl(): string | null {
  for (const key of BACKEND_URL_ENV_KEYS) {
    const raw = (process.env[key] || '').trim();
    if (!raw) continue;
    try {
      const parsed = new URL(raw);
      if (parsed.protocol !== 'http:' && parsed.protocol !== 'https:') continue;
      return raw.replace(/\/+$/, '');
    } catch {
      continue;
    }
  }
  return null;
}

/**
 * Shared headers for Next.js → FastAPI backend calls.
 * Trims EVENTRELAY_API_KEY to avoid Secret Manager newline mismatches.
 */
export function backendHeaders(extra?: Record<string, string>): Record<string, string> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...extra,
  };
  const apiKey = process.env.EVENTRELAY_API_KEY?.trim();
  if (apiKey) {
    headers['X-API-Key'] = apiKey;
  }
  return headers;
}

/** Resolve and validate a backend job status URL (blocks SSRF before sending API key). */
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