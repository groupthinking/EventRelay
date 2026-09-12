# TASK: Wire BACKEND_URL so studio.deploy can emit a verified live URL receipt

## 1. Goal & Scope
* **Objective:** Studio Attempt deploy on uvai.io / v0-uvai must not HOLD solely because `BACKEND_URL is not configured`. G.A.T.E. can PASS when a real https live URL + EventRelay receipt exist; otherwise honest HOLD/REJECT with a different real reason.
* **Context:** AXIOM E2E on video XYMcBrFSJ4c held with receipt `er:gate:v1:wrun_01M28K5Y36REVE5RZ2FET21364` citing missing `BACKEND_URL`. Live `https://api.uvai.io/api/v1/health` returns HTTP 200. `.env.production` already documents `NEXT_PUBLIC_API_URL=https://api.uvai.io`, but `getBackendConfig()` only reads `BACKEND_URL`.
* **Scope:**
  * `apps/web/src/lib/pipeline-backend.ts` — resolve `BACKEND_URL` || `NEXT_PUBLIC_BACKEND_URL` || `NEXT_PUBLIC_API_URL`
  * `apps/web/src/lib/pipeline-backend-health.ts` — use that resolver
  * `apps/web/src/lib/action-tools.ts` — same resolver
  * `apps/web/src/app/api/jobs/[jobId]/route.ts` — request-time config
  * `apps/web/.env.production` — pin the verified Cloud Run hostname
  * Tests for fallbacks + hermetic NEXT_PUBLIC isolation
 * *Initial check:* Modify existing resolver; do not invent a live URL or weaken G.A.T.E.

## 2. Execution Plan
- [x] Step 1: Lock failing tests for env-name fallbacks and nested live_url pass-through
- [x] Step 2: Resolve the three documented env names; pin `.env.production`
- [x] Step 3: Preserve HOLD when no verified https hostname receipt
- [ ] Step 4: Verify Vitest; PR; merge; prod READY `dpl_…`

## 3. Definition of Done (Success Verification)
* **Expected Outcome:** Prod Studio Attempt deploy does not cite `BACKEND_URL is not configured` as the sole HOLD reason. PASS only with a verified https live URL + EventRelay receipt. Missing evidence still HOLDs; no “Deploy completed” overclaim.
* **Verification Method:**
  * `cd apps/web && npx vitest run src/lib/__tests__/pipeline-backend-health.test.ts src/lib/__tests__/action-tools.test.ts src/lib/__tests__/pipeline-async-job.test.ts src/lib/__tests__/gate-transition.test.ts src/__tests__/test-env-isolation.test.ts`
  * Live probe: `curl -sS -o /dev/null -w '%{http_code}' https://api.uvai.io/api/v1/health` → 200
* **Proof Artifact:** (filled after verification)

## 4. Post-Task Reflection
* **What was done:**
* **Why it was needed:**
* **How it was tested:**
