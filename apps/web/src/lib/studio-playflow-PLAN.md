# TASK: Studio playflow for empty events[] packs

## 1. Goal & Scope
* **Objective:** Remove Studio dead ends when a live pack has transcript + architecture + artifacts + stack.tools but `events[]` is empty (`pBsT6v-ciO8` and similar).
* **Context:** Hayden flagged `https://uvai.io/studio?video=https://www.youtube.com/watch?v=pBsT6v-ciO8`. Pack 200: transcript ~1767 chars, architecture + artifacts[2] + stack.tools present, events count = 0. Do not invent fake events from keyframes/concepts.
* **Scope:**
  * `apps/web/src/lib/studio-handoff.ts` — reconstruct unencoded `?video=https://www.youtube.com/watch?v=ID`
  * `apps/web/src/lib/studio-pipeline-status.ts` — honest empty-events copy; promote pack workbench
  * `apps/web/src/lib/action-surface.ts` — export architecture/artifacts when events are empty
  * `apps/web/src/components/OneLoopStudio.tsx` — consume helpers; no fake events
 * *Initial check:* Extend existing helpers. No Origin G.A.T.E., ClipToAction, forge, or Ship checkout.

## 2. Execution Plan
- [x] Failing tests: unencoded query, empty-events copy, export without events, no keyframe→event mapping
- [x] Reconstruct `video` + sibling `v` for Home/share handoff
- [x] Honest Events empty state + promote architecture/artifacts/stack
- [x] Export pack files from formation when events[] is empty
- [x] Verify focused Vitest

## 3. Definition of Done (Success Verification)
* **Expected Outcome:** Studio for `pBsT6v-ciO8` loads the player from `?video=`, shows transcript, honest empty Events, prominent architecture/artifacts/stack, and Export is usable. No fake events.
* **Verification Method:** `cd apps/web && npx vitest run src/lib/__tests__/studio-handoff.test.ts src/lib/__tests__/studio-pipeline-status.test.ts src/lib/__tests__/action-surface.test.ts`
* **Proof Artifact:** `npx vitest run src/lib/__tests__/studio-handoff.test.ts src/lib/__tests__/studio-pipeline-status.test.ts src/lib/__tests__/action-surface.test.ts src/lib/__tests__/uvai-surface-unification.test.ts src/lib/__tests__/home-sell-surface.test.ts` → 5 files, 43 passed. Live GET `https://uvai.io/api/video/pack?url=https://www.youtube.com/watch?v=pBsT6v-ciO8` → 200; transcript 1767 chars; architecture present; artifacts 2; stack.tools 4; no `events` field; keyframes/concepts not mapped into Events.

## 4. Post-Task Reflection
* **What was done:** Honest empty Events copy after a completed run; promoted architecture/artifacts workbench when `events[]` is empty; Export writes ARCHITECTURE.md + artifacts.json; `?video=` handoff reads unencoded watch URLs and reconstructs split `video`+`v` params.
* **Why it was needed:** Packs like `pBsT6v-ciO8` have useful formation but zero events. Studio previously left a dead “Events show up after Run.” rail and could refuse export.
* **How it was tested:** RED then GREEN Vitest for handoff, empty-state copy, export without events, and OneLoopStudio source guards (no keyframe→event mapping). Live pack GET confirmed the empty-events shape.
