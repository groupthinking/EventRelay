# TASK: Studio G.A.T.E. receipt chip after Attempt deploy

## 1. Goal & Scope
* **Objective:** After anonymous Attempt deploy, Studio shows a visible G.A.T.E. decision (PASS | HOLD | REJECT | ESCALATE), a short reason, and a citable `eventrelay.gate-receipt.v1` id/hash — including when BACKEND_URL is missing.
* **Context:** Residual after #1713. Prod claimed a soft PASS with no receipt UI; anon Attempt deploy only showed `BACKEND_URL is not configured`.
* **Scope:**
  * `apps/web/src/lib/gate-transition.ts` — view + attempt id + cite backend_reason
  * `apps/web/src/lib/__tests__/gate-transition.test.ts`
  * `apps/web/src/components/OneLoopStudio.tsx` — evaluate on start-fail/catch; render chip
  * `docs/gate-transition-contract.md` — Studio must surface the receipt
 * *Initial Check:* Reuse `evaluateStudioDeployTransition`. Do not persist receipts in Upstash. Do not revive “Deploy completed”.

## 2. Execution Plan
- [x] Step 1: Failing tests for HOLD+BACKEND_URL view and Studio chip testids
- [x] Step 2: `studioGateReceiptView` + attempt transition id
- [x] Step 3: OneLoopStudio evaluates G.A.T.E. on backend-fail and catch paths
- [x] Step 4: Render decision chip in Studio header
- [x] Step 5: Verify vitest; open ready PR to main

## 3. Definition of Done (Success Verification)
* **Expected Outcome:** Anon Attempt deploy always shows a G.A.T.E. chip. Missing BACKEND_URL → HOLD + backend reason + receipt hash. No “Deploy completed” overclaim.
* **Verification Method:** `cd apps/web && npx vitest run src/lib/__tests__/gate-transition.test.ts src/lib/__tests__/studio-pipeline-status.test.ts`
* **Proof Artifact:** focused **2 files / 33 passed**; full frontend `npx vitest run` → **89 files, 596 passed, 1 skipped**. PR: https://github.com/groupthinking/EventRelay/pull/1717

## 4. Post-Task Reflection
* **What was done:** Visible G.A.T.E. chip on Attempt deploy; HOLD cites BACKEND_URL; receipt id/hash from `eventrelay.gate-receipt.v1`.
* **Why it was needed:** #1713 evaluated only after a successful runId; prod showed backend text with no gate UI.
* **How it was tested:** `cd apps/web && npx vitest run` (596 passed, 1 skipped).
