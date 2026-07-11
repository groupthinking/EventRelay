import 'server-only';

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