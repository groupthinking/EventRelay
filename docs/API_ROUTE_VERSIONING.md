# API route pairs (`/api` vs `/api/v1`) — AUDIT-005

## Strategy (2026-09-20)

| Pair | Handler | Notes |
| --- | --- | --- |
| `/api/video/pack` | `@/lib/video-pack` | Canonical public identity + extract surface |
| `/api/v1/video/pack` | Same handlers | Compatibility alias; no divergent logic |

Additional `/api` ↔ `/api/v1` pairs follow the same rule: **one implementation module, two route entrypoints** until clients migrate. New surfaces must not add a third path.

## Deprecation policy

1. Shared handler required (no copy-paste route bodies).
2. Deprecation notices live in route file headers and this doc.
3. Removal requires grep showing zero external callers and a changelog entry.

## Verification

`apps/web/src/app/api/v1/**` routes should import from `@/lib/*` or re-export from `/api/**` siblings. Vitest covers both pack paths under `src/app/api/video/pack` and `src/app/api/v1/video/pack`.
