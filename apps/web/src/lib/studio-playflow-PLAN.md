# TASK: Restore Studio Ship this playflow after IDE shell

## 1. Goal & Scope
* **Objective:** Get UVAI Studio playflow back toward ≥9/10 by restoring a discoverable **Ship this** path and rewiring leftover B/E/G helpers the IDE shell left unused.
* **Context:** Kill A (#1692) merged. B–G helpers exist (`studioTranscriptStage`, `studioActionCard`, `deployHoldReason` skip/unknown, export toast, player overlay). The 2026-10-07 IDE refactor deleted `studio-deploy-button` and stopped rendering Ship this, stack-check honesty, review_action cards, and transcript retry. Dogfood kill F still stands: no Ship this; seadance/cluely-class checks must not hold anonymous ship.
* **Scope:**
  * `apps/web/src/lib/studio-pipeline-status.ts` — `studioShipEnabled` / `studioShipCta` (exportability gates ship; holdReason never does)
  * `apps/web/src/lib/official-templates.ts` — stack-check row view (skip/unknown)
  * `apps/web/src/components/OneLoopStudio.tsx` — Ship this CTA, transcript retry, toast position, pass checks/actions
  * `apps/web/src/components/studio/StudioIdeOutput.tsx` — stack checks + `studioActionCard`
 * *Initial check:* Extend existing helpers. Do not restore `studio-deploy-button`, origin deploy kickoff, fake events, or G.A.T.E. contract changes.

## 2. Execution Plan
- [x] Failing tests for Ship this enablement, skip/unknown checks, review cards, retry, toast position
- [x] Ship this CTA enabled by `studioCanExport`, never by non-runnable stack checks
- [x] Tools tab shows honest skip/unknown; Intent tab renders `review_action` cards
- [x] Transcript retry control when `studioCanRetryTranscript`
- [x] Export toast no longer uses sticky-footer `bottom-20`
- [x] Focused Vitest

## 3. Definition of Done (Success Verification)
* **Expected Outcome:** Anonymous Studio on a seadance/cluely pack can click **Ship this** (ZIP export). Stack checks read skip/unknown and do not disable the button. No live hostname claim. Transcript retry and review cards are visible.
* **Verification Method:** `cd apps/web && npx vitest run src/lib/__tests__/studio-pipeline-status.test.ts src/lib/__tests__/official-templates.test.ts src/lib/__tests__/uvai-surface-unification.test.ts src/components/__tests__/OneLoopStudio.three-panel.test.tsx src/components/studio/__tests__/StudioIdeOutput.playflow.test.tsx`
* **Proof Artifact:** `cd apps/web && npm test -- src/lib/__tests__/studio-pipeline-status.test.ts src/lib/__tests__/official-templates.test.ts src/lib/__tests__/uvai-surface-unification.test.ts src/components/__tests__/OneLoopStudio.three-panel.test.tsx src/components/studio/__tests__/StudioIdeOutput.playflow.test.tsx` → **5 files, 49 passed**. Related: OneLoopStudio.build-live + job-strip + linked-sop → **3 files, 16 passed**. `tsc --noEmit` and eslint on touched files passed.

## 4. Post-Task Reflection
* **What was done:** Restored a discoverable **Ship this** toolbar CTA that downloads the pack ZIP. Anonymous/unknown SeaDance/Cluely stack checks render as skip/unknown and never disable the button. Intent tab renders `review_action` cards. Transcript retry is visible on retryable failure. Export toast sits at `bottom-4` (no sticky footer). Origin deploy button was not restored.
* **Why it was needed:** IDE shell left playflow helpers unwired; dogfood kill F was a disabled Deploy with no Ship this.
* **How it was tested:** Focused Vitest (49 + 16), type-check, eslint. No production live claim. GitHub issue create was 403 so this cut has no new issue number.
