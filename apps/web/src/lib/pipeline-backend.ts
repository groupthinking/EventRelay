import 'server-only';

/**
 * Backwards-compatible surface for Next.js → FastAPI backend calls.
 *
 * The implementation moved to `lib/backend/capability.ts`, which is now the
 * single source of truth for backend resolution (audit finding F3: three modules
 * had each re-implemented it, and all three read only `BACKEND_URL` — a variable
 * this project never sets). This module re-exports so existing call sites and
 * tests keep working unchanged.
 *
 * New code should import from `@/lib/backend/capability` directly and prefer
 * `resolveBackendCapability()` / `resolveBuildTarget()` over reading env vars.
 */

export {
  backendHeaders,
  resolveBackendStatusUrl,
  parseBackendJson,
} from '@/lib/backend/capability';
