# UVAI▶ — Agent Instructions

Grok Build (`grok --cwd <this-repo>`) appends this file to the system prompt.
This is the live UVAI product repo (`uvai.io`, Vercel project `v0-uvai`).

**Do not invent prices, catalog SKUs, or stack.** If a fact is not locked here, look it up in the repo or leave it unset.

## Product (locked)

**UVAI▶** (Universal Video Action Intelligence).

Paste a YouTube URL → hashed **Video Pack** → shipable architecture / build rails.

The differentiator is **action / ship**, not transcription. Do not compete with Google on STT or models. Ride **Gemini 3.8 Flash via Vercel AI Gateway**.

## Pricing (locked)

| Offer | Price |
| --- | --- |
| Workflow Pro | **$39/mo** and **$390/yr** |
| Maintain | **$199/mo** per live product |
| Ship | **per-job quote** |

Do **not** use **$19** / **$180** (dead EventRelay Pro catalog).

Do not invent other prices or imply Maintain / Ship checkout exists unless the repo already implements it.

## Pack store (locked)

Video Pack persistence is **Upstash REST only** (`KV_REST_API_*`, or the equivalent `UPSTASH_REDIS_REST_*` pair the integration injects).

**Official Redis TCP is not the pack store.** Do not add `redis://`, ioredis, or other TCP Redis clients for packs.

## Already live (do not re-litigate)

- Get Pro checkout
- Hashed Video Pack
- UI unify — single skin; `/dashboard` and sibling skins redirect into the canonical studio
- Pack-quality — architecture / artifacts / `stack.tools`; **no forced Shopify gate**

## Lineage backbone (locked)

```
UVAI▶
  → Video Pack
  → Mission Workspace
  → Agent Factory / Slingshot
  → EventRelay          ← internal runtime, not a public brand
  → Zero-Sim / G.A.T.E. ← Origin hardgate
  → ExperienceOS
```

**FORGE / Workbench / Living Notebook / VIZUL** are UX patterns only — not product brands and not parallel products.

## Operating model (locked)

| Role | Owns |
| --- | --- |
| **UVAI Loop** | The standing ship |
| **Chief of Staff** | Orchestration only — no codebase diving |
| **Grok Build** | Repo-side checker (`grok --cwd`) |
| **Builder** | Stays off parallel UVAI cuts unless Loop asks |

## Authorized next cut

**Origin G.A.T.E.** only.

`asRecord` / claim stay **held** unless that cut requires them. Do not start adjacent cuts (Mission Workspace, Agent Factory, ExperienceOS, FORGE-as-product, etc.) unless Loop asks.

## Grok Build discovery

- **Project rules:** this `AGENTS.md` (also `CLAUDE.md` if present). Grok walks repo root → cwd. Each file is capped at 10k characters.
- **Skills:** auto-discovered from `.grok/skills/` (repo or cwd). Extra `[skills] paths` belong in `~/.grok/config.toml`, not project config.
- **Project `.grok/config.toml`:** official docs honor **`[mcp_servers]` only** here. Do not add one unless sharing MCP servers. This repo has no committed project MCP config.
- **Existing Claude skills** in `.claude/skills/` load via Grok’s Claude compatibility. Do not duplicate them under `.grok/skills/` unless a Grok-native override is required.
- **Workflows:** `.grok/workflows/*.rhai` (already present). Treat as automation, not product lineage.
- Confirm what loaded: `grok inspect --cwd <this-repo>`.

## Repo conventions

- Verify before submit. If a feature has no test, add one.
- Conventional Commits, imperative mood, subject &lt; 72 chars (`feat:`, `fix:`, `docs:`, …).
- Test fixtures: use `auJzb1D-fag`. Do **not** use `dQw4w9WgXcQ`.
- No secrets in git. No mock/hardcoded data from production AI paths.
- EventRelay code under `src/`, `mcp-servers/`, and related paths is the **internal runtime**. Do not rebrand it publicly as EventRelay.

## Nightly audit (Jules)

When running the nightly first-principles audit (status &gt; 400 or latency &gt; 200ms): analyze origin, remediate atomically, add a preventative guard. Manual dry-run:

```bash
PYTHONPATH=src python3 scripts/nightly_audit_agent.py --dry-run
```
