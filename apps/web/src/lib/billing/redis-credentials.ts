/**
 * Resolve Upstash REST credentials from either the canonical
 * `UPSTASH_REDIS_REST_*` names or the `KV_REST_API_*` names that Vercel's
 * Upstash / KV marketplace integration injects. Both point at the same
 * Upstash-REST-compatible endpoint, so either naming is accepted.
 *
 * This module is intentionally dependency-free (only reads `process.env`) so it
 * is safe to import from the Next.js middleware/proxy edge entrypoint as well as
 * from server code.
 */
export type UpstashRestCredentials = {
  url: string;
  token: string;
};

export function resolveUpstashRedisCredentials(): UpstashRestCredentials | null {
  // Never combine a URL from one credential family with another family's token.
  const upstashUrl = process.env.UPSTASH_REDIS_REST_URL?.trim();
  const upstashToken = process.env.UPSTASH_REDIS_REST_TOKEN?.trim();
  if (upstashUrl && upstashToken) return { url: upstashUrl, token: upstashToken };
  const kvUrl = process.env.KV_REST_API_URL?.trim();
  const kvToken = process.env.KV_REST_API_TOKEN?.trim();
  if (kvUrl && kvToken) return { url: kvUrl, token: kvToken };
  return null;
}
