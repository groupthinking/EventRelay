# TASK: G.A.T.E. transition contract (PR1)

## 1. Goal & Scope
* **Objective:** Add a typed Governed Acceptance & Transition Engine contract that returns exactly one of PASS | HOLD | REJECT | ESCALATE, emits a versioned EventRelay receipt, and gates Studio deploy success claims.
* **Context:** Authorized next cut is Origin G.A.T.E. only. Zero-Sim asks if evidence is real; G.A.T.E. asks whether verified evidence + authority permit the transition. This is not a second product DB and does not build artifacts.
* **Scope:**
  * `apps/web/src/lib/gate-transition.ts` (new)
  * `apps/web/src/lib/__tests__/gate-transition.test.ts` (new)
  * `apps/web/src/components/OneLoopStudio.tsx` (one deploy claim site)
  * `docs/gate-transition-contract.md` + short `AGENTS.md` section
 * *Initial Check:* No existing G.A.T.E. module. Reuse `#1707`/`#1710` `studioVerifiedLiveUrl` as the locked live-receipt bar. Do not rebuild Mission Workspace.

## 2. Execution Plan
- [x] Step 1: Write failing unit tests for PASS / HOLD / REJECT / ESCALATE + receipt hash
- [x] Step 2: Implement contract + Zero-Sim assessor (no invented evidence)
- [x] Step 3: Wire OneLoopStudio deploy to evaluate G.A.T.E. before claiming a live receipt
- [x] Step 4: Document the four decisions and Zero-Sim vs G.A.T.E. split
- [ ] Step 5: Verify focused vitest + source-guard; open ready PR to main

## 3. Definition of Done (Success Verification)
* **Expected Outcome:** Studio deploy cannot claim live success unless G.A.T.E. returns PASS with a verified https live URL. Missing evidence HOLDs; unreal/malformed live claims REJECT; unknown authority ESCALATES. Receipts are versioned and SHA-256 hashable.
* **Verification Method:** `cd apps/web && npx vitest run src/lib/__tests__/gate-transition.test.ts src/lib/__tests__/studio-pipeline-status.test.ts`
* **Proof Artifact:** Test command output on this branch.

## 4. Post-Task Reflection
* **What was done:** Typed `evaluateTransition` / `evaluateStudioDeployTransition` contract with EventRelay receipts; Studio deploy claims live success only after G.A.T.E. PASS.
* **Why it was needed:** Authorized Origin G.A.T.E. cut. Copy-only #1707 honesty is not a transition contract.
* **How it was tested:** `cd apps/web && npx vitest run src/lib/__tests__/gate-transition.test.ts src/lib/__tests__/studio-pipeline-status.test.ts`
