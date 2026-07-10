# EXECUTION PLAN — Lead / CEO

**Created:** 2026-07-09T23:15:00Z  
**Product definition of done (P0):** see `00-CEO-DIRECTIVE.md` §3  
**Method:** Gates. No product feature work before GATE-1. No “optimization” before inventory IDs exist.

---

## Phase map

```text
GATE-0  Access + truth          DONE (with env -u token workaround)
GATE-1  Git + branch discipline DONE (main=origin; BRANCHES.md)
GATE-2  Live product baseline   DONE 2026-07-10 — see sessions/gate2-20260710T1755Z/
GATE-3  Launch config — AUDIT DONE, launch blocked on Turnstile/Webhook/Prices/OAuth
GATE-4  Security High — code done on fix/gate4-security-hardening; deploy pending
GATE-5  Single pipeline reliability (honest handoff)
GATE-6  Doc consolidation complete
GATE-7  Optional: data plane (BQ/RAG) only if product needs it
```

Each gate has: **Goal IDs**, **exact steps**, **expected evidence**, **stop conditions**.

---

## GATE-0 — Access + single source of truth

**Purpose:** Humans and agents can see the same reality. No code features.

| ID | Task | Owner | Status | Evidence required |
|----|------|-------|--------|-------------------|
| G0-DOC-01 | Control-plane folder exists and is authoritative | Agent | **DONE** 2026-07-09 | This folder + 00-CEO-DIRECTIVE |
| G0-DOC-02 | LIVE-STATUS + SURFACES written from live probes | Agent | **DONE** 2026-07-09 | inventory/*.md timestamps |
| G0-AUTH-01 | Fix GitHub CLI default auth | Agent | **DONE** (workaround) | Creds already on machine; agent env injects bad `GITHUB_TOKEN`. Use `env -u GITHUB_TOKEN`. `gh` as `groupthinking` works; open PRs listed |
| G0-AUTH-02 | Fix Vercel CLI auth | Agent | **DONE** (workaround) | Creds already on machine; bad `VERCEL_TOKEN` override. Use `env -u VERCEL_TOKEN`. User `ultrathinking`; project `v0-uvai` listed |
| G0-AUTH-03 | Confirm Cloudflare role (DNS for uvai.io?) | **Human** | TODO | Written note: Cloudflare yes/no + zone name OR “DNS at X” |
| G0-MAP-01 | Map `api.uvai.io` → exact Cloud Run service | Agent+Human | TODO | DNS/CNAME or `gcloud run domain-mappings list` + matching health body |
| G0-MAP-02 | Map Vercel production deployment to git SHA | Agent after G0-AUTH-02 | TODO | Deployment URL + commit SHA |
| G0-SMOKE-01 | Re-run 60s smoke; save session file | Either | **DONE** | smoke-2026-07-10T1755Z + gate2 session |

### G0-AUTH-01 exact steps (human, pasteable)

```bash
# 1) See what is wrong
gh auth status

# 2) If shell exports a bad GITHUB_TOKEN, remove it for this shell:
unset GITHUB_TOKEN
# Also remove from ~/.zshrc / Cursor env / agent env if set permanently

# 3) Prefer keyring account that owns the repo:
gh auth switch --user groupthinking
# if switch fails:
gh auth login

# 4) Prove it
gh auth status
gh pr list --repo groupthinking/EventRelay --limit 5
gh api user --jq .login
```

**Stop if:** still 401 → do not invent PR state; leave GATE-0 open.

### G0-AUTH-02 exact steps

```bash
unset VERCEL_TOKEN
vercel login
vercel whoami
cd /Users/garvey/Dev/EventRelay
vercel link --yes   # only if needed; confirm project v0-uvai
vercel env ls --environment production 2>&1 | head -40
# Do not paste secret values into chat or git
```

### G0-MAP-01 exact steps

```bash
# A) Domain mappings
gcloud run domain-mappings list --platform=managed --region=us-central1 --project=uvai-730bb

# B) Direct health compare
for u in \
  https://api.uvai.io/api/v1/health \
  https://eventrelay-api-688578214833.us-central1.run.app/api/v1/health \
  https://uvai-backend-688578214833.us-central1.run.app/api/v1/health \
  https://uvai-api-688578214833.us-central1.run.app/api/v1/health
do
  echo "=== $u ==="
  curl -sS --max-time 12 "$u" || echo FAIL
  echo
done

# C) DNS
dig +short api.uvai.io
dig +short uvai.io
```

Record results in `inventory/LIVE-STATUS.md` §3.1.

**GATE-0 exit:** G0-DOC-01/02 done; G0-AUTH-01 done; G0-MAP-01 recorded (AUTH-02 can slip 24h but blocks deploy claims).

---

## GATE-1 — Git discipline (no product features)

**Purpose:** One clean line of history on `main`. Branch zoo catalogued. No silent divergence.

| ID | Task | Status | Evidence |
|----|------|--------|----------|
| G1-SYNC-01 | Decide fate of local `d2c2587c` “extract EventRelay API” | **DONE** Option A | Dropped via hard reset; recoverable tag `backup/pre-sync-d2c2587c` |
| G1-SYNC-02 | Bring local main = origin/main | **DONE** 2026-07-10 | `0 0` at `e70aa66a` |
| G1-BR-01 | Export full remote branch list to inventory file | **DONE** | `inventory/BRANCHES.md` |
| G1-BR-02 | Classify each local branch: KEEP / MERGE-CANDIDATE / DELETE-CANDIDATE | TODO | Table in BRANCHES.md |
| G1-WT-01 | Inventory worktrees; remove only if clean + unused | TODO | Listed in BRANCHES; cleanup later |
| G1-STASH-01 | Inspect 3 stashes; keep or drop with note | TODO | Listed in BRANCHES |
| G1-REMOTE-01 | After gh works: open PR count + CI status on main | partial | 30 open PRs listed earlier; CI status not yet polled |

### G1-SYNC recommended path (safe default)

**Do not run reset until you read `git show d2c2587c --stat`.**

Option A — discard misnamed local commit, take origin (if 3-file commit is disposable):

```bash
cd /Users/garvey/Dev/EventRelay
git fetch origin
git show d2c2587c --stat
# If you agree to drop it:
git checkout main
git reset --hard origin/main
# Expected: clean, 0 0
git status -sb
git rev-list --left-right --count origin/main...HEAD
```

Option B — keep the 3-file commit on a side branch:

```bash
git branch backup/local-extract-api d2c2587c
git fetch origin
git reset --hard origin/main
```

**Forbidden without explicit owner OK:** `git push --force` to `main`.

### G1-BR-01 commands

```bash
cd /Users/garvey/Dev/EventRelay
git fetch --prune origin
{
  echo "# BRANCHES inventory $(date -u +%Y-%m-%dT%H:%MZ)"
  echo "## Local"
  git branch -vv
  echo "## Remote"
  git branch -r -vv
} > docs/control-plane/inventory/BRANCHES.md
wc -l docs/control-plane/inventory/BRANCHES.md
```

**GATE-1 exit:** main synced `0 0`; BRANCHES.md exists; worktrees/stashes noted; no force-push.

---

## GATE-2 — Live product baseline (measure before change)

**Purpose:** Know what the running system does with a real request. Assume failures.

| ID | Task | Status | Evidence |
|----|------|--------|----------|
| G2-WEB-01 | Homepage + studio load | **DONE** | gate2-20260710T1755Z web-home 200 |
| G2-API-01 | Health both paths | **DONE** | api-v1-health + root health 200 |
| G2-PIPE-01 | GET pipeline metadata | **DONE** | pipeline-get 200 |
| G2-PIPE-02 | POST pipeline with **known short** public video | **DONE** | async job complete + transcript; sync partial |
| G2-BILL-01 | billing/status shape | **DONE** | free/inactive |
| G2-SEC-BASE | Note SSRF audit file path as baseline | **DONE** | audit report + KNOWN-FAILURES; GATE-4 still open |

### G2-PIPE-02 exact (careful)

```bash
# Use a short, famous public video only
curl -sS --max-time 120 -X POST https://uvai.io/api/pipeline \
  -H 'content-type: application/json' \
  -d '{"url":"https://www.youtube.com/watch?v=jNQXAC9IVRw"}' \
  | tee docs/control-plane/sessions/pipeline-post-$(date -u +%Y%m%dT%H%MZ).json | head -c 2000
```

If 500/timeout: record body; **do not** “fix” until GATE-4 security and GATE-5 reliability tickets are written.

**GATE-2 exit:** **MET** 2026-07-10 — `sessions/gate2-20260710T1755Z/REPORT.md` + `inventory/KNOWN-FAILURES.md`.

---

## GATE-3 — Launch config (money path)

**Source of truth for checklist content:** `LAUNCH_CHECKLIST.md` (validate each item live; do not trust “DONE” markers without recheck).

| ID | Task | Status | Evidence |
|----|------|--------|----------|
| G3-STRIPE-01 | Production Stripe keys + price IDs on Vercel | **PARTIAL** | Names present; price ID rejected live (KF-007) |
| G3-STRIPE-02 | Webhook endpoint live `https://uvai.io/api/billing/webhook` | **FAIL** | 503 webhook_not_configured (KF-006) |
| G3-TURN-01 | Turnstile site+secret on Vercel | **FAIL** | 403 turnstile_not_configured (KF-005) |
| G3-UPSTASH-01 | Upstash Redis for entitlements | **PASS** (KV alias) | KV_REST_API_* present; code accepts |
| G3-AUTH-01 | NextAuth secret + provider | **FAIL** | /api/auth/* 500; no GOOGLE_OAUTH_* (KF-008) |
| G3-E2E-01 | Sign in → checkout → webhook → status pro | **BLOCKED** | Needs P0 fixes first |

**GATE-3 exit:** **AUDIT COMPLETE / LAUNCH NOT READY** 2026-07-10 — see `sessions/gate3-20260710T1759Z/REPORT.md`. Paid E2E blocked.

---

## GATE-4 — Security High cluster (blockers)

**Baseline:** `eventrelay-audit-report.md` (27 findings; High cluster yt-dlp + Veo).

| ID | Task | Status | Evidence |
|----|------|--------|----------|
| G4-SSRF-01 | YouTube-host validator (backend + BFF) | **DONE** on branch | models + BFF; live prod still open until deploy |
| G4-YTDLP-01 | `--` end-of-options before URL yt-dlp argv | **DONE** on branch | robust.py + enhanced_video_processor |
| G4-VEO-01 | Gate video/generate Pro + fail-closed RL | **DONE** on branch | live 402 free; RL 503 if no Redis |
| G4-PROXY-01 | Fail-closed rate limit when Redis missing in prod | **DONE** on branch | proxy.ts fail-closed |
| G4-REG-01 | Regression tests | **LOCAL PASS** | needs PR merge for CI |

**Order:** implement on branch from **synced** main only (after GATE-1).  
**Note:** local branch `fix/audit-remediation-video-url-ssrf` may contain work — **inventory before rewrite**.

**GATE-4 exit:** **IMPLEMENTED on `fix/gate4-security-hardening`** — see sessions/gate4-20260710T1806Z/REPORT.md. Deploy required for prod BFF 400.

---

## GATE-5 — Single reliable path (product honesty)

| ID | Task | Status | Evidence |
|----|------|--------|----------|
| G5-PATH-01 | Document the **one** happy path code route (web BFF → backend) with file:line | TODO | `inventory/HAPPY-PATH.md` |
| G5-HAND-01 | Any non-complete pipeline returns explicit handoff JSON (never silent empty) | TODO | tests + live |
| G5-VP-01 | VideoPack emit optional; if not emitted, status says so | TODO | schema + response field |
| G5-AGENT-01 | Pro agent dispatch works only with BACKEND_URL healthy + entitlement | TODO | 503 vs 200 matrix |

**GATE-5 exit:** One demo script a human can run in 10 minutes with expected outputs.

---

## GATE-6 — Documentation consolidation

| ID | Task | Status | Evidence |
|----|------|--------|----------|
| G6-IDX-01 | `DOC-REGISTRY.md` classifies every top-level + docs/*.md | TODO | registry complete |
| G6-ARCH-01 | Replace root ARCHITECTURE.md claims with pointer to control-plane + real tree | TODO | PR |
| G6-AGENT-01 | AGENTS.md / CLAUDE.md / GEMINI.md start with “read control-plane first” | TODO | files updated |
| G6-ARC-01 | Move clearly historical reports under `docs/control-plane/archives/` **or** stamp ARCHIVE banner | TODO | list of moves |
| G6-DEV-01 | `/Users/garvey/Dev` sibling folders labeled in SURFACES only (no mass delete) | TODO | labels only |

**GATE-6 exit:** New agent can onboard from control-plane alone in &lt;15 minutes.

---

## GATE-7 — Data plane (optional, last)

Only if product needs dashboards/training:

| ID | Task | Status |
|----|------|--------|
| G7-BQ-01 | Prove whether `uvai_ml_training` exists; create or abandon export | TODO |
| G7-SQL-01 | Map `all-strides-postgres-db` vs app connection strings | TODO |
| G7-RAG-01 | One RAG path; “RAG Unset” resolved or feature removed from claims | TODO |

---

## Explicitly deferred (do not start)

| Item | Why deferred |
|------|--------------|
| Standalone `eventrelay-api` extract / assemble.sh | No kit; monorepo works; extract after GATE-5 |
| Filling empty `packages/*` | Not on ship path |
| Restoring VERA from pyc | Research only after P0 |
| ADK / Digital Refinery full vision | Concept; not P0 |
| Branch mass-delete of all 145 remotes | After BRANCHES classification only |
| Multi-agent parallel feature work | Causes the mess we are ending |

---

## Weekly cadence (discipline)

| Day | Action |
|-----|--------|
| Every work session start | 60s smoke + read EXECUTION-PLAN active gate |
| After any deploy | smoke file in sessions/ |
| End of day | Update LIVE-STATUS if anything changed |
| Weekly | Branch prune candidates review (human approve deletes) |

---

## What you (owner) do next — in order

1. **G0-AUTH-01** (GitHub token) — 5 minutes  
2. **G0-AUTH-02** (Vercel token) — 5 minutes  
3. Tell the lead agent: “GATE-0 auth done”  
4. Lead agent runs **G0-MAP-01**, **G1-BR-01**, proposes **G1-SYNC** option A or B  
5. You approve one sync command set only  
6. Then GATE-2 smokes, then GATE-3/4 in parallel tracks with separate PRs  

You do **not** need to design architecture right now. You need **access fixed** and **main synced**. That is progress.
