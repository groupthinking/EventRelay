# SURFACES — Every place work / state lives

**Last updated:** 2026-07-09T23:15:00Z
**Purpose:** One map of tools and workspaces so agents stop inventing parallel homes.

Legend: **CANONICAL** = ship here · **SUPPORT** = allowed tooling · **ARCHIVE** = do not ship · **BLOCKED** = auth broken · **UNKNOWN** = not verified

---

## 1. Code & version control

| Surface | Path / ID | Role | Status |
|---------|-----------|------|--------|
| Product monorepo | `/Users/garvey/Dev/EventRelay` | All product code | **CANONICAL** |
| GitHub repo | `groupthinking/EventRelay` | Remote of record | **CANONICAL** (gh API currently **BLOCKED** by bad `GITHUB_TOKEN`) |
| Git protocol | `git@github.com:groupthinking/EventRelay.git` | fetch/push | Works for fetch (verified) |
| Local branches | 27 names | WIP | **SUPPORT** — inventory before delete |
| Remote branches | ~145 | clutter risk | **SUPPORT** — branch audit GATE-1 |
| Worktrees | 4 paths (see LIVE-STATUS) | agent sandboxes | **SUPPORT** — clean GATE-1 |
| Stashes | 3 | WIP | **UNKNOWN** content value |
| Meta-git on `/Users/garvey/Dev` | `/Users/garvey/Dev/.git` | Dangerous confusion | **ARCHIVE / DO NOT USE for product** |

---

## 2. Deploy / hosting

| Surface | ID / URL | Role | Status |
|---------|----------|------|--------|
| Vercel project | `v0-uvai` / `prj_4Qj52UTshPstdsMWdgFtN3B31j8B` | Frontend | **CANONICAL** for web |
| Vercel rootDirectory | `apps/web` (from apps/web/.vercel/project.json) | Build root | **CANONICAL** |
| Vercel CLI | `vercel` | Ops | **BLOCKED** invalid `VERCEL_TOKEN` |
| Public web | `https://uvai.io` | Production UI | **LIVE 200** |
| Public API host | `https://api.uvai.io` | Production API | **LIVE 200** |
| Cloud Run `eventrelay-api` | `…run.app` last deploy 2026-07-08 | Candidate API | **LIVE service exists** |
| Cloud Run `uvai-api` | last deploy 2025-12-31 | Legacy? | **LIVE but old** |
| Cloud Run `uvai-backend` | last deploy 2026-06-18 | Legacy? | **LIVE** |
| Custom domain → which service | DNS mapping | Critical | **UNKNOWN** — must resolve GATE-0 |
| Cloudflare | wrangler present | DNS/WAF/Turnstile possible | **UNKNOWN** account |
| Firebase | project `uvai-730bb` | Data Connect etc. | **SUPPORT** (not primary ship path) |

---

## 3. Google Cloud

| Surface | ID | Role | Status |
|---------|-----|------|--------|
| GCP project | `uvai-730bb` / `688578214833` | Cloud home | **CANONICAL** for backend cloud |
| gcloud account | `garveyht@gmail.com` | Ops | **OK** |
| Cloud Run | 3 services listed | API runtime | **LIVE list** |
| BigQuery | dataset UI `uvai_5b6dc7c4_…` + code wants `uvai_ml_training` | Data | **PARTIAL / MISMATCH** |
| Cloud SQL | UI showed `all-strides-postgres-db`; docs say `uvai-vector-db` | DB | **MISMATCH / UNKNOWN wiring** |
| GCS | blueprint, aiml-image-processing, prompt-data | Artifacts | **EXISTS**; product link **UNKNOWN** |
| Secret Manager | claimed in docs | Keys | **UNKNOWN** this probe (do not dump secrets) |
| Artifact Registry | `eventrelay-repo` claimed in BACKEND_DEPLOY | Images | **UNKNOWN** list this probe |
| Vertex / AI Platform | prompt-data paths in UI | Jobs/papers | **NOT product path** until proven |

---

## 4. AI operator tools (sprawl)

| Tool | Typical home | Role | Rule going forward |
|------|--------------|------|--------------------|
| Grok / this session | EventRelay workspace | Lead inventory + plan | Must write to `control-plane/` |
| Claude Code | `.claude/`, worktrees | Implementation agents | Read CEO directive first |
| Gemini / Google AI Studio | Drive + Cloud Data Agent | Specs / catalog | Concept unless promoted |
| Antigravity | (user-named) | Unknown local role | **UNKNOWN** — inventory path later |
| GitHub Copilot / Jules | PRs, issues, workflows | Automation | Stop until gh auth fixed |
| Cursor | `.cursor/` | Editor MCP | Config only |
| NotebookLM / MCP | various | Experiments | **ARCHIVE** unless wired |

**Policy:** One active implementation agent at a time for product code after GATE-1. Parallel agents only for read-only inventory.

---

## 5. Local filesystem workspaces under `/Users/garvey/Dev`

| Path | Approx size (earlier du) | Classification |
|------|--------------------------|----------------|
| `EventRelay/` | ~8.7G | **CANONICAL product** |
| `ALL VID-ANYTHING /` | ~14G | **ARCHIVE / experiments** (prototypes, PDFs, old `uvai.io` next-enterprise) |
| `refinery-agent/` | small | **EXPERIMENT** (Cloudflare Agents SDK) |
| `prescient-twin/` | ~134M | **EXPERIMENT** |
| `genkit-full-repo/` | ~31M | **EXPERIMENT** |
| `Grok-Claude-Hybrid-Deployment/` | ~53M | **ARCHIVE / historical** |
| `agents/` | ~10M | **SUPPORT** scripts + symlink to `~/.claude/agents` |
| `flash-ui/`, `webapp/`, `runner/`, `flutter/`, … | various | **NON-PRODUCT** |
| `_workspace_review/` | process buckets | **SUPPORT** for Dev cleanup only |
| `google-cloud-sdk/` | ~1.1G | **TOOL** |
| `MASTER_PROMPT.md` | file | **DIRTY** (merge conflict markers) — do not trust |
| `video_to_gtm_architecture.md` | file | **CONCEPT** |

**Policy:** No new product features outside EventRelay. Promotion requires written decision in `plans/PROMOTION-LOG.md` (create when first needed).

---

## 6. Google Drive / concept

| Path | Classification |
|------|----------------|
| `…/My Drive/UVAI + concept ` (trailing space) | **CONCEPT** — mostly `.gdoc` stubs offline |
| `…/Google AI Studio/` UVAI prompts | **CONCEPT** |
| `/Users/garvey/Documents/UVAI_MASTER_SPECIFICATION.md` | **CONCEPT** readable local copy |
| `/Users/garvey/Documents/UVAI - MASTER FILE DUMP (1).md` | **CONCEPT** |
| `ALL VID-ANYTHING /*.pdf` blueprints | **CONCEPT** |

Vision docs inform roadmap language only. They do **not** override LIVE-STATUS.

---

## 7. Credentials & env file map (names only)

| Runtime | Expected files | Notes |
|---------|----------------|-------|
| Next.js web | `apps/web/.env.local` (+ Vercel project env) | Billing/auth/AI for BFF |
| Python backend local | root `.env` | Backend keys |
| Vercel pulled | `apps/web/.vercel/.env.*.local` | Do not commit |
| Backups | `.env.local.bak.*` | Rotate/delete after inventory |

**Never** put secret values into control-plane docs.

---

## 8. What “progress” means on surfaces

Progress is only counted when:

1. LIVE-STATUS or a session smoke file is updated, **or**
2. An EXECUTION-PLAN goal moves `TODO → DONE` with verification commands attached, **or**
3. Auth moves BLOCKED → OK with evidence

Code pushed without (1)–(3) is **not** progress for this program.
