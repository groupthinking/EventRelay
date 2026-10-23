# TASK: Rewire leftover Studio playflow onto Ship this

## 1. Goal & Scope
* **Objective:** Keep #2437 **Ship this** and re-render the leftover B/E/G helpers the IDE still left unused: honest Events empty copy + pack workbench when `events[]` is empty.
* **Context:** A/#1692 and B–G helpers landed in September. #2437 restored Ship this, transcript retry, stack-check skip/unknown, and review_action cards. Live pack GET for pBsT6v-ciO8 has transcript + architecture + artifacts + stack.tools and **no `events` field**. UI must label that as **Events**, never INSIGHTs. No G.A.T.E. No fake events. No ClipToAction.
* **Scope:**
  * `apps/web/src/components/OneLoopStudio.tsx` — pass `studioEventsEmptyMessage` + `PackWorkbench` when `studioPromotePackWorkbench`
  * `apps/web/src/components/studio/StudioIdeOutput.tsx` — Events empty honesty + pack workbench; keep Ship this / reviewActions / stackCheckViews from #2437
  * `apps/web/src/lib/__tests__/studio-pipeline-status.test.ts` — lock Events≠INSIGHTs + workbench wiring
 * *Initial check:* Do not restore `studio-deploy-button`, origin deploy kickoff, fake events, or G.A.T.E. contract changes.

## 2. Execution Plan
- [x] Rebase onto origin/main after #2437 (clears DIRTY + stale required closer)
- [x] Events tab uses `studioEventsEmptyMessage` + pack workbench
- [x] Keep Ship this, transcript retry, skip/unknown stack checks, review_action cards
- [x] Focused Vitest green

## 3. Definition of Done (Success Verification)
* **Expected Outcome:** Anonymous Studio can click **Ship this**. Events tab says this pack has no extracted events (not INSIGHTs) and can show the pack workbench. Stack checks stay skip/unknown and do not hold ship. Transcript retry and review cards remain visible.
* **Verification Method:** `cd apps/web && npx vitest run src/lib/__tests__/studio-pipeline-status.test.ts src/lib/__tests__/official-templates.test.ts src/lib/__tests__/uvai-surface-unification.test.ts src/components/__tests__/OneLoopStudio.three-panel.test.tsx src/components/studio/__tests__/StudioIdeOutput.playflow.test.tsx`
* **Proof Artifact:** `cd apps/web && npx vitest run src/lib/__tests__/studio-pipeline-status.test.ts src/lib/__tests__/official-templates.test.ts src/lib/__tests__/uvai-surface-unification.test.ts src/components/__tests__/OneLoopStudio.three-panel.test.tsx src/components/studio/__tests__/StudioIdeOutput.playflow.test.tsx` → **5 files, 51 passed**.

## 4. Post-Task Reflection
* **What was done:** Rebased #2436 onto #2437. Wired honest Events empty copy and PackWorkbench into the IDE without dropping Ship this.
* **Why it was needed:** The required closer check was a stale FAILURE on the old SHA, and main had moved (CONFLICTING/DIRTY).
* **How it was tested:** Focused Vitest after rebase. Required closer then failed because #2435 closed when #2437 merged; remaining E/G lives on open #2440 (Act CTA + pricing copy).
