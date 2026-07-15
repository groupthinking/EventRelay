/**
 * Upstash Search client (full-text + semantic search over indexed documents).
 *
 * Complements the per-video vector search in `gemini-embedding.ts` /
 * `embedding-store.ts` (which is scoped to one video's transcript chunks and
 * backed by ephemeral storage) with a durable, cross-video index hosted on
 * Upstash. Reads config at call time so a deploy picks up env changes without
 * module-load ordering concerns — same pattern as `vercel-ai-gateway.ts`.
 *
 * Required env (Vercel project / apps/web/.env.local):
 *   UPSTASH_SEARCH_REST_URL
 *   UPSTASH_SEARCH_REST_TOKEN      (admin token — server-side only)
 * Optional:
 *   UPSTASH_SEARCH_INDEX           (default: "videos")
 */

import { Search } from '@upstash/search';

export const DEFAULT_SEARCH_INDEX = 'videos';

export type SearchDocument = {
  id: string;
  content: Record<string, string>;
  metadata?: Record<string, unknown>;
};

export function resolveSearchConfig(): { url: string; token: string } | null {
  const url = process.env.UPSTASH_SEARCH_REST_URL?.trim();
  const token = process.env.UPSTASH_SEARCH_REST_TOKEN?.trim();
  if (!url || !token) return null;
  return { url, token };
}

export function hasUpstashSearch(): boolean {
  return resolveSearchConfig() !== null;
}

export function resolveSearchIndexName(): string {
  return process.env.UPSTASH_SEARCH_INDEX?.trim() || DEFAULT_SEARCH_INDEX;
}

/**
 * Returns a handle to the configured Upstash Search index, or null when the
 * env vars are absent (callers surface an honest 503 — never fake results).
 */
export function getSearchIndex() {
  const config = resolveSearchConfig();
  if (!config) return null;
  const client = new Search({ url: config.url, token: config.token });
  return client.index(resolveSearchIndexName());
}
