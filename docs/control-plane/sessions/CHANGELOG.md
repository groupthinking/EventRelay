# Control-plane session changelog

## 2026-07-09T23:15Z — Bootstrap

- Created control-plane tree and CEO directive
- Live probes: uvai.io 200, api.uvai.io health 200, billing/status free/inactive
- Git: main ahead 1 / behind 6; local d2c2587c misnamed extract commit
- Auth: gh default broken (bad GITHUB_TOKEN); vercel token invalid; gcloud OK (uvai-730bb)
- Cloud Run listed: eventrelay-api (2026-07-08), uvai-backend (2026-06-18), uvai-api (2025-12-31)
- Active gate: **GATE-0** (auth + map api.uvai.io)
- Product code freeze until GATE-0/1 per directive
- Follow-up probe 23:18Z: api.uvai.io via Cloudflare; health JSON matches eventrelay-api 2.0.0; uvai-api times out; uvai-backend is 1.0.0 different app
- `bq ls`: only dataset `uvai_5b6dc7c4_…`; no `uvai_ml_training`
- gh still blocked: env `GITHUB_TOKEN` overrides keyring and is invalid
- Parallel inventory: wrangler **not logged in**; gcloud account sees multiple projects beyond `uvai-730bb` (agent, playground, aicce, express-mode) — product deploys stay on `uvai-730bb` only

## 2026-07-10T17:54Z — Option A git sync

- User authorized best recommendation (Option A)
- `git reset --hard origin/main` → HEAD `e70aa66a`, left-right **0 0**
- Discarded tip preserved: tag `backup/pre-sync-d2c2587c` → commit `d2c2587c` (3-file misnamed extract)
- Wrote `inventory/BRANCHES.md` (27 local, 145 remote)
- Smoke: uvai.io 200, pipeline 200, api health 200, billing free/inactive → `sessions/smoke-2026-07-10T1755Z.md`
- Control-plane banners re-applied after hard reset wiped uncommitted M files
- GATE-1 SYNC complete; next: G1-BR-02 classification optional, GATE-2 pipeline POST

## 2026-07-09 — Auth root cause corrected

- User was right: credentials already on disk / keyring / agent env
- Failure mode was **bad overrides**, not missing secrets:
  - Agent-injected `GITHUB_TOKEN` len=40 invalid → shadows `gh` keyring
  - Agent-injected `VERCEL_TOKEN` len=24 invalid → shadows Vercel login
- Workaround: `env -u GITHUB_TOKEN -u VERCEL_TOKEN` before CLI
- Verified: `gh` → `groupthinking`, open PRs listed; `vercel whoami` → `ultrathinking`; `v0-uvai` is team `garv1` production project

## 2026-07-10T17:57Z — GATE-2 complete

- Live async pipeline: kickoff + job complete + transcript (Me at the zoo)
- Sync path: partial local-fallback, Gemini TIMEOUT, no live_url
- Poll bug: relative status_url (KF-001) — product returns relative; clients must absolute-ize
- Artifacts: sessions/gate2-20260710T1755Z/
- KNOWN-FAILURES.md created (KF-001..004)
- Next: GATE-3 launch config verification (env names already listed; live checkout not run)

## 2026-07-10T18:00Z — GATE-3 audit

- Vercel prod env inventoried (names only)
- Live: checkout 403 turnstile_not_configured; webhook 503; renew No such price; auth 500
- KV_REST_API_* present → entitlement durability OK via alias
- Report: sessions/gate3-20260710T1759Z/REPORT.md
- KF-005..009 added
- Launch blocked until human dashboard fixes; then re-probe G3-E2E

## 2026-07-10T18:10Z — GATE-4 security hardening

- Branch fix/gate4-security-hardening
- BFF YouTube allowlist (pipeline + video) — prod still vulnerable until deploy
- yt-dlp -- on enhanced_video_processor; robust.py already had it
- Veo Pro gate live 402; rate limit fail-closed in prod
- proxy AI rate limit fail-closed without Redis
- Tests: vitest 26 pass; pytest SSRF model tests pass
- Report: sessions/gate4-20260710T1806Z/REPORT.md
