/**
 * `@workflow/world-vercel` builds an `undici.Agent` from the npm `undici`
 * package (7.28.0 in its package.json) and passes it as `fetch(..., { dispatcher })`.
 *
 * On Vercel, `globalThis.fetch` is Node 22 / Next's fetch (undici 6). An Agent
 * from undici 7 is a different class — `dispatch` then throws
 * `Cannot read private member #P` (issue #1538). Sentry wrapping only puts
 * `Proxy.dispatch` on the stack; #1541 proved skipOpenTelemetrySetup is not enough.
 *
 * Bind string/URL fetches to the same `undici` module for `start()`. `getRun()`
 * calls `fetch(Request)` — undici treats that as a URL string (`[object Request]`).
 * Keep Request inputs on the previous (Next/Node) fetch.
 */
function isFetchRequest(input: unknown): input is Request {
  if (typeof Request !== 'undefined' && input instanceof Request) {
    return true;
  }
  return (
    typeof input === 'object' &&
    input !== null &&
    !(input instanceof URL) &&
    typeof (input as { url?: unknown }).url === 'string'
  );
}

export async function withWorldVercelFetch<T>(fn: () => Promise<T>): Promise<T> {
  const { fetch: undiciFetch } = await import('undici');
  const previous = globalThis.fetch;
  const compatFetch = ((input: RequestInfo | URL, init?: RequestInit) => {
    if (isFetchRequest(input)) {
      return previous.call(globalThis, input, init);
    }
    return undiciFetch(
      input as Parameters<typeof undiciFetch>[0],
      init as Parameters<typeof undiciFetch>[1],
    );
  }) as unknown as typeof fetch;
  globalThis.fetch = compatFetch;
  try {
    return await fn();
  } finally {
    globalThis.fetch = previous;
  }
}
