import 'server-only';

/**
 * Backwards-compatible health surface, now delegating to
 * `lib/backend/capability.ts` (audit finding F3).
 *
 * The behavioural change worth knowing about: `getBackendConfig()` and
 * `checkBackendHealth()` previously consulted `BACKEND_URL` only, so they
 * reported `configured: false` on every production deployment of this project.
 * They now resolve through the shared candidate list — `BACKEND_URL`,
 * `NEXT_PUBLIC_BACKEND_URL`, `NEXT_PUBLIC_API_URL` — so the live backend is
 * finally detected. Return shapes are unchanged.
 */

import {
  BACKEND_HEALTH_TIMEOUT_MS,
  checkBackendHealth as checkCapabilityHealth,
  resolveBackendCapability,
  type BackendHealth,
} from '@/lib/backend/capability';

export { parseBackendJson } from '@/lib/backend/capability';
export type { BackendHealth } from '@/lib/backend/capability';

/** @deprecated Prefer `BACKEND_HEALTH_TIMEOUT_MS` from `@/lib/backend/capability`. */
export const PIPELINE_HEALTH_TIMEOUT_MS = BACKEND_HEALTH_TIMEOUT_MS;

/**
 * Resolve the backend base URL.
 *
 * @deprecated Prefer `resolveBackendCapability()`, which also reports *which*
 * env var supplied the value and why resolution failed.
 */
export function getBackendConfig(): { configured: boolean; url: string } {
  const capability = resolveBackendCapability();
  return {
    configured: capability.configured,
    // Legacy contract: empty string rather than null when unconfigured.
    url: capability.url ?? '',
  };
}

/**
 * Probe the backend health endpoint.
 *
 * Accepts a positional timeout for backwards compatibility with the original
 * signature; `@/lib/backend/capability` exposes the richer options object.
 */
export function checkBackendHealth(
  timeoutMs: number = BACKEND_HEALTH_TIMEOUT_MS,
): Promise<BackendHealth> {
  return checkCapabilityHealth({ timeoutMs });
}
