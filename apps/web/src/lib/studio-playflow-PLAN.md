# TASK: Restore remaining Studio IDE playflow after Ship this

## 1. Goal & Scope
* **Objective:** Keep #2437’s **Ship this** ZIP CTA, and restore the leftover dogfood rails this branch still owns: honest empty Events (never Insights), pack workbench, Act on this run, transcript-tab retry, and softened “run tools” copy.
* **Context:** #2437 (`560f07120`) already closed #2435 with Ship this + skip/unknown stack rows + review cards + toolbar retry. This branch layers Events honesty and the flag-gated Act CTA on that landing. C (player) and D (export toast at `bottom-4`) stay. No Origin G.A.T.E., ClipToAction, fake events, or Ship checkout.
* **Scope:**
  * `apps/web/src/components/OneLoopStudio.tsx` — Act on this run, honest empty-events + pack workbench into output; keep Ship this
  * `apps/web/src/components/studio/StudioIdeOutput.tsx` — Events empty copy, pack workbench, transcript-tab retry on main’s stackChecks/reviewActions API
  * Focused Vitest for the dogfood path
 * *Initial check:* Do not restore `studio-deploy-button`. Do not replace Ship this with a second Export button.

## 2. Execution Plan
- [x] Merge origin/main (#2437 Ship this) and keep complementary Events/Act wiring
- [x] Honest Events empty + pack workbench; Tools skip/unknown; Intent review cards
- [x] Soften remaining “run tools” paste-ready copy
- [x] Verify focused Vitest after the merge

## 3. Definition of Done (Success Verification)
* **Expected Outcome:** On `/studio?video=…pBsT6v-ciO8` Events says no extracted events (not Insights), architecture/artifacts visible, SeaDance/Cluely Unknown, **Ship this** enabled, failed transcript has Retry, Act cards say Review this result.
* **Verification Method:** `npm --workspace=apps/web exec vitest run src/components/__tests__/OneLoopStudio.playflow.test.tsx src/components/__tests__/StudioIdeOutput.playflow.test.tsx src/components/studio/__tests__/StudioIdeOutput.playflow.test.tsx src/components/__tests__/OneLoopStudio.three-panel.test.tsx src/components/__tests__/OneLoopStudio.build-live.test.tsx src/components/__tests__/OneLoopStudio.job-strip.test.tsx src/lib/__tests__/studio-pipeline-status.test.ts src/lib/__tests__/official-templates.test.ts src/lib/__tests__/uvai-surface-unification.test.ts`
* **Proof Artifact:** 9 files, 62 passed after merging `origin/main` (#2437).

## 4. Post-Task Reflection
* **What was done:** Merged #2437’s Ship this landing and kept the remaining playflow: Events honesty, pack workbench, Act on this run (`agentWorkflowUi`), transcript-tab retry, and “act, export, or save” paste copy.
* **Why it was needed:** #2437 restored Ship this / stack rows / review cards; empty `events[]` packs still needed an honest Events pane and the flag-gated Act CTA.
* **How it was tested:** Focused Vitest after merge: 9 files, 62 passed.
