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
- [ ] Extend emit: pinned deps, SOP checklist, honesty copy
- [ ] Assembly lib: file hashes, pinned deps, unresolved requirements, gates
- [ ] HTTP assemble wraps sandbox (gates labeled **untested** — no npm on Vercel)
- [ ] Local/CI assemble runs install + build + typecheck and writes receipt
- [ ] Draft PR; do not merge

## 3. Definition of Done (Success Verification)
* **Expected Outcome:** Qj ingredients assemble to a workspace whose receipt lists `videoId`, `sourceHash`, `filesDigest`, pinned deps, honest unresolved requirements, and **pass** for install/build/typecheck when the local assemble step runs. HTTP assemble never fake-greens those gates. XYMc identity stays distinct. Architecture/code snippets stay stripped.
* **Verification Method:**
  * `cd apps/web && npx vitest run src/lib/__tests__/assemble-app-builder.test.ts src/lib/__tests__/assemble-app-builder.gates.test.ts src/app/api/video/assemble/__tests__/route.test.ts src/lib/__tests__/emit-app-builder-sandbox.test.ts src/app/api/video/sandbox/__tests__/route.test.ts src/lib/__tests__/auth-paths.test.ts`
  * `node apps/web/scripts/assemble-app-builder.mjs --from-sandbox <sandbox.json> --out /tmp/uvai-assemble-qj` then `npm run build` / `npm run typecheck` already recorded on the receipt
* **Proof Artifact:** [filled after gates run]

## 4. Post-Task Reflection
* **What was done:**
* **Why it was needed:**
* **How it was tested:**
