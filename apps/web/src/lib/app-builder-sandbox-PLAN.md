# TASK: second-video→App Builder smoke (XYMcBrFSJ4c)

## 1. Goal & Scope
* **Objective:** Lock App Builder sandbox emit for live pack `XYMcBrFSJ4c` (`vp:v0:XYMcBrFSJ4c`, source_hash `b7d0ea083b1f8a6146fd6db818896ed09abfaa3f92babf976f5c209e07d3b959`). Payload is transcript + visual events + SOP only. PASS is fixture + tests, materialize from live pack/sandbox JSON, `npm run build` + `npm run typecheck`, and `0.0.0.0:8080` smoke on this VM.
* **Context:** CoS re-GO after B1 close. First-video emit (`QjZ5ohr7sGA`, cos-20260912-002 / #1898) stays. Do not regress that pack. Do not touch B1 extractor unless a real gap blocks emit. No B2 keyframes. No live-URL / G.A.T.E. Loop owns the shared-box AXIOM URL.
* **Scope:**
  * `apps/web/src/lib/__fixtures__/xymcbrfsj4c-emit.ts` — live pack slice (transcript / visual / SOP + forbidden architecture held only for strip proofs)
  * `apps/web/src/lib/__tests__/emit-app-builder-sandbox.test.ts` — XYMc emit + Studio export; existing Qj cases stay
  * `apps/web/src/app/api/video/sandbox/__tests__/route.test.ts` — XYMc materialize from stored pack
 * *Initial check:* Emit path already generic. Extend fixtures/tests. Do **not** open `video-pack-extractor.ts`. Do not invent live URLs.

## 2. Execution Plan
- [x] Fetch live pack + sandbox JSON for XYMcBrFSJ4c (HTTP 200)
- [x] Fixture from that live JSON (not QjZ5ohr7sGA)
- [x] Fail-closed tests: identity hash, transcript/visual/SOP, strip architecture/code_snippets, no Qj leak
- [x] Materialize from live JSON; `npm install && npm run build && npm run typecheck`; `startup.sh` / 8080 smoke
- [x] Draft PR off EventRelay main; do not merge

## 3. Definition of Done (Success Verification)
* **Expected Outcome:** Ready pack `XYMcBrFSJ4c` materializes a workspace whose UI shows the boring-AI-automations transcript, visual events (Torty Gym / n8n / Make), and SOP requirements. No architecture, no code snippets, no `dpl_`, no Qj tire-change copy.
* **Verification Method:**
  * `cd apps/web && npx vitest run src/lib/__tests__/emit-app-builder-sandbox.test.ts src/app/api/video/sandbox/__tests__/route.test.ts`
  * Write emitted files from live pack/sandbox JSON to a temp dir; `npm install && npm run build && npm run typecheck`
  * `npm run dev` on `0.0.0.0:8080` then `node scripts/browser-smoke.mjs` — visible UI includes `XYMcBrFSJ4c`
* **Proof Artifact:**
  * Live pack GET `https://uvai.io/api/video/pack?url=https://www.youtube.com/watch?v=XYMcBrFSJ4c` → HTTP 200, `status=success`, `id=vp:v0:XYMcBrFSJ4c`, hash `b7d0ea083b1f8a6146fd6db818896ed09abfaa3f92babf976f5c209e07d3b959`. Not PARTIAL. Pack still contains invented `architecture` / `code_snippets` (`email_triage.ts`, `EmailClassification`); emit stripped them.
  * Live sandbox GET `https://uvai.io/api/video/sandbox?url=https://www.youtube.com/watch?v=XYMcBrFSJ4c` → HTTP 200, `videoId=XYMcBrFSJ4c`.
  * Focused vitest: 2 files, **19 passed** (`emit-app-builder-sandbox` including original Qj cases + sandbox route).
  * Materialize from that live sandbox JSON → `/tmp/xymc-app-builder-sandbox`. `npm run build` (vite 6.4.3, 5 modules) and `npm run typecheck` (`tsc --noEmit`) exit 0.
  * `npm run dev` on `0.0.0.0:8080`. `node scripts/browser-smoke.mjs` → `{"ok":true,"url":"http://127.0.0.1:8080/","status":200,"visible":true,"videoId":"XYMcBrFSJ4c"}`. Also HTTP 200 on `http://0.0.0.0:8080/` and `http://172.30.0.2:8080/`.
  * Playwright: title `UVAI▶ Video Pack · XYMcBrFSJ4c`; visible transcript (“unpaid invoices” / “nine boring AI automations”), visual events (Torty Gym / n8n / Make), SOP (Email Triage Workflow … 24/7 AI Inbound Receptionist). No `EmailClassification`, no `QjZ5ohr7sGA`. Screenshot: `/opt/cursor/artifacts/screenshots/xymcbrfsj4c-app-builder-sandbox.png`.
  * Draft PR: https://github.com/groupthinking/EventRelay/pull/1901 — do not merge.

## 4. Loop envelope
* Cut: `second-video→App Builder smoke`
* Locked video: `XYMcBrFSJ4c` (NOT `QjZ5ohr7sGA`)
* B1 extractor: do not touch unless emit is blocked
* B2 keyframes: out of scope (existing emit may still surface pack keyframes already stored on the live pack)
* G.A.T.E. live-URL cascade: PARKED

## 5. Post-Task Reflection
* **What was done:** Added a live `XYMcBrFSJ4c` fixture and fail-closed tests so App Builder emit stays transcript + visual + SOP. Existing `QjZ5ohr7sGA` cases still pass. No extractor or G.A.T.E. change. Materialized the live sandbox JSON on this VM and smoked 8080.
* **Why it was needed:** CoS re-GO after B1 close. First-video emit was already generic; the second video needed a locked fixture so it cannot silently alias Qj or leak invented architecture.
* **How it was tested:** 19 focused unit tests; live pack + sandbox 200 re-fetched; files written from that JSON; build + typecheck; 8080 + browser-smoke + Playwright snapshot/screenshot.
