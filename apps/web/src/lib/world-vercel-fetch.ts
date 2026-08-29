/**
 * `@workflow/world-vercel` builds an `undici.Agent` from the npm `undici`
 * package (7.28.0 in its package.json) and passes it as `fetch(..., { dispatcher })`.
 *
 * On Vercel, `globalThis.fetch` is Node 22 / Next's fetch (undici 6). An Agent
 * from undici 7 is a different class — `dispatch` then throws
 * `Cannot read private member #P` (issue #1538). Sentry wrapping only puts
 * `Proxy.dispatch` on the stack; #1541 proved skipOpenTelemetrySetup is not enough.
 *
 * Bind global fetch to the *same* `undici` module for the duration of `start()`.
 */
export async function withWorldVercelFetch<T>(fn: () => Promise<T>): Promise<T> {
  const { fetch: undiciFetch } = await import('undici');
  const previous = globalThis.fetch;
  globalThis.fetch = undiciFetch as unknown as typeof fetch;
  try {
    return await fn();
  } finally {
    globalThis.fetch = previous;
  }
}
