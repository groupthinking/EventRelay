# TASK: Gemini 3.8 Flash spec extract on identity Video Pack

## 1. Goal & Scope
* **Objective:** POST `/api/video/pack` (and `/api/v1/video/pack`) returns a v0 spec pack: keep `source_url` + `source_hash`, fill extracted spec content via `google/gemini-3.8-flash` on the existing Vercel AI Gateway. Fail closed if Gateway/model is missing.
* **Context:** Hayden 2026-09-02 lock. Identity Video Pack (hashed cite) is done. Qwen wait is dead. Do not self-host vLLM, bounce to Origin/forge, or default this extractor to `google/gemini-2.5-flash`. Ride Gemini for frames/audio/transcript; do not compete on STT.
* **Scope:**
  * `apps/web/src/lib/video-pack-extractor.ts` — new extractor (AI SDK `generateText`, model pin `google/gemini-3.8-flash`).
  * `apps/web/src/lib/video-pack.ts` — merge extracted spec onto the identity pack; fail closed on Gateway miss.
  * Pack routes — same handler; raise `maxDuration` for video ingest.
  * `apps/web/src/lib/emit-video-pack.ts` — client timeout must cover Gateway video extract.
  * Tests mock `generateText` / Gateway. No live billing.
 * *Initial Check: Reuse identity pack + VideoPackV0 fields. Do not add a second pack format.*

## 2. Execution Plan
- [x] Confirm identity contract (`source_url` + `source_hash`) and existing Gateway helpers
- [x] Lock failing extractor + pack POST tests (RED)
- [x] Implement extractor + merge; fail closed without Gateway key
- [x] Update route / emit tests to expect spec content under mocked Gateway
- [x] Verify focused Vitest; open PR against main

## 3. Definition of Done (Success Verification)
* **Expected Outcome:** Anonymous POST with a YouTube URL returns v0 with identity hash plus non-empty extracted spec (not only `cite:youtube:`). Missing Gateway key returns a visible error status. Extractor call uses `google/gemini-3.8-flash`.
* **Verification Method:**
  * `cd apps/web && npx vitest run src/lib/__tests__/video-pack-extractor.test.ts src/lib/__tests__/video-pack.test.ts src/app/api/video/pack src/app/api/v1/video/pack src/lib/__tests__/emit-video-pack.test.ts`
* **Proof Artifact:** `cd apps/web && npx vitest run src/lib/__tests__/video-pack-extractor.test.ts src/lib/__tests__/video-pack.test.ts src/app/api/video/pack src/app/api/v1/video/pack src/lib/__tests__/emit-video-pack.test.ts` — 5 files, 22 passed. Pack-related `tsc --noEmit` is clean.

## 4. Post-Task Reflection
* **What was done:** Added a Gemini 3.8 Flash spec extractor (`google/gemini-3.8-flash` via AI SDK `generateText`) and merged extracted fields onto the existing v0 identity pack. POST `/api/video/pack` now fail-closes with 503 if Gateway/model extract is missing or empty.
* **Why it was needed:** Identity cite (`cite:youtube:` + hash) was done; paste-URL still did not produce a spec pack. Qwen wait is dead; Gateway Gemini is the plug.
* **How it was tested:** Unit tests inject/mocks `generateText`. No live Gateway billing. Identity `source_hash` golden values unchanged.

## Environment note
`AI_GATEWAY_API_KEY` / `VERCEL_AI_GATEWAY_API_KEY` / `VERCEL_OIDC_TOKEN` are unset in this agent VM. Fail-closed is the production path. Unit tests mock Gateway and do not hit live billing. GitHub `issue_write` returned 403 (same as #1613); PR will state that governance issue create is blocked.
