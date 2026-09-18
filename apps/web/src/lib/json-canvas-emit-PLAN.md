# TASK: pack→JSON Canvas emit

## 1. Goal & Scope
* **Objective:** Optionally emit a JSON Canvas 1.0 `.canvas` file (`mission.canvas`) from the Video Pack emit slice (transcript + visual events + SOP/requirements) so App Builder / Mission Workspace can open the pack spatially.
* **Context:** Hayden YES via CoS, queued after B2 CLOSED PARTIAL (`#1903` / `7dfdd3efe`). B2 left keyframe `image_path` null — this cut must not invent frames or file-node image paths. Packs still invent `architecture` / `code_snippets`; those stay stripped.
* **Chosen approach (H1):** New `emit-json-canvas.ts` implements the [groupthinking/jsoncanvas spec 1.0](https://github.com/groupthinking/jsoncanvas/blob/main/spec/1.0.md) (nodes/edges only). Wire `mission.canvas` into the existing App Builder sandbox file map and Studio Export merge. No new route, no G.A.T.E., no frame-capture.
* **Rejected:**
  * **H2:** Inline canvas JSON inside `emit-app-builder-sandbox.ts` — mixes HTML sandbox with the open canvas contract.
  * **H3:** New `/api/video/canvas` route — out of scope; user said wire existing sandbox / Studio export only.
* **Scope:**
  * `apps/web/src/lib/emit-json-canvas.ts` — emit + validate against spec 1.0
  * `apps/web/src/lib/emit-app-builder-sandbox.ts` — add `mission.canvas` when content exists
  * `apps/web/src/lib/__tests__/emit-json-canvas.test.ts` — contract + fixture proofs
  * Existing sandbox / Studio tests stay green (file map gains one optional key)
 * *Initial check:* No existing canvas emit. Reuse `AppBuilderSandboxInput`, `visualEventsFromPack`, `sopStepsFromPack`, Qj + XYMc fixtures. Do not touch the extractor or invent `image_path`.

## 2. Execution Plan
- [x] Read jsoncanvas spec 1.0 + sample.canvas; map sandbox / Studio export path
- [x] Lock failing canvas tests (RED: missing `@/lib/emit-json-canvas`)
- [x] Implement emit + validator; wire `mission.canvas`
- [x] Verify focused vitest (no live G.A.T.E. / dpl_ / frame-capture)

## 3. Definition of Done (Success Verification)
* **Expected Outcome:** Ready packs `QjZ5ohr7sGA` and/or `XYMcBrFSJ4c` produce a non-empty valid `mission.canvas` from transcript / visual / SOP only. Empty packs omit the file. Architecture, code_snippets, and invented keyframe file paths never appear.
* **Verification Method:**
  * `cd apps/web && npx vitest run src/lib/__tests__/emit-json-canvas.test.ts src/lib/__tests__/emit-app-builder-sandbox.test.ts src/app/api/video/sandbox`
* **Proof Artifact:** `cd apps/web && npx vitest run src/lib/__tests__/emit-json-canvas.test.ts src/lib/__tests__/emit-app-builder-sandbox.test.ts src/app/api/video/sandbox` — 3 files, **28 passed**. Related `action-surface` 16 passed. New emit files typecheck clean.

## 4. Post-Task Reflection
* **What was done:** Added JSON Canvas 1.0 emit (`mission.canvas`) from transcript + visual events + SOP, wired into the App Builder sandbox file map and Studio Export merge. Empty packs omit the file. File nodes / invented `image_path` are not emitted.
* **Why it was needed:** Mission Workspace / App Builder portability after B2 closed PARTIAL — spatial canvas without inventing architecture or frames.
* **How it was tested:** Validator accepts official `sample.canvas`. QjZ5ohr7sGA and XYMcBrFSJ4c fixtures emit non-empty valid canvases. Architecture / code_snippets / `dpl_` stay out. Null keyframe `image_path` never becomes a file node.
