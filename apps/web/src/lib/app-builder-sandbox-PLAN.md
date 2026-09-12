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
- [ ] Materialize from live JSON; `npm install && npm run build && npm run typecheck`; `startup.sh` / 8080 smoke
- [ ] Draft PR off EventRelay main; do not merge

## 3. Definition of Done (Success Verification)
* **Expected Outcome:** Ready pack `XYMcBrFSJ4c` materializes a workspace whose UI shows the boring-AI-automations transcript, visual events (Torty Gym / n8n / Make), and SOP requirements. No architecture, no code snippets, no `dpl_`, no Qj tire-change copy.
* **Verification Method:**
  * `cd apps/web && npx vitest run src/lib/__tests__/emit-app-builder-sandbox.test.ts src/app/api/video/sandbox/__tests__/route.test.ts`
  * Write emitted files from live pack/sandbox JSON to a temp dir; `npm install && npm run build && npm run typecheck`
  * `sh startup.sh` then `node scripts/browser-smoke.mjs` — visible UI includes `XYMcBrFSJ4c`
* **Proof Artifact:**
  * Live pack GET `https://uvai.io/api/video/pack?url=https://www.youtube.com/watch?v=XYMcBrFSJ4c` → HTTP 200, `status=success`, `id=vp:v0:XYMcBrFSJ4c`, hash `b7d0ea083b1f8a6146fd6db818896ed09abfaa3f92babf976f5c209e07d3b959`.
  * Live sandbox GET `https://uvai.io/api/video/sandbox?url=https://www.youtube.com/watch?v=XYMcBrFSJ4c` → HTTP 200 before this cut (emit already generic). Fixture/tests lock that second video.

## 4. Loop envelope
* Cut: `second-video→App Builder smoke`
* Locked video: `XYMcBrFSJ4c` (NOT `QjZ5ohr7sGA`)
* B1 extractor: do not touch unless emit is blocked
* B2 keyframes: out of scope (existing emit may still surface pack keyframes already stored on the live pack)
* G.A.T.E. live-URL cascade: PARKED

## 5. Post-Task Reflection
* **What was done:**
* **Why it was needed:**
* **How it was tested:**
