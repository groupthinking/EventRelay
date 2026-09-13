# TASK: Assembly engine (JIT kit → cohesive build)

## 1. Goal & Scope
* **Objective:** For one banked video (`QjZ5ohr7sGA`), turn Video Pack / App Builder **ingredients** into an actual install/build/typecheck run and a reproducible assembly receipt. Not emit-only. Not G.A.T.E. theater.
* **Context:** CoS 2026-09-13 SOLE cut. `/api/video/sandbox` already emits a pack viewer (transcript / visual / SOP + mission.canvas + startup.sh / 8080). That emit is necessary input; a generated directory alone does not PASS. Live-URL / G.A.T.E. stays PARKED. Do not invent architecture/code_snippets. Do not revive FORGE / Workbench / VIZUL / ClipToAction as products.
* **Scope:**
  * `emit-app-builder-sandbox.ts` — pin deps; source-grounded SOP checklist; honest viewer labels
  * `assemble-app-builder.ts` — identity manifest + receipt + optional real gates
  * `assemble-app-builder-route.ts` + `/api/video/assemble` (+ v1) — wraps existing sandbox lookup
  * `scripts/assemble-app-builder.mjs` — local assemble from sandbox JSON
  * Tests: determinism, two-source distinction, honest labels, real `npm run build` + `npm run typecheck`
 * *Initial check:* Reuse `emitAppBuilderSandbox` / `handleAppBuilderSandboxGet|Post`. Do **not** open a parallel builder or `video-pack-extractor.ts`.

## 2. Execution Plan
- [x] Inventory emit/sandbox/handoff (sandbox emit is the valid path)
- [x] Extend emit: pinned deps, SOP checklist, honesty copy
- [x] Assembly lib: file hashes, pinned deps, unresolved requirements, gates
- [x] HTTP assemble wraps sandbox (gates labeled **untested** — no npm on Vercel)
- [x] Local/CI assemble runs install + build + typecheck and writes receipt
- [x] Draft PR; do not merge

## 3. Definition of Done (Success Verification)
* **Expected Outcome:** Qj ingredients assemble to a workspace whose receipt lists `videoId`, `sourceHash`, `filesDigest`, pinned deps, honest unresolved requirements, and **pass** for install/build/typecheck when the local assemble step runs. HTTP assemble never fake-greens those gates. XYMc identity stays distinct. Architecture/code snippets stay stripped.
* **Verification Method:**
  * `cd apps/web && npx vitest run src/lib/__tests__/assemble-app-builder.test.ts src/lib/__tests__/assemble-app-builder.gates.test.ts src/app/api/video/assemble/__tests__/route.test.ts src/lib/__tests__/emit-app-builder-sandbox.test.ts src/app/api/video/sandbox/__tests__/route.test.ts src/lib/__tests__/auth-paths.test.ts`
  * `node apps/web/scripts/assemble-app-builder.mjs --from-sandbox <sandbox.json> --out /tmp/uvai-assemble-qj` then `npm run build` / `npm run typecheck` already recorded on the receipt
* **Proof Artifact:** Focused Vitest 7 files / 67 passed (`assemble-app-builder`, gates, assemble route, emit, sandbox route, auth-paths, emit-json-canvas). Local `node apps/web/scripts/assemble-app-builder.mjs --from-sandbox /tmp/qj-sandbox.json --out /tmp/uvai-assemble-qj` → install/build/typecheck **pass**, `browser_smoke` **untested**, `videoId=QjZ5ohr7sGA`, `sourceHash=0c351eae941cc151f9581ef22d9a0c7a585b75fe5e4aef890813a143c7a5fd8a`, `filesDigest=a34b3d87688036be323f72229ca4fc90d9a3270616df25558a1c541a2742f2bf`. Draft PR https://github.com/groupthinking/EventRelay/pull/1933 — do not merge.

## 4. Post-Task Reflection
* **What was done:** Extended App Builder emit into an assembly path: pinned deps, SOP checklist, planned HTTP receipt, and a local/CI assemble that actually runs npm install/build/typecheck.
* **Why it was needed:** Sandbox emit alone is not a build. CoS required a reproducible receipt with honest untested/unsupported labels and no G.A.T.E. theater.
* **How it was tested:** 67 focused unit tests including a real Qj materialize+gates run; mjs assemble script on fixture sandbox JSON; XYMc vs Qj identity kept distinct.
