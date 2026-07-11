# GATE-2 Live Product Baseline Report

**When:** 2026-07-10T17:55:51Z – 17:57:16Z UTC  
**Git (local main):** `e70aa66a` = `origin/main`  
**Test video:** `https://www.youtube.com/watch?v=jNQXAC9IVRw` (Me at the zoo — short public clip)  
**Evidence directory:** `docs/control-plane/sessions/gate2-20260710T1755Z/`

---

## Goal checklist

| ID | Task | Result | Evidence file |
|----|------|--------|---------------|
| G2-WEB-01 | Homepage load | **PASS** HTTP 200, 15438 bytes HTML, deploy `dpl_CHKfkAtwmwBwYraAvuAdXbYaRs3B` | `web-home.txt` |
| G2-API-01 | Backend health | **PASS** `/api/v1/health` 200 v2.0.0; root `/health` 200 | `api-v1-health.txt`, `api-root-health.txt` |
| G2-API-01b | Direct Cloud Run health | **PASS** same body as api.uvai.io | `backend-direct-health.txt` |
| G2-PIPE-01 | GET pipeline metadata | **PASS** 200, stages list | `pipeline-get.txt` |
| G2-BILL-01 | billing/status | **PASS** 200, plan=free, inactive | `billing-status.txt` |
| G2-PIPE-02 | POST pipeline (default async) | **PASS kickoff** 200 → job `job_638c836f7b` | `pipeline-post-async.json` |
| G2-PIPE-02p | Poll job to completion | **PASS** (after absolute URL) job_status=complete, transcript present | `job-final.json`, `job-final.summary.json` |
| G2-PIPE-02s | POST pipeline `async:false` | **DEGRADED** 200 partial `local-fallback`, Gemini TIMEOUT | `pipeline-post-sync.json` |
| G2-SEC-BASE | Security audit baseline noted | **PASS** pointer | `eventrelay-audit-report.md` (repo root, untracked) |

---

## Detailed results

### 1) GET surfaces — all healthy

| URL | HTTP | Notes |
|-----|------|-------|
| `https://uvai.io/` | 200 | Next.js production |
| `https://uvai.io/api/pipeline` | 200 | Metadata only (no video work) |
| `https://uvai.io/api/billing/status` | 200 | free / inactive / chatDailyLimit 5 |
| `https://api.uvai.io/api/v1/health` | 200 | gemini_key_present true, youtube_api_key_present true |
| `https://api.uvai.io/health` | 200 | service uvai-youtube-extension |
| `https://eventrelay-api-688578214833.us-central1.run.app/api/v1/health` | 200 | Matches api.uvai.io fingerprint |

### 2) POST `/api/pipeline` default (async=true)

**Request:**
```json
{"url":"https://www.youtube.com/watch?v=jNQXAC9IVRw"}
```

**Response HTTP 200:**
```json
{
  "id": "job_638c836f7b",
  "status": "pending",
  "pipeline": "backend-async",
  "async_processing": true,
  "job_id": "job_638c836f7b",
  "status_url": "/api/jobs/job_638c836f7b"
}
```

**Meaning:** Web BFF reached backend, created async job. This is the **intended** production path.

### 3) Poll job (critical)

| Attempt | Issue |
|---------|--------|
| First script polls | **Failed** — used relative `status_url` as curl URL → HTTP 000 (client error). **Probe bug, not product bug.** |
| Correct poll | `GET https://uvai.io/api/jobs/job_638c836f7b` → **HTTP 200** |

**Final job (summary):**

| Field | Value |
|-------|--------|
| outer `status` | `success` |
| `data.status` | `complete` |
| `progress` | 100.0 |
| `video_url` | Me at the zoo URL |
| `transcript` | present, 767 chars (JSON-wrapped transcript text about elephants) |
| `error` | null |

**Conclusion:** Async path **works end-to-end** for this short public video: kickoff → process → complete with transcript.

### 4) POST `/api/pipeline` with `async:false` (sync / fallback path)

**HTTP 200** but **not** full success:

| Field | Value |
|-------|--------|
| `status` | `partial` |
| `pipeline` | `local-fallback` |
| `degraded` | true |
| `backend.available` | true (host `eventrelay-api-gpwz4wb5na-uc.a.run.app`) |
| `gemini_error` | `TIMEOUT` — Gemini analysis timed out |
| `result.build_status` | `handoff_ready_backend_unavailable` |
| `result.live_url` | null |
| `deployment.status` | `blocked_by_configuration` |

**Conclusion:** Sync path does **not** complete full video-to-software. It returns an **honest handoff package** (review/build/deploy steps) after Gemini timeout. Messaging says backend unavailable even though health probe said available — **inconsistency to track** (see KNOWN-FAILURES).

---

## What “works” vs overstated (from live data only)

| Claim | Live verdict |
|-------|----------------|
| Site up | **Works** |
| API healthy | **Works** |
| Billing status endpoint | **Works** (free tier shape) |
| Async URL → job → transcript | **Works** for this video |
| Full sync “code gen + deploy live URL” | **Does not work** in this run (partial handoff) |
| Gemini always finishes in sync window | **Failed** TIMEOUT on sync path |
| GET pipeline = full product | **Overstated** — GET is metadata only |

---

## Operator notes

1. Always poll **`https://uvai.io` + status_url** (absolute), not the relative path alone.  
2. Prefer **default async** for real users; sync is degraded.  
3. Do not claim “pipeline complete” on HTTP 200 alone — check `status`, `pipeline`, `async_processing`, and job poll.

---

## GATE-2 exit status

**GATE-2 COMPLETE** with measured baseline.

Exit criteria met:

- [x] Session artifacts for GET/POST  
- [x] Known failure modes written (`inventory/KNOWN-FAILURES.md`)  
- [x] Async happy-path proven for golden video  
- [x] Sync degradation captured honestly  
