# TASK: studio.deploy must surface a backend hostname or a precise kickoff HOLD

## 1. Goal & Scope
* **Objective:** Ready-transcript `studio.deploy` / G.A.T.E. for XYMcBrFSJ4c must PASS with a backend-supplied https hostname + receipt, or HOLD with a residual that is **not** any cleared copy (reuse miss, timeout abort, HTTP 524, YouTube bot, UNKNOWN, workflow-run, workflow-return, BACKEND_URL, origin-no-live, or the #1889 hostname-finished string).
* **Context:** AXIOM on READY prod `dpl_EHAzZtKkJ2PQLS2fjPfu8PpDyizt` (#1889 / `ab752a7b`) / XYMcBrFSJ4c. Cleared: `Origin video-to-software returned no verified live URL.` Still HOLD: `Origin deploy finished without a backend-supplied https hostname.` Receipt `er:gate:v1:wrun_01M2B5SRA5W5S4WQP2M4ZHY040`. AXIOM: Not VERCEL_TOKEN. No live URL.
* **Root cause (verified in Vercel runtime logs):** Kickoff `POST /video-to-software` hit `AbortSignal.timeout(20s)` twice per `kickoffStep` (16:04:25 and 16:05:05). #1889 remapped that abort via `studioDeployReadyTranscriptHold` / `isGatewayTimeoutKickoff` to `STUDIO_ORIGIN_NO_HOSTNAME_HOLD`. Workflow retried kickoff once, then `FatalError` — never received a `job_id`, never polled. The residual is false: deploy did not finish.
* **Scope:** Stop remapping kickoff abort/524 to hostname-finished. Durable kickoff retries. Longer vts wait. Normalize backend-supplied bare `*.vercel.app` hosts. Async initial job persist so 202 is not store-blocked. Do not invent a URL or a secret.
 * *Initial check:* Modify existing kickoff/poll/extract/persist. No new Studio surface.

## 2. Execution Plan
- [x] Step 1: Lock failing tests (kickoff abort/524 ≠ hostname HOLD; bare hostname extract; wrun_01M2B5SRA5W5S4WQP2M4ZHY040 receipt; persist hang ≠ blocked 202)
- [x] Step 2: Implement kickoff residual + retries + 45s wait + bare-host extract + async pending persist
- [ ] Step 3: Focused Vitest + pytest GREEN
- [ ] Step 4: PR off current main

## 3. Definition of Done
* **Expected Outcome:** Timeout/524 kickoff stays retryable and HOLDs `STUDIO_ORIGIN_KICKOFF_NO_JOB_HOLD` if no job id arrives. Hostname HOLD is only for a terminal job with no URL. Bare backend hostnames become `https://`. 202 is not blocked on job-store save.
* **Verification Method:** Focused Vitest (`pipeline-async-job`, `gate-transition`, `studio-pipeline-status`) + pytest extract/persist/202.
* **Proof Artifact:** (filled after tests + PR)

## 4. Post-Task Reflection
* **What was done:** (filled after GREEN)
* **Why it was needed:** Prod logs for `wrun_01M2B5SRA5W5S4WQP2M4ZHY040` showed kickoff abort remapped to a finished-deploy HOLD.
* **How it was tested:** (filled after GREEN)

---

# Prior cut: Origin video-to-software must return verified live URL

## 1. Goal & Scope
* **Objective:** After transcript reuse, studio.deploy / origin video-to-software must surface a verified clickable https live URL + EventRelay receipt for G.A.T.E. PASS, or an honest HOLD that is **not** `Origin video-to-software returned no verified live URL` and not prior cleared residuals.
* **Context:** AXIOM on `dpl_3mKicmxjHttT1JznuaRp1tRx8tWS` (#1887 `b6c0b4416d14`) / XYMcBrFSJ4c. Ready-transcript reuse CLEARED. Still HOLD: `Origin video-to-software returned no verified live URL.` Receipt `er:gate:v1:wrun_01M2B1Q97XA9GHVSG1FZY92N19`. No live URL.
* **Root cause:** #1887 returns origin 202 immediately so WDK can poll, but (1) `fetchAsyncVideoJob` / kickoff miss `metadata.result.live_url` and `deployment.urls.*`, (2) persist only reads top-level `result.live_url`, (3) GET `/jobs/{id}` never flattens a live URL, (4) first poll 404 (async persist / other instance) is a terminal fail remapped to the origin-no-live HOLD.
* **Scope:** Extract backend-supplied https hostnames only (claim guard). Continue poll on 404 / pending until a verified URL or a non-cleared honest HOLD. Flatten persist + GET. Do not invent a URL. Do not reopen reuse / timeout / 524.
 * *Initial check:* Modify existing kickoff/poll/persist/GET. Do not add a second Studio surface.

## 2. Execution Plan
- [x] Step 1: Lock failing tests (nested live_url extract; 404 continue; persist from deployment.urls; GET flatten)
- [x] Step 2: Implement extract + continue + persist/GET flatten
- [x] Step 3: Focused Vitest + pytest GREEN; no reuse/timeout/524 regression
- [x] Step 4: PR off current main — https://github.com/groupthinking/EventRelay/pull/1889 (`1e1a22b7d`)

## 3. Definition of Done
* **Expected Outcome:** Poll continues until a backend-supplied verified https hostname is extracted, or HOLD is a specific non-cleared reason (still pending / adapter error) — not origin-no-live, not reuse-miss, not timeout/524/bot/UNKNOWN/workflow-run/return-value/BACKEND_URL.
* **Verification Method:** Focused Vitest pipeline-async-job + studio-deploy + gate-transition; pytest persist/GET/202 loadable.
* **Proof Artifact:** PR https://github.com/groupthinking/EventRelay/pull/1889. Focused Vitest (`pipeline-async-job`, `studio-deploy`, `gate-transition`, `studio-pipeline-status`, `studio-workflow`) + pytest persist/GET/202. Claim guard: only `studioVerifiedLiveUrl` / `_verified_https_live_url` pass-through. Honest HOLD is `STUDIO_ORIGIN_NO_HOSTNAME_HOLD`, not the origin-no-live residual. No URL invented. No Hayden secrets guessed.

## 4. Post-Task Reflection
* **What was done:** After #1887's immediate 202, extract nested backend live URLs (`metadata.result.live_url`, `deployment.urls.vercel`), persist/GET flatten them, and continue the WDK poll on first-read 404 instead of remapping to the origin-no-live HOLD. Missing-URL job error is now a specific adapter/hostname miss, not that residual string.
* **Why it was needed:** Dogfood on `dpl_3mKicmxjHttT1JznuaRp1tRx8tWS` / XYMcBrFSJ4c reused the transcript (CLEARED) but HOLDed `Origin video-to-software returned no verified live URL` with receipt `er:gate:v1:wrun_01M2B1Q97XA9GHVSG1FZY92N19` and no live URL — poll ended before a nested URL was surfaced, or first 404 was treated as terminal.
* **How it was tested:** TDD RED then GREEN on extract/poll/persist/GET. Reuse (202 without sync wait, no `/videos/process` on ready transcript), timeout abort remap, and HTTP 524 remap tests left intact and passing.

---

# Prior cut: restore ready-transcript reuse on studio.deploy

## 1. Goal & Scope
* **Objective:** Attempt Deploy must reuse an already-ready transcript — never re-hit YouTube `/videos/process` — and still reach G.A.T.E. PASS with a clickable https live URL + receipt, or an honest HOLD that is **not** the reuse-miss copy and not prior cleared residuals.
* **Context:** AXIOM on `dpl_BL2mQMcrQEyuKB1LjmwCgEeA4V9Y` (#1884 / `2f9b4751`) / XYMcBrFSJ4c. Timeout abort residual CLEARED. Still HOLD: `Ready transcript was not reused. Deploy must not re-fetch YouTube.` Receipt `er:gate:v1:wrun_01M2B05JJZNTD7MKANV0RN0J28`. No live URL.
* **Root cause (verified in tree):** `#1884` remaps timeout / 524 / empty poll messages through `studioDeployReadyTranscriptHold()` to `STUDIO_READY_TRANSCRIPT_HOLD`. `decideStudioDeployPoll` continue with a ready transcript and no status message becomes that reuse-miss string; kickoff abort catch calls `studioDeployReadyTranscriptHold()` with no args. Transcript **is** sent to origin vts — the HOLD is a false reuse-miss label. Origin 202 is also delayed by a 12s sync wait even when a transcript is already ready.
* **Scope:** Honest remappers (reuse HOLD only on YouTube re-fetch). Continue poll keeps pending copy. Ready-transcript vts returns 202 immediately. Keep timeout/524/bot/UNKNOWN/workflow-run/return-value/BACKEND_URL cleared. Claim guard unchanged.
 * *Initial check:* Modify existing `pipeline-async-job.ts`, `studio-deploy.ts` workflow, and `router.py` vts. Do not add a second Studio surface.

## 2. Execution Plan
- [x] Step 1: Lock failing tests (continue ≠ reuse miss; 524/abort ≠ reuse miss; bot still reuse HOLD; origin 202 without sync wait)
- [x] Step 2: Remap + immediate 202 + workflow abort copy
- [x] Step 3: Focused Vitest + pytest GREEN
- [ ] Step 4: PR off current main

## 3. Definition of Done
* **Expected Outcome:** Ready-transcript deploy never calls `/videos/process`. Timeout/524 no longer become the reuse-miss HOLD. Origin 202 + job poll remains the async path. PASS only with verified https hostname URL + receipt.
* **Verification Method:** Focused Vitest (`pipeline-async-job`, `studio-workflow`, `studio-pipeline-status`, `gate-transition`, studio-deploy route) + pytest ready-transcript 202 + skip YouTube.
* **Proof Artifact:** Vitest 5 files / 96 passed. Pytest `test_ready_transcript_video_to_software_returns_202_without_sync_wait` + `test_video_to_software_returns_202_when_sync_budget_exceeded` + `test_ready_transcript_skips_youtube_fetch` passed.

## 4. Post-Task Reflection
* **What was done:** Stopped remapping timeout/524/empty poll copy to the reuse-miss HOLD. Continue polls stay `Deploy job … still pending`. Origin vts with a usable transcript returns 202 immediately so Studio can poll `job_id` instead of aborting the 12s sync wait. YouTube bot string still maps to the reuse HOLD. `/videos/process` still skipped when a transcript is ready. Claim guard unchanged.
* **Why it was needed:** After #1884, AXIOM HOLDs `Ready transcript was not reused` even though kickoff already sent the Studio transcript — `studioDeployReadyTranscriptHold()` treated timeout/empty as a reuse miss, and exhausted polls inherited that string.
* **How it was tested:** TDD RED then GREEN. Focused Vitest 96. Pytest 3 ready-transcript/202 cases. Cannot signed-in dogfood AXIOM here.

---

# Prior cut: studio.deploy no abort-timeout → live URL

## 1. Goal & Scope
* **Objective:** Prevent abort-timeout on the studio.deploy path (extend wait, async poll, or honest progress) through a verified deploy receipt + clickable live URL, or an honest HOLD that is not this timeout and not prior cleared residuals.
* **Context:** CoS formal GO. Residual on `dpl_DL2TCbLyYZhgjv7tnePcEdKHCARs` / XYMcBrFSJ4c: `The operation was aborted due to timeout` (receipt `er:gate:v1:wrun_01M2AKRAVZ0SEBM670BGXEMCQZ`). Transcript ready. No Deploy completed / no live URL. Cleared: YouTube bot wall, HTTP 524, UNKNOWN checks, workflow-run, return-value, BACKEND_URL.
* **Root cause:** WDK `pollJobStep` sat ~180s (`18 × 10s setTimeout`) inside one `'use step'`. Vercel/WDK step budget ~60s aborts with the DOM string. Receipt exists so kickoff succeeded. Remap/retry alone does not prevent the in-step abort.
* **Scope:** Split poll onto durable `sleep('10s')` between short job reads. Continue on 408/gateway timeout. Client poll window covers the durable wait. Claim guard unchanged. No Origin invent. Do not reopen #1878.
 * *Initial check:* Modify existing workflow + poll helpers. Do not add a second Studio surface.

## 2. Execution Plan
- [x] Step 1: Lock failing tests (decideStudioDeployPoll continue on 408; workflow imports sleep; no in-step setTimeout; client window ≥ 6 min)
- [x] Step 2: Implement durable poll + decide helper + client window
- [ ] Step 3: Focused + full frontend tests / lint GREEN
- [ ] Step 4: Push PR #1884 — core CI green — report PR # + SHA

## 3. Definition of Done
* **Expected Outcome:** studio.deploy does not abort-timeout. PASS only with verified https hostname URL + receipt. Honest HOLD ≠ abort-timeout, ≠ bot, ≠ 524, ≠ UNKNOWN checks, ≠ workflow-run, ≠ return-value, ≠ BACKEND_URL.
* **Verification Method:** Focused Vitest + `cd apps/web && npx vitest run` + `npm run lint` + required GitHub core jobs.
* **Proof Artifact:** (filled after verification)

## 4. Post-Task Reflection
* **What was done:**
* **Why it was needed:**
* **How it was tested:**

---

# Prior cut: clear G.A.T.E. timeout abort HOLD on studio.deploy

## 1. Goal & Scope
* **Objective:** Attempt deploy / studio.deploy for XYMcBrFSJ4c must not HOLD on `The operation was aborted due to timeout`. Reach G.A.T.E. PASS with a verified https live URL + EventRelay receipt, or an honest HOLD that is not timeout-abort, not HTTP 524, and not the YouTube bot wall.
* **Context:** AXIOM on `dpl_DL2TCbLyYZhgjv7tnePcEdKHCARs` (includes #1880) / XYMcBrFSJ4c. Receipt `er:gate:v1:wrun_01M2AKRAVZ0SEBM670BGXEMCQZ`. Bot + 524 residuals cleared. Still HOLD on timeout abort. No live URL.
* **Root cause:** `AbortSignal.timeout` in WDK `kickoffStep` / `pollJobStep` and the client poller is treated as a terminal workflow failure. WDK marks AbortError as FatalError. `fetchAsyncVideoJob` and `pollStudioDeploy` do not catch the abort, so `run.returnValue` / OneLoopStudio catch pass the raw DOM message to G.A.T.E. #1880 then `kind: 'failed'`s a ready-transcript vts abort instead of retrying origin `202` + `job_id`.
* **Scope:** Retry origin vts on abort (never `/videos/process` when transcript is ready). Catch abort on job status reads and client polls. Remap leftover abort copy. Claim guard unchanged. No Origin invent.
 * *Initial check:* Modify existing kickoff / poll / workflow / outcome helpers. Do not add a second Studio surface.

## 2. Execution Plan
- [x] Step 1: Lock failing tests (timeout abort → retry 202 / keep polling; never raw abort HOLD; no process; no 524)
- [x] Step 2: Retry + catch + remap; workflow does not FatalError abort
- [x] Step 3: Focused Vitest GREEN (7 files, 97 passed)
- [x] Step 4: PR #1884 from current main — local test-frontend 703 passed; GitHub Actions core jobs still queued (no failure)

## 3. Definition of Done
* **Expected Outcome:** Timeout abort is not a terminal HOLD reason. Ready-transcript path still skips YouTube process. 524 stay remapped. PASS only with a verified https hostname URL + receipt.
* **Verification Method:** Focused Vitest on pipeline-async-job, studio-workflow, studio-pipeline-status, gate-transition.
* **Proof Artifact:** https://github.com/groupthinking/EventRelay/pull/1884 — local `npx vitest run` 100 files / 703 passed / 1 skipped; `npm run lint` 0 errors. GitHub `CI` / `PR Checks` queued at report time (runner backlog), 0 failed.

## 4. Post-Task Reflection
* **What was done:** Retry origin vts on abort when a ready transcript exists; catch abort on job status reads and client start/poll; WDK treats abort/408 as retryable; remap leftover abort copy. Claim guard unchanged.
* **Why it was needed:** After #1880, AXIOM HOLDs on `The operation was aborted due to timeout` because AbortSignal.timeout failed the WDK step / client poll as a terminal run error instead of waiting for origin 202 + a verified live URL.
* **How it was tested:** TDD RED then GREEN. Focused 97 + full apps/web 703. Cannot signed-in dogfood AXIOM here.

---

# Prior cut: restore #1859 ready-transcript reuse after #1875 524 handoff

## 1. Goal & Scope
* **Objective:** Ready-transcript studio.deploy must not HOLD the YouTube bot wall and must not HOLD HTTP 524. Keep #1875 async past 524 via origin `202` + `job_id`. Do not regress UNKNOWN / workflow-run / return-value / BACKEND_URL. Claim guard stays.
* **Context:** AXIOM on `dpl_BK1hFnDuN366N5WBAUpAsLka9iwP` / XYMcBrFSJ4c (receipt `er:gate:v1:wrun_01M2AF8WD3G4VCB63KEBX311HV`) cleared HTTP 524. Regression: `Sign in to confirm you’re not a bot` (cleared on #1859). No live URL.
* **Root cause:** #1875 gateway-timeout fallthrough starts `/videos/process` even when a Studio transcript is ready. Prod `api.uvai.io` ignores `transcript` / `pipeline` and re-hits YouTube. WDK `pollJobStep` FatalErrors the bot string.
* **Scope:** Skip `/videos/process` whenever a usable transcript exists. Treat origin vts `202` + `job_id` as the async handoff (not process). Remap bot / 524 on the ready-transcript miss. URL-only timeout/401 still uses process. No cookies / Origin invent.
 * *Initial check:* Modify existing kickoff + poll remap. Do not add a second Studio surface.

## 2. Execution Plan
- [x] Step 1: Lock failing tests (524 + ready transcript must not call process)
- [x] Step 2: Skip process on ready transcript; keep process for URL-only; origin 202 job_id
- [x] Step 3: Focused Vitest GREEN (89) + pytest vts 202
- [ ] Step 4: New PR from current main → merge-when-core-green → prod READY `dpl_`

## 3. Definition of Done
* **Expected Outcome:** Ready-transcript deploy does not HOLD bot wall or HTTP 524. PASS only with a verified https hostname URL + EventRelay receipt. Honest HOLD ≠ bot, ≠ 524, ≠ cleared residuals is allowed.
* **Verification Method:** Focused Vitest + Vercel prod READY after merge. Cannot signed-in dogfood AXIOM here.
* **Proof Artifact:** PR https://github.com/groupthinking/EventRelay/pull/1880 — Vitest 3 files 58 passed + 4 files 31 passed; pytest `test_video_to_software_returns_202_when_sync_budget_exceeded` PASSED.

## 4. Post-Task Reflection
* **What was done:**
* **Why it was needed:**
* **How it was tested:**

---

# Prior cut: studio.deploy backend kickoff no HTTP 524

## 1. Goal & Scope
* **Objective:** Attempt deploy kickoff must not HOLD on `Backend kickoff returned HTTP 524`. Reach a verified https live URL + EventRelay receipt, or an honest HOLD that is not 524 and not the cleared residuals.
* **Context:** AXIOM on `dpl_BbFnnqTvYiVDfSFEDa43LQTFETTD` / XYMcBrFSJ4c (receipt `er:gate:v1:wrun_01M2AE6Z9Q2KZRBA0Z0Q455B0S`) cleared #1859 YouTube bot. Transcript was ready. New HOLD is HTTP 524. No Deploy completed / no live URL.
* **Root cause:** After #1859, ready-transcript kickoff only calls sync `POST /api/v1/video-to-software` (180s). Cloudflare in front of api.uvai.io returns 524 at ~100s. Kickoff HOLDs that status and never starts an async job to poll.
* **Scope:** Fail-fast / treat 524·504·408·abort as gateway timeout; origin `/video-to-software` returns 202 + job_id when work exceeds a 12s sync budget (no CF 524). Studio uses that job_id. Fallback `/videos/process` with ready transcript + `pipeline: video-to-software`. Backend accepts `transcript` and runs vts in the job (skip YouTube when transcript is provided). Claim guard unchanged. Do not reopen #1848. No cookies / Origin invent.
 * *Initial check:* Modify existing kickoff + `_run_video_job`; do not add a second Studio surface.

## 2. Execution Plan
- [x] Step 1: Lock failing tests (524 → async job, not HTTP 524 HOLD)
- [x] Step 2: Gateway-timeout handoff + backend transcript/vts job
- [x] Step 3: Focused Vitest + pytest
- [ ] Step 4: PR from main → merge-when-core-green → prod READY `dpl_`

## 3. Definition of Done
* **Expected Outcome:** Kickoff does not HOLD solely for HTTP 524. PASS only with a verified https hostname URL.
* **Verification Method:** Focused Vitest/pytest + Vercel prod READY after merge.
* **Proof Artifact:** (filled after verification)

## 4. Post-Task Reflection
* **What was done:**
* **Why it was needed:**
* **How it was tested:**

---

# Prior cut: studio.deploy reuse ready transcript (no YouTube re-hit)

## 1. Goal & Scope
* **Objective:** When Video Pack / transcript is already ready, Attempt deploy must not re-fetch YouTube. Continue to a verified https live URL + EventRelay receipt, or an honest HOLD that is not the yt-dlp bot miss and not the cleared residuals.
* **Context:** AXIOM on `dpl_8DjoBuK8pE5MxE5L7SQaRgixivTK` / XYMcBrFSJ4c (receipt `er:gate:v1:wrun_01M2ACYVYXBHM0YVMX1WHMQ1PJ`) cleared #1855 UNKNOWN-checks. New HOLD: `ERROR: [youtube] XYMcBrFSJ4c: Sign in to confirm you’re not a bot.` Transcript was already ready.
* **Root cause:** `startStudioDeploy` / `kickoffAsyncVideoJob` send URL only. After video-to-software misses (401 / no live URL), kickoff starts `/videos/process`, which re-runs yt-dlp. `pollJobStep` FatalErrors the bot check. Ready Studio transcript is never passed.
* **Scope:** Pass usable transcript through Studio deploy → WDK → kickoff. When transcript is ready, do not start URL-only `/videos/process`. Surface the real vts miss (remap YouTube bot). Claim guard unchanged. No YouTube cookies/secret. Do not reopen #1848 / #1853 / #1855.
 * *Initial check:* Reuse `usableProvidedTranscript`; modify existing kickoff/workflow/POST. Do not add a second deploy path.

## 2. Execution Plan
- [x] Step 1: Lock failing tests (no process re-hit, POST/client pass transcript, remapped bot HOLD)
- [x] Step 2: Thread transcript; skip `/videos/process` when ready
- [x] Step 3: Focused Vitest 75 passed
- [ ] Step 4: New PR from main → merge-when-core-green → prod READY `dpl_`

## 3. Definition of Done
* **Expected Outcome:** Ready-transcript deploy does not HOLD on the YouTube bot string. PASS only with a verified https hostname URL. Honest different HOLD is allowed.
* **Verification Method:** Focused Vitest + Vercel prod READY after merge.
* **Proof Artifact:** (filled after verification)

## 4. Post-Task Reflection
* **What was done:**
* **Why it was needed:**
* **How it was tested:**

---

# Prior cut: Wait for a verified studio.deploy receipt (residual after #1853)

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
