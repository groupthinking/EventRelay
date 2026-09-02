# TASK: Public identity Video Pack emit after #1609 401

## 1. Goal & Scope
* **Objective:** Anonymous paste-URL on uvai.io emits a hashed Video Pack v0 even when transcript fetch fails. `POST /api/video/pack` must return 200 without sign-in.
* **Context:** PR 1609 (`5ccbdf7`) added identity helpers and wired `processVideo` → `emitVideoPack`. Live uvai.io still 401s both pack URLs because `needsAuthentication('/api/video/pack')` is true. Home then shows "No transcript yet" / "source evidence could not be verified" with no `source_hash` or `cite:youtube`.
* **Scope:**
  * Allowlist `/api/video/pack` and `/api/v1/video/pack` in Next.js auth-paths (exact paths only; do not open `/api/video` or `/api/video/generate`).
  * Alias `POST /api/v1/video/pack` on the Next.js surface to the existing 1609 handler.
  * Allowlist FastAPI `/api/v1/video/pack` so a backend hit is not API-key gated.
  * Persist and show the identity citation on home paste+Run when speech evidence is missing.
  * Tests: 401-not-required, hash stability, emit-without-transcript.
* **Initial check:** Modify existing `auth-paths.ts`, `OneLoopStudio.tsx`, `dashboard-store` tests, and 1609 videopack helpers. Do not invent a second pack format.
* **Out of scope:** Qwen/Qwen3.8-27B, vLLM, Origin wasm, FORGE, slingshot, reach, ClipToAction.

## 2. Execution Plan
- [x] Lock failing tests (auth-paths public pack, FastAPI public pack, processVideo emit-without-transcript, citation label)
- [x] Allowlist exact pack paths; add Next.js `/api/v1/video/pack` alias
- [x] Show persisted pack citation on home even when transcript is missing
- [x] Verify tests; open PR against main (Closes #1611; #1610 already closed)

## 3. Definition of Done (Success Verification)
* **Expected Outcome:** Anonymous `POST /api/video/pack` with `{"url":"https://www.youtube.com/watch?v=jNQXAC9IVRw"}` returns 200 Video Pack v0 (`video_id`, `version`, `source_hash`). Same URL retry same hash; different video ID different hash. Home paste+Run shows/persists that citation if transcript is missing.
* **Verification Method:**
  * `cd apps/web && npx vitest run src/lib/__tests__/auth-paths.test.ts src/lib/__tests__/video-pack.test.ts src/lib/__tests__/studio-pipeline-status.test.ts src/app/api/video/pack src/app/api/v1/video/pack src/store/__tests__/dashboard-store.test.ts`
  * `PYTHONPATH=src pytest tests/unit/test_api_key_auth.py tests/unit/test_videopack_identity.py tests/unit/test_videopack_store.py -o addopts=`
* **Proof Artifact:** Frontend 71 passed (6 files). Python 23 passed. Live production still 401 until this branch deploys: `curl POST https://uvai.io/api/video/pack` → `{"error":"Authentication required"}`. Golden hashes unchanged: `auJzb1D-fag` → `2778c5fc08a1b7f19fe0a83bca959e24ecf20040c3cc1a3b6edd244d68c5e4ea`; `jNQXAC9IVRw` → `97150a5c21eef3d12a4543ce2108ca28fd6f829db1da120d7e75655ab471f97d`.

## 4. Post-Task Reflection
* **What was done:** Ungated exact `/api/video/pack` and `/api/v1/video/pack` from Next.js login wall and FastAPI API-key wall; aliased the v1 Next.js path to the 1609 identity handler; home paste now shows `cite:youtube:<id> · v0 · <source_hash>` even when the workflow has no transcript.
* **Why it was needed:** After #1609, anonymous paste called `emitVideoPack`, middleware 401'd, and the UI never persisted a pack citation.
* **How it was tested:** TDD red (auth-paths public=false, FastAPI 401, missing v1 route, missing citation helper) then green. Hash-stability and emit-without-transcript tests remain locked.
