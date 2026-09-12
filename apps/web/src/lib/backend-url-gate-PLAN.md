# TASK: Parse studio.deploy workflow return / live URL (residual after #1848)

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
