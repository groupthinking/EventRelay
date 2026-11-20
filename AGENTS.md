# UVAI▶ — Agent Instructions

Grok Build (`grok --cwd <this-repo>`) appends this file to the system prompt; keep locked UVAI facts here.

**Public brand:** UVAI▶ at https://uvai.io
**Repo of record:** github.com/groupthinking/EventRelay
**Live Vercel project:** `v0-uvai` (not Origin tmp project `uvai`)

**Do not invent prices, catalog SKUs, or stack.** If a fact is not locked here, stop and ask — do not guess.

## Product (locked)

**UVAI▶** (Universal Video Action Intelligence).

Paste a YouTube URL → hashed **Video Pack** → shipable architecture / build rails.

The differentiator is **action / ship**, not transcription. Do not compete with Google on STT or models. Ride **Gemini 3.8 Flash via Vercel AI Gateway** as the video-to-spec extractor (`google/gemini-3.8-flash`). Do not wait on Qwen. Do not self-host 80GB. Do not put an LLM in Origin wasm.

## Pricing (locked)

| Offer | Price |
| --- | --- |
| Workflow Pro | **$39/mo** and **$390/yr** |
| Maintain | **$199/mo** per live product |
| Ship | **per-job quote** |

Do **not** use **$19** / **$180** (dead EventRelay Pro catalog).

Do not invent other prices or imply Maintain / Ship checkout exists unless the repo already implements it.

## Pack store (locked)

Video Pack persistence is **Upstash REST only** (`KV_REST_API_*`, or the equivalent `UPSTASH_REDIS_REST_*` pair the integration injects). Sole pack store resource name: `upstash-uvai-pack`.

**Official Redis TCP is not the pack store.** Do not add `redis://`, ioredis, or other TCP Redis clients for packs. Do not use TCP `STORAGE_REDIS_URL` / `redis-carmine-saddle` as the pack store.

## Already live (do not re-litigate)

- Get Pro checkout (Turnstile→Stripe)
- Hashed Video Pack
- UI unify — single skin; `/dashboard` and sibling skins redirect into the canonical studio
- Pack-quality — architecture / artifacts / `stack.tools`; stack-checks grounded in pack tools — **no forced Shopify gate** on Cloudflare/X402 sources like `MNNfat_QP0E`

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

**FORGE / Workbench / Living Notebook / VIZUL** are UX patterns only — not product brands and not parallel products. Do not bounce work to forge, slingshot, reach, uvai-skills, ClipToAction, or Origin tmp project `uvai`. Origin is **not** Google G.A.T.E./GEAR; do not retarget to GEAR.

## Operating model (locked)

| Role | Owns |
| --- | --- |
| **UVAI Loop** | The standing ship |
| **Chief of Staff** | Orchestration only — no codebase diving |
| **Grok Build** | Inspects/reviews repos via `grok --cwd` |
| **Builder** | Stays off parallel UVAI cuts unless Loop asks |

## Authorized next cut

**Origin G.A.T.E.** only.

`asRecord` / claim stay **held** unless that cut requires them. Do not start adjacent cuts (Mission Workspace, Agent Factory, ExperienceOS, FORGE-as-product, etc.) unless Loop asks.

## Exit (locked)

uvai.io distribution-ready **and** 50 distinct videos with real Video Packs. The 50/50 milestone is already met on the official list.

## G.A.T.E. vs Zero-Sim (locked)

- **Zero-Sim:** is the evidence real? (`real` | `unverified` | `unreal`). Never invent evidence.
- **G.A.T.E.:** do verified evidence + authority permit this state transition?
- Every consequential transition resolves to exactly one of **PASS | HOLD | REJECT | ESCALATE**.
- Missing required evidence → **HOLD**. Weak/unverified evidence → **HOLD**. Unreal or a live claim without a verified receipt → **REJECT**. Unknown authority / unknown Zero-Sim verdict → **ESCALATE**.
- G.A.T.E. does not build the artifact and is not the project database. Plane stays **proposed** until config + receipts verify. SeeScriptShip lock ≠ install/run/deploy.
- Contract: `apps/web/src/lib/gate-transition.ts`. Spec: `docs/gate-transition-contract.md`.
- Gated today: Studio `studio.deploy` (`proposed` → `live`) in `OneLoopStudio` — no live success claim unless G.A.T.E. **PASS**es a verified `https://` hostname URL (#1707 / #1710).

## Grok Build discovery

- **Project rules:** this `AGENTS.md` (also `CLAUDE.md` if present). Grok walks repo root → cwd. Each file is capped at 10k characters.
- **Skills:** auto-discovered from `.grok/skills/` (repo or cwd). Extra `[skills] paths` belong in `~/.grok/config.toml`, not project config.
- **Project `.grok/config.toml`:** official docs honor **`[mcp_servers]` only** here (`https://docs.x.ai/build/settings`). This repo ships GitHub and Vercel MCP stubs that expand `GITHUB_TOKEN` / `VERCEL_TOKEN` (optional `VERCEL_TEAM_ID`) at load time — no secrets in git. Enable from the checkout with `grok mcp add ... -s project` (commands are commented in that file). Confirm what loaded: `grok inspect --cwd <this-repo>`.
- **Existing Claude skills** in `.claude/skills/` load via Grok’s Claude compatibility. Do not duplicate them under `.grok/skills/` unless a Grok-native override is required.
- **Workflows:** auto-discovered from `.grok/workflows/*.rhai` (already present). Treat as automation, not product lineage.

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

## Security dependency maintenance

For an advisory-driven dependency update, follow [docs/security-dependency-maintenance.md](docs/security-dependency-maintenance.md). Reuse the canonical issue/PR, preserve direct versus transitive dependencies, and include the Security dependency evidence block. Before an authorized merge, re-fetch the exact head, applicable checks, reviews, unresolved threads, and mergeability; use expected-head protection and record the resulting merge commit. A recipe or green historical run is not current verification. This procedure grants no deployment or spending authority.

## Agent staff governance

Full spec: [docs/agent-staff-governance.md](docs/agent-staff-governance.md).

- **Five rules:** (1) no external state change without a standing policy or task authorization; (2) one human approval gate; (3) all work committed to a tracked GitHub branch; (4) a changelog entry linked to the issue, PR, or Video Pack hash; (5) every fix leaves an SOP and a regression test or check.
- **The one gate (Hayden):** production deploys, live database changes, billing, entitlements and spend, and credentials or access settings. CI-green merges to `main` that touch none of these fall under the standing merge policy (POL-001) and MERGE_POLICY.md.
- **Policy loop:** spot the inconsistency, propose a rule plus its check, Hayden approves it once, then codify it and enforce it automatically.
- **Hiring brief:** every agent role states what it owns, how it thinks, its definition of done, and what it never touches. It states its execution limits before taking work and never claims access it lacks.
