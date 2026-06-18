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