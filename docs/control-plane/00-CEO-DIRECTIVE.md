# CEO DIRECTIVE — EventRelay / UVAI

**Authority:** Lead / CEO mode for this workspace  
**Effective:** 2026-07-09T23:15:00Z (UTC)  
**Status:** BINDING until explicitly superseded in this folder  

---

## 1. Why this exists

Progress has stalled because:

- Multiple AI tools (Claude, Grok, Gemini, Antigravity, Copilot, Jules) act without a shared inventory
- Docs, branches, and cloud resources claim different “truths”
- Agents summarize, assume, and edit product code before knowing what is live
- Human attention is spent re-explaining sprawl instead of finishing a short list

This folder is the **only operational source of truth** for planning and agent work.

---

## 2. Hard rules (non-negotiable)

### 2.1 Assume nothing works until live-proven

| Rule | Meaning |
|------|---------|
| No claim of “works” | Without a command + timestamp + observed output in `inventory/` or `sessions/` |
| No claim of “fixed” | Without re-running the same live check after the change |
| No claim of “deployed” | Without URL + HTTP status + body snippet from the live host |
| No claim of “merged” | Without `git` / GitHub evidence after re-auth |

### 2.2 Freeze product mutation until Phase GATE-0 and GATE-1 clear

Until `plans/EXECUTION-PLAN.md` marks **GATE-0** and **GATE-1** complete:

| Allowed | Forbidden |
|---------|-----------|
| Inventory, probes, docs under `docs/control-plane/` | Feature code “while we’re here” |
| Auth repair (gh, vercel, gcloud) | Refactors, package renames, monorepo surgery |
| Git hygiene **with explicit user approval** (reset/rebase) | Force-push, mass branch delete without list |
| Moving/labeling **docs** into control-plane / archives | Deleting unknown folders under `/Users/garvey/Dev` |
| Reading secrets locations (file **names** only) | Printing secret **values** into docs or chat |

### 2.3 No agent may start “implementation” without citing inventory IDs

Every implementation prompt must include:

1. Goal ID from `plans/EXECUTION-PLAN.md` (e.g. `G2-SEC-01`)
2. Live baseline evidence from inventory (what was true before change)
3. Exact verification commands to run after change
4. Out-of-scope list (what not to touch)

If those four are missing, **stop and update inventory first**.

### 2.4 One product, one git root, one ship path

| Role | Canonical location |
|------|-------------------|
| Product code | `/Users/garvey/Dev/EventRelay` only |
| Git remote | `git@github.com:groupthinking/EventRelay.git` |
| Public web | `https://uvai.io` (Vercel project `v0-uvai`, rootDirectory `apps/web`) |
| Public API | `https://api.uvai.io` (must be mapped to a single Cloud Run service — see inventory) |
| GCP project | `uvai-730bb` (project number `688578214833`) |
| Ops docs | `docs/control-plane/` |

Everything else under `/Users/garvey/Dev` and Drive is **archive / experiment / concept** until promoted by a written decision in `plans/`.

### 2.5 Documentation authority

| Document class | Location | Rule |
|----------------|----------|------|
| **Operational truth** | `docs/control-plane/**` | Must be updated when reality changes |
| **Historical / research** | `docs/control-plane/archives/` or original path with ARCHIVE label | Do not use for “what ships” |
| **Agent identity files** | Root `AGENTS.md`, `CLAUDE.md`, `GEMINI.md` | Must **point here**; must not invent architecture |
| **Marketing / vision** | Drive, PDFs, MASTER dumps | Never override live inventory |

Stale claims in `ARCHITECTURE.md`, `docs/refactor/STATE.md`, `shared/_core/SYSTEM_STATUS.md` are **not authoritative**. See inventory.

---

## 3. What “done” means for the company (narrow)

Not “complete UVAI ecosystem.” Not “Digital Refinery ADK.”  

**Product done (P0):** A user can:

1. Open `https://uvai.io`
2. Sign in (when auth configured) or use free path honestly
3. Paste a YouTube URL and get a **bounded** result (transcript/analysis or explicit failure)
4. Optionally pay for Pro (Stripe) with durable entitlement
5. Backend at `api.uvai.io` stays healthy
6. No known High severity unauthenticated SSRF/injection path on the public proxy → yt-dlp chain

Everything else is P1/P2 and waits for inventory + P0.

---

## 4. Human (owner) incapacity assumption

The lead agent must:

- Write steps a non-expert can paste
- Prefer checklists with expected outputs
- Never say “just sync main” without exact commands and failure modes
- Never require the human to remember 5 tools’ state — put it in inventory files

---

## 5. Session start protocol (every agent, every tool)

Before any work:

```text
1. Read docs/control-plane/00-CEO-DIRECTIVE.md
2. Read docs/control-plane/plans/EXECUTION-PLAN.md (active phase only)
3. Read docs/control-plane/inventory/LIVE-STATUS.md (latest)
4. Run the 60-second smoke in LIVE-STATUS.md if older than 24h
5. Confirm: which GATE are we on? Is product freeze still on?
6. Only then act
```

---

## 6. Supersession

To change these rules: edit this file, set new timestamp, add a one-line entry to `sessions/CHANGELOG.md`.
