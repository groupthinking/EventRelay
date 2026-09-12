# TASK: ingest→App Builder sandbox emit (cos-20260912-002)

## 1. Goal & Scope
* **Objective:** From EventRelay paste-URL ingest, emit a trail-velvet App Builder Workspace sandbox whose **only** payload is transcript + visual events + SOP steps. PASS is pack `QjZ5ohr7sGA` (`vp:v0:QjZ5ohr7sGA`) running under `startup.sh` / `0.0.0.0:8080` with visible browser UI and `npm run build` + `npm run typecheck`.
* **Context:** Lock override cos-20260912-002 replaces prior emit design. Packs invent `architecture` / `code_snippets` (SimpleKnotState / TireChangeContext / `tire_procedure.ts`). Those must not be fed to App Builder. PARTIAL packs and Origin/`dpl_` are not proof. Live-URL / G.A.T.E. cascade stays PARKED. `video-pack-extractor.ts` is owned by a parallel agent (B1) — do not touch it.
* **Scope:**
  * `apps/web/src/lib/emit-app-builder-sandbox.ts` — file map from allowed emit slice only
  * `apps/web/src/lib/app-builder-sandbox-route.ts` + `/api/video/sandbox` (+ v1) — materialize stored pack
  * `apps/web/src/lib/action-surface.ts` — Studio export merges sandbox, drops ARCHITECTURE.md / artifacts.json
  * `apps/web/src/lib/emit-video-pack.ts` — citation carries transcript / visual / requirements for emit
  * Fixture: `apps/web/src/lib/__fixtures__/qj-z5ohr7sga-emit.ts` (live pack 200, 2026-09-12)
 * *Initial check:* Extend ingest + export. Do **not** open `studio.deploy`. Do not push trail-velvet. Do not invent live URLs.

## 2. Execution Plan
- [x] Fail-closed tests for startup.sh / 8080 / smoke / build+typecheck / strip architecture
- [x] Emit function + API materialize from stored pack (QjZ5ohr7sGA)
- [x] Wire Studio export + public auth path without naming pack frames in OneLoopStudio
- [x] Materialize QjZ5ohr7sGA files; `npm install && npm run build && npm run typecheck`; `startup.sh` + smoke
- [x] PR off EventRelay main; do not merge

## 3. Definition of Done (Success Verification)
* **Expected Outcome:** Ready pack `QjZ5ohr7sGA` materializes a workspace whose UI shows the tire-change transcript, visual events, and SOP requirements. No architecture, no code snippets, no `dpl_`, no G.A.T.E. HOLD receipt.
* **Verification Method:**
  * `cd apps/web && npx vitest run src/lib/__tests__/emit-app-builder-sandbox.test.ts src/lib/__tests__/action-surface.test.ts src/lib/__tests__/auth-paths.test.ts src/lib/__tests__/emit-video-pack.test.ts src/lib/__tests__/studio-pipeline-status.test.ts src/store/__tests__/dashboard-store.test.ts src/app/api/video/sandbox`
  * Write emitted files to a temp dir; `npm install && npm run build && npm run typecheck`
  * `sh startup.sh` then `node scripts/browser-smoke.mjs` — visible UI includes `QjZ5ohr7sGA`
* **Proof Artifact:**
  * Live pack GET `https://uvai.io/api/video/pack?url=https://www.youtube.com/watch?v=QjZ5ohr7sGA` → HTTP 200, `status=success`, `id=vp:v0:QjZ5ohr7sGA`, hash `0c351eae941cc151f9581ef22d9a0c7a585b75fe5e4aef890813a143c7a5fd8a`. Not PARTIAL. Pack still contains invented `architecture` / `code_snippets` (`tire_procedure.ts`, `TireChangeContext`); emit stripped them.
  * Focused vitest: 7 files, **105 passed** (`emit-app-builder-sandbox`, sandbox route, auth-paths, emit-video-pack, studio-pipeline-status, dashboard-store, action-surface).
  * Materialize from that live JSON → `/tmp/qj-app-builder-sandbox`. `npm run build` (vite 6.4.3, 5 modules) and `npm run typecheck` (`tsc --noEmit`) exit 0.
  * `npm run dev` on `0.0.0.0:8080`. `node scripts/browser-smoke.mjs` → `{"ok":true,"url":"http://127.0.0.1:8080/","status":200,"visible":true,"videoId":"QjZ5ohr7sGA"}`.
  * Playwright: title `UVAI▶ Video Pack · QjZ5ohr7sGA`; visible transcript (“five flat tires”), visual events (scissor jack / star pattern), SOP (Safety and Vehicle Staging … 50 mph / 100 miles). No `TireChangeContext`, no `dpl_`. Screenshot: `/opt/cursor/artifacts/screenshots/qj-z5ohr7sga-app-builder-sandbox.png`.

## 4. Loop envelope
* First cut: `ingest→App Builder sandbox emit`
* Earlier emit fed invented architecture into the sandbox (escalated to Loop). Current cut strips it.
* Not using PARTIAL packs or Origin/`dpl_` as proof.
* G.A.T.E. live-URL cascade: PARKED

## 5. Post-Task Reflection
* **What was done:** EventRelay now materializes a trail-velvet App Builder sandbox from a ready Video Pack. Payload is transcript + visual events + SOP only. Studio Export merges those files and drops architecture dumps. `/api/video/sandbox` reads the pack store and does not start extract.
* **Why it was needed:** Lock override cos-20260912-002. Prior emit fed invented architecture (SimpleKnotState-class types). PASS is a running `QjZ5ohr7sGA` preview, not prose, not a `dpl_`, not a G.A.T.E. HOLD.
* **How it was tested:** 105 focused unit tests; live pack 200 re-fetched; files written from that JSON; build + typecheck; 8080 + browser-smoke + Playwright snapshot/screenshot.
