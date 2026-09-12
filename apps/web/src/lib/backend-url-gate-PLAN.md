# TASK: Wait for a verified studio.deploy receipt (residual after #1853)

## 1. Goal & Scope
* **Objective:** Attempt deploy must not HOLD solely for `Deploy still running. No verified deploy receipt — UNKNOWN checks are not a live URL.` Wait for a verified https live URL + EventRelay receipt, or an honest different HOLD.
* **Context:** AXIOM on `dpl_8wx8iEfUcwNpWQNHwvpMsyLh9xsW` / XYMcBrFSJ4c (receipt `er:gate:v1:wrun_01M2ABB1NJ5TFZ153CTRNTPNW9`) cleared the three prior residuals. New HOLD is the UNKNOWN-checks string. No Deploy completed / no live URL.
* **Root cause:** `tryVideoToSoftwareDeploy` aborted at 50s (real deploy path still in flight) and fell through to `/videos/process`. Client `pollStudioDeploy(..., { attempts: 20 })` stopped while WDK `runStatus` was still `running`. `studioDeployOutcomeMessage` then HOLDs with UNKNOWN checks. WDK `pollJobStep` later died after 4 retries on `job_96f498640b still transcribing`.
* **Scope:** `pipeline-async-job.ts` (do not abandon vts on timeout), `studio-workflow.ts` poller, `OneLoopStudio` attempt count, `studio-pipeline-status.ts` HOLD copy, WDK `pollJobStep` wait. Do not invent a live URL, do not weaken G.A.T.E., do not reopen #1848.
 * *Initial check:* Modify existing poll/kickoff; do not add a second deploy path.

## 2. Execution Plan
- [x] Step 1: Lock failing tests (poll through running, no UNKNOWN-checks HOLD, vts timeout not process-fallback)
- [x] Step 2: Retry vts on timeout; wait for terminal/receipt; honest in-flight HOLD
- [x] Step 3: Focused Vitest 66 passed
- [ ] Step 4: New PR from main → merge-when-core-green → prod READY `dpl_`

## 3. Definition of Done
* **Expected Outcome:** HOLD is not UNKNOWN-checks, not the three cleared residuals. PASS only with a verified https hostname URL.
* **Verification Method:** Focused Vitest + Vercel prod READY after merge.
* **Proof Artifact:** (filled after verification)

## 4. Post-Task Reflection
* **What was done:**
* **Why it was needed:**
* **How it was tested:**

---

# Prior cut: Read studio.deploy workflow run (residual after #1850)

## 1. Goal & Scope
* **Objective:** Attempt deploy must not HOLD solely for `Failed to read workflow run`. GET must read the WDK run. PASS only with a verified https live URL + EventRelay receipt; otherwise honest HOLD/REJECT with a different real reason.
* **Context:** #1850 removed `Failed to read workflow return value`. AXIOM re-dogfood XYMcBrFSJ4c on `dpl_3o6VDNVej7vkA82TQKDNWhkxLGYs` HOLDs with `Failed to read workflow run` (receipt `er:gate:v1:wrun_01M2A9Z9SYXD59NG211W9N8EQA`).
* **Root cause:** `withWorldVercelFetch` rebinds `globalThis.fetch` to undici `fetch(url, init)`. `getRun()` calls `fetch(Request)`. undici treats the Request as a URL string → `Failed to parse URL from [object Request]` / `ERR_INVALID_URL`. Outer GET catch swallows that as `Failed to read workflow run`.
* **Scope:** `world-vercel-fetch.ts`, GET `[runId]/route.ts`, `studio-workflow.ts` poller. Do not invent a live URL, do not weaken G.A.T.E., do not reopen #1848 env pin.
 * *Initial check:* Modify the existing undici wrapper; do not add a second fetch path.

## 2. Execution Plan
- [x] Step 1: Lock failing tests (Request fetch, GET unread-run, poller retry, claim guard)
- [x] Step 2: Compat-wrap undici fetch so Request inputs use native fetch; never emit the generic unread-run string
- [x] Step 3: Focused Vitest 88 passed
- [ ] Step 4: New PR from main → merge-when-core-green → prod READY `dpl_`

## 3. Definition of Done
* **Expected Outcome:** GET can read the workflow run. HOLD is not `Failed to read workflow run` or `Failed to read workflow return value`. PASS only with a verified https hostname URL.
* **Verification Method:** Focused Vitest + Vercel prod READY after merge.
* **Proof Artifact:** 88 passed (`world-vercel-fetch`, GET `[runId]`, `studio-workflow`, `gate-transition`, `pipeline-async-job`, `studio-pipeline-status`, `pipeline-backend-health`, POST studio-deploy, isolation)

## 4. Post-Task Reflection
* **What was done:** Compat-wrapped `withWorldVercelFetch` so `fetch(Request)` stays on Next/Node fetch; GET no longer emits `Failed to read workflow run`; poller retries unread-run 500s. Claim guard unchanged.
* **Why it was needed:** #1850 wrapped GET in undici fetch. `getRun()` passes a Request; undici parses it as `[object Request]` → 500 generic HOLD.
* **How it was tested:** TDD RED then GREEN. Focused Vitest 88/88. Prod logs on `dpl_3o6VDNVej7vkA82TQKDNWhkxLGYs` showed `Failed to parse URL from [object Request]` for `wrun_01M2A9Z9SYXD59NG211W9N8EQA`.

---

# Prior cut: Parse studio.deploy workflow return / live URL (residual after #1848)

## 1. Goal & Scope
* **Objective:** Attempt deploy must not HOLD solely for `Failed to read workflow return value`. PASS only with a verified https live URL + EventRelay receipt; otherwise honest HOLD/REJECT/ESCALATE with the real reason.
* **Context:** #1848 pinned `BACKEND_URL` to `https://api.uvai.io`. AXIOM re-dogfood XYMcBrFSJ4c then HOLDs with unread workflow return (receipt `er:gate:v1:wrun_01M2A8RXT1HS8NPW70HV6AA0YV`). Not an API-key cut.
* **Root cause:** Backend jobs finish as `JobStatus.complete` (`"complete"`). Studio only treated `"completed"` as terminal, so the WDK poll step retried until the run failed. GET `/api/workflows/studio-deploy/:runId` then swallowed `returnValue` (a `WorkflowRunFailedError` whose cause was the real job message) as `Failed to read workflow return value`. Nested `live_url` / `job.error` were also dropped. `/videos/process` is transcript-only; a real live URL can only come from `/video-to-software`.
* **Scope:** `pipeline-async-job.ts`, `studio-workflow.ts`, `studio-deploy.ts` (F5 poll), `workflows/studio-deploy.ts`, GET `[runId]/route.ts`.
 * *Initial check:* Modify existing parsers; do not invent a live URL or weaken G.A.T.E.

## 2. Execution Plan
- [x] Step 1: Lock failing tests (`complete` terminal, nested live_url, job.error, vts pass-through, unread-return poll, failed-run cause)
- [x] Step 2: Parse backend `complete`; surface returnValue cause; wrap GET in `withWorldVercelFetch`; try video-to-software then fall through
- [x] Step 3: Focused Vitest 85/85
- [ ] Step 4: Prod Attempt deploy no longer HOLDs solely for unread return value

## 3. Definition of Done (Success Verification)
* **Expected Outcome:** HOLD reason is a real backend/workflow message or missing-live-URL — not the generic unread-return string. PASS only with a verified https hostname URL.
* **Verification Method:** `cd apps/web && npx vitest run` on the focused files below.
* **Proof Artifact:** 85 passed (pipeline-async-job, studio-workflow, studio-deploy, gate-transition, studio-pipeline-status, pipeline-backend-health, test-env-isolation, studio-deploy POST + GET [runId])

## 4. Post-Task Reflection
* **What was done:** Treated backend `complete` as terminal; surfaced WDK `returnValue` cause; wrapped GET in `withWorldVercelFetch`; passed through nested `live_url` / `job.error`; tried `/video-to-software` for a real live URL and fell through on 401.
* **Why it was needed:** After #1848, AXIOM HOLDs with a generic unread-return string because the poller never accepted `complete` and GET swallowed the failed-run cause.
* **How it was tested:** Focused Vitest 85/85. Live `GET /api/v1/health` = 200. Process/vts without key remain 401 (not this cut). Prod Attempt deploy still needs a post-merge READY `dpl_`.

---

# Prior cut: Wire BACKEND_URL so studio.deploy can emit a verified live URL receipt

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
- [x] Step 4: Verify Vitest; PR #1848; merge + prod READY `dpl_…` pending CI

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
