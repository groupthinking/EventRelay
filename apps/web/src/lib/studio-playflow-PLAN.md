# TASK: Restore Studio IDE playflow CTAs (B/E/F/G)

## 1. Goal & Scope
* **Objective:** Restore user-visible playflow after the three-pane IDE rebuild: Retry transcript, honest empty Events (never Insights), skip/unknown stack checks, review_action cards + Act CTA.
* **Context:** Closes #2435. Dogfood `pBsT6v-ciO8`: pack 200, no `events`, no `insights`, architecture + artifacts + SeaDance/Cluely tools. Helpers already exist on main; IDE does not render them. C (player) and D (export toast) stay.
* **Scope:**
  * `apps/web/src/components/OneLoopStudio.tsx` — Retry transcript, Act on this run, pass empty-events + stack + action cards into output
  * `apps/web/src/components/studio/StudioIdeOutput.tsx` — Events empty copy, pack workbench, stack skip/unknown, review_action cards, transcript retry
  * Focused Vitest for the dogfood path
 * *Initial check:* Extend existing helpers (`studioCanRetryTranscript`, `studioEventsEmptyMessage`, `studioActionCard`, `stackCheckStatusLabel`). No Origin G.A.T.E., ClipToAction, fake events, Ship checkout.

## 2. Execution Plan
- [x] Failing tests: retry button, empty Events ≠ Insights, SeaDance Unknown, review_action card, Act CTA
- [x] Wire Retry transcript in toolbar + transcript tab
- [x] Honest Events empty + pack workbench; Tools skip/unknown; Intent review cards
- [x] Soften remaining “run tools” / durable overclaim copy
- [x] Verify focused Vitest

## 3. Definition of Done (Success Verification)
* **Expected Outcome:** On `/studio?video=…pBsT6v-ciO8` Events says no extracted events (not Insights), architecture/artifacts visible, SeaDance/Cluely Unknown, failed transcript has Retry, Act cards say Review this result.
* **Verification Method:** `npm --workspace=apps/web exec vitest run src/components/__tests__/OneLoopStudio.playflow.test.tsx src/components/__tests__/StudioIdeOutput.playflow.test.tsx src/components/__tests__/OneLoopStudio.three-panel.test.tsx src/components/__tests__/OneLoopStudio.build-live.test.tsx src/components/__tests__/OneLoopStudio.job-strip.test.tsx src/lib/__tests__/studio-pipeline-status.test.ts src/lib/__tests__/official-templates.test.ts src/lib/__tests__/uvai-surface-unification.test.ts`
* **Proof Artifact:** 8 files, 58 passed.

## 4. Post-Task Reflection
* **What was done:** Re-wired B/E/F/G helpers into the IDE: Retry transcript in toolbar + Transcript tab, honest Events empty copy + pack workbench, skip/unknown stack checks, review_action cards, Act on this run when `agentWorkflowUi` is on. Softened paste-ready copy from “run tools” to “act, export, or save”.
* **Why it was needed:** The IDE rebuild left those CTAs computed but unrendered, so AXIOM’s dogfood pack still looked stuck (empty Events, no retry, SeaDance looking like a hold).
* **How it was tested:** RED playflow component tests, then GREEN (`58 passed` across 8 files, including job-strip / three-panel / build-live regressions).
