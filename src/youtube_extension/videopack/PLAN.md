# TASK: Fix Next.js static parse of /api/v1/video/pack runtime

## 1. Goal & Scope
* **Objective:** Restore a passing Vercel `v0-uvai` `next build` after PR 1612. The v1 pack alias must declare a literal `export const runtime = 'nodejs'` (or omit it) and must not re-export route-segment config. Anonymous POST `/api/video/pack` and `/api/v1/video/pack` keep emitting hashed Video Pack v0 with `source_url` + `source_hash` even without a transcript.
* **Context:** Commit `25b4de4552030dd0e00e41f11ad7bfda72a3ec4f` added `apps/web/src/app/api/v1/video/pack/route.ts` as `export { POST, runtime } from '../../../video/pack/route'`. Next.js cannot statically parse a re-exported `runtime`. Production uvai.io is not serving that commit.
* **Scope:**
  * `apps/web/src/app/api/v1/video/pack/route.ts` — literal runtime + POST that calls the same identity-pack handler.
  * Shared handler extracted into existing `apps/web/src/lib/video-pack.ts` so neither route re-exports config or imports a sibling route file.
  * `apps/web/src/app/api/video/pack/route.ts` — call the shared handler; keep literal runtime.
  * Regression test: v1 route source is statically parseable (literal `runtime`, no `export { … runtime }`).
  * Existing CoS tests remain locked.
 * *Initial Check: Existing v1 route file is the defect; do not add a second pack format or a new route tree.*

## 2. Execution Plan
- [x] Lock failing source-format test on the v1 route
- [x] Extract identity-pack POST handler; give v1 a literal `runtime` + wrapper POST
- [x] Verify CoS pack tests + `next build` no longer fails on this file
- [x] Open PR against main with Closes #1613 (issue create returned 403; reuse the open pack-emit issue)

## 3. Definition of Done (Success Verification)
* **Expected Outcome:** `next build` does not report a route-segment-config parse error at `apps/web/src/app/api/v1/video/pack/route.ts`. Anonymous POSTs still return 200 Video Pack v0 with `source_url` + `source_hash`.
* **Verification Method:**
  * `cd apps/web && npx vitest run src/app/api/v1/video/pack src/app/api/video/pack src/lib/__tests__/video-pack.test.ts src/lib/__tests__/emit-video-pack.test.ts src/lib/__tests__/auth-paths.test.ts`
  * `cd apps/web && npm run build`
* **Proof Artifact:** Head `346b276f8`. Vitest 42 passed (5 files). `next build` compiled successfully and listed `ƒ /api/v1/video/pack` and `ƒ /api/video/pack`. No route-segment-config parse error.

## 4. Post-Task Reflection
* **What was done:** Replaced `export { POST, runtime }` on the v1 pack alias with a literal `export const runtime = 'nodejs'` and a POST wrapper that calls shared `handleIdentityPackPost`. Moved that handler into `apps/web/src/lib/video-pack.ts` so neither route re-exports config.
* **Why it was needed:** After #1612, Vercel `v0-uvai` `next build` failed because Next cannot statically parse a re-exported `runtime`. uvai.io is not serving `25b4de455`.
* **How it was tested:** Source-format test failed on the re-export (RED), then passed after the literal runtime (GREEN). CoS emit tests still return hashed v0 packs with `source_url` + `source_hash`. `npm run build` in `apps/web` exited 0.
