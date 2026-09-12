# TASK: Persist Video Pack specs by source_hash (off the request wall)

## 1. Goal & Scope
* **Objective:** Anonymous POST `/api/video/pack` returns immediately (`processing` or a cached spec). Extraction runs after the response via existing Vercel `waitUntil`. Finished packs persist keyed by identity `source_hash` and are readable without login on the same route (GET).
* **Context:** Live uvai.io (dpl_43XkviiJUCuC1vN85iLTTd3nARy4 / 25e6fbb / PR 1616) extracts a real Gemini 3.8 Flash spec but (1) blocks 74–92s and 503s with `Delay was aborted`, (2) re-extracts every time (in-process Map dies with the lambda), (3) has no anonymous read path.
* **Chosen mechanism (fits this repo + Vercel, no new surface):**
  * **Store:** Upstash Redis via already-wired `KV_REST_API_URL`/`KV_REST_API_TOKEN` (and `UPSTASH_REDIS_REST_*`) using existing `@upstash/redis` + `resolveUpstashRedisCredentials`. Memory fallback for tests/dev. Not Blob (unwired), not Postgres, not Python `storage/video_packs/` (ephemeral on Vercel).
  * **Background:** `@vercel/functions` `waitUntil` — already used by `/api/pipeline` and `/api/video`. First POST claims `processing` (SET NX), schedules extract, returns 202. Client polls GET on the same public path.
  * **Anonymous read:** GET `/api/video/pack?source_hash=` or `?video_id=` (path already on `PUBLIC_API_EXACT`). Listing `/api/video/packs` stays gated / unbuilt.
* **Rejected alternatives:** Vercel Blob (not imported in `apps/web`); Vercel Workflow (new surface); new `/api/video/packs/[hash]` route (new surface).
* **Scope:**
  * `apps/web/src/lib/video-pack-store.ts` — durable record keyed by `source_hash`
  * `apps/web/src/lib/video-pack.ts` — POST returns cache/processing; GET reads; extract via `waitUntil`
  * `apps/web/src/lib/video-pack-extractor.ts` — raise abort to 110s so waitUntil can finish under `maxDuration=120`
  * `apps/web/src/lib/emit-video-pack.ts` — poll GET when POST is processing
  * Pack routes export GET; auth-paths unchanged
 * *Initial Check: Reuse identity hash, extractor, Redis credentials helper. Do not add a second pack format.*

## 2. Execution Plan
- [x] Confirm hash contract, Redis wiring, waitUntil usage, public path allowlist
- [x] Lock failing store + route + emit tests (RED)
- [x] Implement store + async handler + anonymous GET + client poll
- [x] Verify focused Vitest (Gateway mocked, no live billing)
- [ ] Open ready PR against main (issue create 403)

## 3. Definition of Done (Success Verification)
* **Expected Outcome:** Repeat URL is a cache hit (no model call). First request returns fast processing. GET by hash/video_id is anonymous. Fail-closed still 503s with a visible error, never an identity-only success pack. Golden `jNQXAC9IVRw` hash unchanged.
* **Verification Method:**
  * `cd apps/web && npx vitest run src/lib/__tests__/video-pack-store.test.ts src/lib/__tests__/video-pack.test.ts src/lib/__tests__/video-pack-extractor.test.ts src/lib/__tests__/emit-video-pack.test.ts src/app/api/video/pack src/app/api/v1/video/pack src/lib/__tests__/auth-paths.test.ts`
* **Proof Artifact:** `cd apps/web && npx vitest run src/lib/__tests__/video-pack-store.test.ts src/lib/__tests__/video-pack.test.ts src/lib/__tests__/video-pack-extractor.test.ts src/lib/__tests__/emit-video-pack.test.ts src/app/api/video/pack src/app/api/v1/video/pack src/lib/__tests__/auth-paths.test.ts src/store/__tests__/dashboard-store.test.ts` — 8 files, 87 passed. Pack-related `tsc --noEmit` is clean. GitHub `issue_write` returned 403.

## 4. Post-Task Reflection
* **What was done:** Replaced the in-process Map with an Upstash/KV Redis store keyed by identity `source_hash`. POST `/api/video/pack` now returns 202 `processing` (or a cache hit) and runs Gemini 3.8 Flash extract via existing `waitUntil`. GET on the same public path reads the pack without auth.
* **Why it was needed:** Live extract blocked 74–92s and 503'd (`Delay was aborted`); repeats re-paid Gateway; anonymous callers could not read the finished pack.
* **How it was tested:** Vitest mocks `extractVideoPackSpec`. Cache hit does not call the model. Hash golden for `jNQXAC9IVRw` unchanged. Anonymous GET works. Cite-only / Gateway errors stay 503 with no identity-only success body.
