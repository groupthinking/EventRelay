# LIVE STATUS — Verified facts only

**Last full probe:** 2026-07-10T17:54:00Z (UTC)  
**Probed by:** Grok lead agent  
**Method:** `curl`, `git`, `gcloud`, `env -u GITHUB_TOKEN gh`, `env -u VERCEL_TOKEN vercel`  
**Rule:** Anything not listed with a probe time is UNKNOWN, not “probably fine.”

---

## 1. Git — EventRelay

| Field | Value | Evidence |
|-------|--------|----------|
| Working tree | `/Users/garvey/Dev/EventRelay` | `git rev-parse --show-toplevel` |
| Branch | `main` | `git branch --show-current` |
| Remote | `origin` → `git@github.com:groupthinking/EventRelay.git` | `git remote -v` |
| vs `origin/main` | **`0 0` synced** | `git rev-list --left-right --count origin/main...HEAD` → `0 0` (2026-07-10) |
| Local HEAD | `e70aa66a` — `feat: Real AI provider integrations for unified_ai_sdk (#643)` | `git log -1` |
| origin/main | same `e70aa66a` | after Option A reset |
| Untracked (ops) | `CONTROL.md`, `docs/control-plane/`, `.audit-findings.json`, `eventrelay-audit-report.md`, `strategy/` | `git status -sb` |
| Local branches | **27** | see `inventory/BRANCHES.md` |
| Remote branches | **145** | `BRANCHES.md` |
| Stashes | 3 | `BRANCHES.md` |
| Worktrees | 4 | `BRANCHES.md` |

### 1.1 Sync action (Option A) — 2026-07-10

- Discarded local-only tip `d2c2587c` (“extract EventRelay API” — 3 files: `.gitignore`, `package-lock.json`, `tests/conftest.py`). **Not** an API extract.
- Command: `git reset --hard origin/main`
- Recover: `git show backup/pre-sync-d2c2587c` (annotated tag on discarded tip)

### 1.2 (historical) Commits that were on origin while local was behind

Now present on local main after sync:

```
e70aa66a feat: Real AI provider integrations for unified_ai_sdk (#643)
a78e4054 perf: resolve critical system bottlenecks and memory leaks (#642)
c5350ded refactor: rewrite Dockerfile with ffmpeg, nodejs v22 and multi-stage build (#639)
0149e7aa feat: integrate GTM skills from uvai-skills into agent orchestrator (#641)
f90a071e feat: migrate video-generate to AI SDK and durable Redis rate limiting (#638)
cb5e593b fix: resolve critical backend bugs and linting errors (#640)
```

### 1.3 Worktrees (paths may be stale; do not delete without check)

| Path | HEAD | Branch |
|------|------|--------|
| `/Users/garvey/Dev/EventRelay` | `d2c2587c` | `main` |
| `/private/tmp/er-main-baseline` | `798bf874` | detached |
| `/Users/garvey/.grok/worktrees/dev-eventrelay/grok-round1` | `a9effcf5` | `fix/vercel-functions-remediation-waituntil-middleware` |
| `/Users/garvey/dev/EventRelay/.claude/worktrees/sleepy-satoshi-613715` | `48dc1aa6` | `claude/sleepy-satoshi-613715` |

### 1.4 Stashes

```
stash@{0}: On main: lockfile drift on main
stash@{1}: On codex/eventrelay-sync-prep: local npm install drift
stash@{2}: On fix/ralph-max-clean: ai-codegen-wip
```

### 1.5 Local branch names (complete list as of probe)

```
billing-revenue-spine
chore/docs-audit-reports
chore/security/upgrade-dev-deps
chore/security/upgrade-vitest-vite
claude/beautiful-knuth-5afe5f
claude/beautiful-margulis
claude/clever-sutherland-c4f1e4
claude/gracious-lehmann-b7c92c
claude/sleepy-satoshi-613715
codex/uvai-studio-realtime
feat/a2a-wiring
feat/cloudevents-and-builtinai
feat/litert-setup
feat/sentry-nextjs
feat/vera-platform
fix/audit-issues
fix/audit-remediation-video-url-ssrf
fix/frontend-ux
fix/ralph-max-clean
fix/ralph-max-unclosed-demo-verification
fix/ralph-unclosed-max-demo-build
fix/restore-pk998-pattern
fix/vercel-functions-remediation-waituntil-middleware
fix/vertex-ai-express-mode
fix/video-processor-pipeline-stubs
fix/video-workflow-transcript
main
```

---

## 2. Live HTTP (public product)

| URL | HTTP | Observed | Probe time |
|-----|------|----------|------------|
| `https://uvai.io/` | **200** | HTML Next.js, `data-dpl-id=dpl_CHKfkAtwmwBwYraAvuAdXbYaRs3B` | 2026-07-09T23:15Z |
| `https://uvai.io/api/pipeline` | **200** | JSON pipeline metadata v1.0.0 | same |
| `https://uvai.io/api/billing/status` | **200** | `plan:free`, `status:inactive`, chatDailyLimit 5 | same |
| `https://api.uvai.io/api/v1/health` | **200** | `status:healthy`, version `2.0.0`, gemini_key_present true, youtube_api_key_present true | same |
| `https://api.uvai.io/health` | **200** | `service:uvai-youtube-extension` | same |

### 2.1 NOT verified this session (UNKNOWN)

| Check | Why unknown |
|-------|-------------|
| Full pipeline POST with real YouTube URL | Not run (costs + SSRF caution); schedule under GATE-2 |
| Stripe checkout live | Needs Turnstile + price IDs in Vercel env — not verified via API |
| Auth login | NextAuth live path not exercised |
| Vercel dashboard env list | CLI token invalid |
| GitHub open PR count | `gh` GraphQL 401 (see §4) |

---

## 3. GCP (`uvai-730bb`)

| Field | Value | Evidence |
|-------|--------|----------|
| Active account | `garveyht@gmail.com` | `gcloud auth list` (ACTIVE *) |
| Project | `uvai-730bb` | `gcloud config get-value project` |
| Project number | `688578214833` | appears in Cloud Run URLs |
| Region default | `us-central1` | `gcloud config list` |
| Firebase default | `uvai-730bb` | `.firebaserc` |

### 3.1 Cloud Run services listed (us-central1) — LIVE gcloud

| Service | URL | Last deployed (gcloud) |
|---------|-----|------------------------|
| **eventrelay-api** | `https://eventrelay-api-688578214833.us-central1.run.app` | 2026-07-08T20:59:52Z by `eventrelay-deployer@…` |
| **uvai-api** | `https://uvai-api-688578214833.us-central1.run.app` | 2025-12-31 (old) |
| **uvai-backend** | `https://uvai-backend-688578214833.us-central1.run.app` | 2026-06-18 by Garveyht@gmail.com |

**Mapping progress (2026-07-09T23:18Z):**

| Host / service | Health body fingerprint | Notes |
|----------------|-------------------------|--------|
| `https://api.uvai.io/api/v1/health` | `version":"2.0.0"`, gemini+youtube keys | Response headers include **Cloudflare** (`cf-ray`, `server: cloudflare`) |
| `https://eventrelay-api-688578214833.us-central1.run.app/api/v1/health` | **same** `2.0.0` + keys | **Strong match** to api.uvai.io |
| `https://uvai-api-….run.app` | **timeout** (10s, 0 bytes) | Treat as dead/hung |
| `https://uvai-backend-….run.app/` | `version":"1.0.0"`, “UVAI YouTube Extension API” | **Different** older service |

**Working conclusion (still confirm DNS/CNAME formally):** production API path is **Cloudflare → `eventrelay-api`**, not `uvai-api` / not the 1.0.0 `uvai-backend` root message. GATE-0 still wants `dig` + domain-mappings list.

### 3.2 BigQuery (CLI, 2026-07-09T23:18Z)

```
bq ls --project_id=uvai-730bb
→ only dataset: uvai_5b6dc7c4_15f7_46e5_80fb_50b6337ed14c
```

- Matches Data Agent catalog dataset id.  
- Code default `uvai_ml_training` (**does not appear** in `bq ls`).  
- **Conclusion:** product ML export dataset is **not provisioned** (or wrong project). Catalog dataset is not the app training warehouse.

### 3.3 GCS (sample list, same probe)

Buckets include (partial list):

- `gs://688578214833-us-central1-blueprint-config`
- `gs://688578214833_629292216_us_central1_import_document` (label `goog-drz-discoveryengine-…`, lifecycle delete age 3)

These look **Discovery Engine / blueprint infra**, not the EventRelay monorepo app storage path. Product link: **UNKNOWN** until code references grepped and confirmed.

### 3.4 Data Agent catalog (operator screenshot 2026-07-09)

- Views under the only BQ dataset: `bucket_activity_view`, `events_view`, `object_events_view`, …  
- Cloud SQL UI name: `all-strides-postgres-db` (docs claim different names — mismatch).  
- Side agent log: **`RAG status Unset`**.

---

## 4. Tool auth matrix (this machine)

| Tool | Binary present | Auth status | Impact |
|------|----------------|-------------|--------|
| `gh` | `/opt/homebrew/bin/gh` | **Keyring OK** (`groupthinking`). Agent process injects **invalid** `GITHUB_TOKEN` (len 40) which overrides keyring. Fix for agents: `env -u GITHUB_TOKEN -u GH_TOKEN gh …` | With unset: PR list works |
| `gcloud` | yes | **OK** — `garveyht@gmail.com`, project `uvai-730bb` | Can list Cloud Run |
| `vercel` | yes | **Logged in as `ultrathinking`** when `VERCEL_TOKEN` unset. Agent injects invalid `VERCEL_TOKEN` (len 24) | Use `env -u VERCEL_TOKEN vercel …` |
| `wrangler` | yes | **Broken:** not logged in (`Failed to fetch auth token: 400`) | Cloudflare ops via CLI unavailable |
| `firebase` | yes | Project file points `uvai-730bb` | CLI login not rechecked |
| `git` ssh | remote uses `git@github.com:…` | Fetch worked earlier | Git protocol separate from `gh` GraphQL |

### 4.0 Root cause (2026-07-09 clarification)

**Credentials were already on the machine.** The failure was not “missing secrets.”

| Var in agent env | Length | Effect |
|------------------|--------|--------|
| `GITHUB_TOKEN` | 40 | Invalid classic-style token; **forces** `gh` to use it instead of keyring |
| `GITHUB_FINE_GRAINED_TOKEN` | 93 | Present (likely valid); `gh` does **not** auto-use this name |
| `VERCEL_TOKEN` | 24 | Too short / invalid; **forces** Vercel CLI to ignore local login |

Also present in agent env (names only): `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `GEMINI_API_KEY`, `GOOGLE_API_KEY`, `AI_GATEWAY_API_KEY`, `VERCEL_AI_GATEWAY_API`, `PERPLEXITY_API_KEY`, `SUPABASE_ACCESS_TOKEN`, `GODADDY_API_KEY`, `GODADDY_API_SECRET`, `SPINE_API_KEY`, `OPENCLAW_GATEWAY_TOKEN`, `Vertex_AI_API_KEY`.

**Operator rule for this Grok session:** always run `gh` / `vercel` as:

```bash
env -u GITHUB_TOKEN -u GH_TOKEN -u VERCEL_TOKEN gh …
env -u GITHUB_TOKEN -u GH_TOKEN -u VERCEL_TOKEN vercel …
```

### 4.2 Additional GCP projects visible to account (sprawl — 2026-07-09T23:17Z)

`gcloud projects list` returned at least (list may be truncated in log):

| PROJECT_ID | NAME |
|------------|------|
| `uvai-730bb` | **active** product project |
| `agent-495116` | agent |
| `ai-multi-media-playground` | AI MULTI MEDIA Playground |
| `aicce-ce885` | AICCE |
| `artful-inverter-ff4r2` | express-mode-project |

**Rule:** Do not deploy EventRelay product changes to non-`uvai-730bb` projects unless inventory says so. Full project list should be re-dumped to `inventory/GCP-PROJECTS.md` under GATE-0.

### 4.1 Required owner actions (no code)

1. Unset or replace invalid `GITHUB_TOKEN` in shell profile / Cursor / agent env  
2. `gh auth switch --user groupthinking` then `gh auth status`  
3. Unset invalid `VERCEL_TOKEN` or `vercel login`  
4. Confirm Cloudflare account if used for DNS for `uvai.io` / `api.uvai.io`

---

## 5. Vercel linkage (from local project files — not CLI)

| File | projectId | projectName | rootDirectory | orgId |
|------|-----------|-------------|---------------|-------|
| `apps/web/.vercel/project.json` | `prj_4Qj52UTshPstdsMWdgFtN3B31j8B` | `v0-uvai` | **`apps/web`** | `team_3lNy0xpw2OnPBHCcsoG99Sru` |
| `.vercel/project.json` | same projectId | `v0-uvai` | null (root) | same |

Env pull artifacts present (names only):  
`apps/web/.vercel/.env.development.local`, `.env.preview.local`, `.env.production.local`  
**Do not commit. Do not paste contents.**

---

## 6. Local runtime environment (machine)

| Item | Value |
|------|--------|
| Node | v22.22.0 |
| Python | 3.14.2 |
| `.venv` | present |
| `node_modules` root | present |
| `apps/web/node_modules` | present |
| Env files present (names) | root `.env`, `.env.local`, backups; `apps/web/.env.local`, `.env.production`, examples |

---

## 7. 60-second smoke (re-run anytime)

```bash
date -u
curl -sS -o /dev/null -w "uvai.io:%{http_code}\n" --max-time 12 -L https://uvai.io/
curl -sS --max-time 12 https://uvai.io/api/pipeline | head -c 200; echo
curl -sS --max-time 12 https://api.uvai.io/api/v1/health; echo
curl -sS --max-time 12 https://uvai.io/api/billing/status; echo
cd /Users/garvey/Dev/EventRelay && git fetch origin && git status -sb && git rev-list --left-right --count origin/main...HEAD
gh auth status 2>&1 | head -20
gcloud config get-value project
vercel whoami 2>&1 | head -5
```

Paste output into a new file:  
`docs/control-plane/sessions/smoke-YYYY-MM-DDTHHMMZ.md`

---

## 8. Explicitly false or stale (do not trust)

| Claim source | Why false/stale |
|--------------|-----------------|
| Root `ARCHITECTURE.md` folder layout (`api/`, `ingest/`, …) | Those top-level dirs **do not exist**; real layout is `apps/web` + `src/youtube_extension` + `src/agents` |
| `docs/refactor/STATE.md` hybrid refactor tasks | Dated 2026-06-23; not current main |
| `shared/_core/SYSTEM_STATUS.md` | Dated 2026-01-02; “all operational” is not current evidence |
| `export/eventrelay-api/assemble.sh` | **Does not exist** |
| Standalone `../eventrelay-api` repo | **Does not exist** |
| `packages/*` as real monorepo libs | Empty or dist-only; workspaces only `apps/*` |
| `src/vera` as source package | **Only `__pycache__`**, no `.py` sources |
| Local commit message “extract EventRelay API” | Misnamed; 3 files only |
| PDF titled EventRelay containing OpenAI VPT paper | Research paper, not product doc |
| Data Agent “RAG status Unset” vs “RAG ready” docs | Unset in live agent log |

---

## 9. GATE-2 snapshot (2026-07-10T17:55Z)

| Check | Result |
|-------|--------|
| GET home / pipeline / billing / health | all **200** |
| POST pipeline default async | **200** job `job_638c836f7b` backend-async |
| Job poll absolute URL | **complete** progress 100, transcript ~767 chars |
| POST pipeline async=false | **200 partial** local-fallback, Gemini TIMEOUT |
| Direct API jobs unauthenticated | **401** (expected) |
| Report | `docs/control-plane/sessions/gate2-20260710T1755Z/REPORT.md` |
| Failures log | `docs/control-plane/inventory/KNOWN-FAILURES.md` |

---

## 10. GATE-3 snapshot (2026-07-10T17:59Z)

| Money-path check | Result |
|------------------|--------|
| Stripe secret + publishable + price env names | Present |
| Stripe price usable | **FAIL** `No such price: price_1Tos02…` on renew |
| Webhook secret | **MISSING** → 503 |
| Turnstile | **MISSING** → checkout 403 |
| KV Redis for entitlements | **OK** (KV_REST_API_*) |
| NextAuth/Google | **FAIL** 500; no GOOGLE_OAUTH_* / NEXTAUTH_URL |
| Paid E2E | Not attempted (blocked) |
| Full report | `sessions/gate3-20260710T1759Z/REPORT.md` |
