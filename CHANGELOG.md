## 2026-11-22 — Benchmark evidence correction

- Reclassify the three static benchmark examples as unverified fixtures; remove unsupported acquisition dates and latency measurements and prevent their quality gates passing.
- Retain deterministic hash/scaffold coverage and add a regression guard. SOP: `docs/benchmark-evidence-maintenance.md`. Related live-acceptance work: https://github.com/groupthinking/EventRelay/pull/2472 (not completed by this fix).

# Changelog

All notable changes to UVAI / EventRelay are documented in this file.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
versioning aims for [SemVer](https://semver.org/).

## [Unreleased]

- Studio deploy preflight no longer polls a run id. `POST /api/workflows/studio-deploy` returns a gate or an error, so the unreachable poll, the always-null receipt URL, and the unused live-claim helper are gone. The receipt card remains the only live-URL check. Related: #2328.
- Studio Deploy unify (Cut 5): one G.A.T.E. preflight path + receipt card as primary outcome UI. PASS may show a verified https live URL; non-PASS never claims live. No deploy/billing/credentials policy change; fixture `auJzb1D-fag`. Related: #2872.
- Studio IA rename keeps one activity type and one output-section union. The duplicate context-surface mapper, the test-only mode list, and the unused `initialSection` prop are gone. Related: #2328.
- Studio IA rename (Cut 4): Agents/Tools/Files/Canvas/Code activity modes wire to existing chat + four deliverable tabs (Tasks & Tools / Transcript / Preview / Code & Spec). No persona grid; fixture `auJzb1D-fag`. Related: #2868.
- Studio chat artifact stream uses the transcript stage the shell already computed. The unused `activeStage` prop, the orphaned `.studio-chat-timeline` rule, and the second stage derivation are gone. Related: #2328.
- Studio Agents chat shows Cut 3 pack-forming artifact stream (skeletal → real extract stages → settled architecture/artifacts/stack preview). No mock pack content; fixture `auJzb1D-fag`. Related: #2862.
- Studio event display reads pack `events[]` through one parser. The unused display count, sample-events wrapper, and lib task note are gone. Related: #2328.
- Studio stage shell keeps one activity mode and derives the mobile pane from it. The second pane state, unused controlled props, and the `[hidden]` `!important` overrides are gone. Related: #2328.

### 2026-11-24: Long Video Packs use one agentic Gemini call

Tracked by #2808.

#### Changed

- A YouTube video of at least 300 seconds is extracted with one direct Gemini Interactions call on `gemini-3.8-flash`, `processing: "agentic"`, and `thinking_level: "high"`. The call sends no offsets and no fps. Shorter clips keep the static shard path.
- A grounded citation on that call must stay inside `0..durationSeconds`. A citation past the duration is invalid (`out-of-range-citation`).
- An empty response, invalid JSON, or an SDK rejection of agentic processing throws `VideoPackExtractError`. There is no static full-video fallback.

### 2026-11-22: Obsolete unused-surface cleanup

#### Removed

- Fly deploy script and `FLY_API_TOKEN` setup/template refs
- Broken `scripts/nightly_audit_agent.py` and its unit test
- Empty `STAGE_RUNNERS` autonomous-video CI scripts, workflow, and unit tests
- Unused `infrastructure/k8s/ray/**` manifests (kept `src/uvai/ml` library)
- Deleted-backend verify/populate/load probes and `AUTOMATION_LAUNCHER.sh`

#### Changed

- Relocated `knowledge_base` to `src/agents/knowledge_base.py` and fixed the
  `mcp_agent_network` import (no more `scripts/` on `sys.path`)
- Retargeted `tests/e2e/pipeline.test.ts` so `/features` and `/dashboard`
  assert permanent redirects to `/` and `/studio`

### 2026-11-22: Honest Studio Events and Pro export toast (apps/web)

Tracked by #2491. Live unsigned dogfood of `pBsT6v-ciO8` on uvai.io.

#### Fixed

- Detected events no longer render analysis `insight` cards when the Video Pack has no `events[]`. Empty copy is "this pack has no extracted events".
- `verifyIdentityPack` keeps real pack `events[]` so Detected events can render extracted events when the store actually has them. It still does not invent events from visual_elements or analysis insights.
- Live Events stage counts pack `events[]` only. Visual on-screen elements stay under Keyframes extras, not as extracted events.
- Unsigned **Export** / Ship this on 402 stays on Studio with a Pro-required toast. It does not assign `window.location` to Stripe Checkout.

### 2026-11-22: Studio transcript, player, export, and proposed-tool honesty (apps/web)

Related: #2491. Does not close it. Dogfood video `pBsT6v-ciO8`. No G.A.T.E. No invented events.

#### Changed

- A slow transcript fetch shows the remaining-time estimate in the transcript pane. A failed fetch keeps **Retry transcript** next to the error in the live Studio transcript.
- A YouTube player that does not load is covered by an error state with **Retry player** and **Open on YouTube**.
- The Video Pack ZIP success toast sits above the sticky mobile dock and uses the page colors so the download confirmation stays visible.
- Named pack tools, including SeaDance 2.5, Claude Fable 5, Character.ai, and Cluely Desktop, render as **Proposed** cards that say UVAI has not run them.
- Studio content on a narrow screen keeps 72px of clearance above the sticky pane dock.

### 2026-11-19: WebMCP preview permissions ([#2746](https://github.com/groupthinking/EventRelay/pull/2746))

#### Fixed

- Skip optional WebMCP tool registration when the browser's permissions policy
  denies `tools`, and handle permission failures without unhandled rejections.
- Handle in-flight registration cancellation during Studio effect cleanup while
  preserving diagnostics for unexpected failures. Security headers are unchanged.

#### Regression SOP

- Run `npm --workspace=apps/web run test -- src/lib/__tests__/webmcp-studio-tools.test.ts`
  for changes to WebMCP initialization (16 tests cover registration, denied or
  unavailable APIs, audits, and cancellation).
- Run the web app type check and ESLint on the changed TypeScript files.
- Check `/studio` normally and with `Permissions-Policy: tools=()` enforced by a
  local verification proxy. Confirm the sidebar toggles after hydration and no
  uncaught errors appear. Preserve restrictions rather than enabling tools in
  embedded previews; forward development WebSocket traffic through the proxy.

### 2026-11-22: Grok Vercel MCP uses OAuth, not VERCEL_TOKEN (docs)

#### Changed

- `.grok/config.toml`: Vercel MCP stub is URL-only (`https://mcp.vercel.com`).
  A static `Authorization: Bearer ${VERCEL_TOKEN}` header made Grok skip OAuth
  and fail `mcp doctor vercel` with `invalid_token`. GitHub still uses
  `Bearer ${GITHUB_TOKEN}`. First Vercel grant is stored in
  `~/.grok/mcp_credentials.json`. (#2778)
- `docs/vercel-ai-setup.md`: Vercel MCP is Streamable HTTP + OAuth 2.1;
  `VERCEL_TOKEN` remains CLI/REST-only.

### 2026-11-22: Evidence-bound local video reconstruction

#### Added

- A local UVAI Video Pack → browser reconstruction → EventRelay command path, tracked by [#2798](https://github.com/groupthinking/EventRelay/issues/2798). The strict contract separates source-linked evidence, inferred architecture, generated files and verified browser behavior, with a reusable JSON Schema projection.
- An original browser interface for the retained `auJzb1D-fag` tutorial's URL attachment, structured-summary rendering and image-annotation flows. Imported outputs are explicitly user-supplied; live inference and token counts are not simulated as successful model calls.
- Fixed-argument integration with the existing durable local artifact harness. Receipts bind immutable manifest content, exact source/profile/generated bytes, the browser run and capture inventory. Missing, failed or changed evidence cannot replay as verified.
- Focused contract/CLI regressions and a Chromium CI workflow retaining screenshots, recordings and source-bound receipts. The [reconstruction SOP](docs/video-reconstruction.md) records source provenance and the duplicate-poster/timestamp discrepancy.

Full original-app acceptance, live inference, visual parity and deployment remain held. The public Studio, existing evidence-viewer export, extraction provider, pack store and Origin G.A.T.E. are unchanged.

### 2026-11-22: Remove finished lib task logs

#### Removed

- Ten completed `PLAN.md` files under `apps/web/src/lib/`. Nothing in the app imported them. Emitter fixtures and tests stay. (#2793)

### 2026-11-22: Remove fixture-only skill import and factory handoff (apps/web)

Tracked by #2786.

#### Removed

- `chatgpt-mcp-skill-import` and `factory-video-pack-handoff`, plus their tests. Neither module had a production importer. The `xymcbrfsj4c-emit` fixture stays; other pack tests still use it.
- Direct `yaml` dependency. It was only imported by the skill-import module. Vite still lists `yaml` as an optional peer.

### 2026-11-22: Remove pack-build-live re-export barrel (apps/web)

Tracked by #2788.

#### Removed

- `pack-build-live.ts`. It only re-exported `pack-build-live-client`, and the Studio UI already imports the client. The pack-build-live tests now import the client directly.

### 2026-11-22: Drop unused studio store search surface

#### Removed

- Studio video store no longer keeps `searchQuery`, `searchResults`, `searchLoading`, `setSearchQuery`, `loading`, `setLoading`, or `selectedVideo()`. Nothing in the studio reads them. `processVideo` and the persisted video list are unchanged.
- Unused `SearchResult`, `Activity`, and `PipelineResult` types. `pipelineResult` was never written.

### 2026-11-22: Remove unused transcript embedding path (apps/web)

Tracked by #2787.

#### Removed

- `embedding-store.ts` and `gemini-embedding.ts`. Neither had a production importer after `/api/video/search` was removed. Both were unchanged since the November 4 lib audit.
- Gateway embedding helpers that only those modules called: `gatewayEmbed`, `gatewayEmbedOne`, `chunkTextForEmbedding`, and `VERCEL_AI_GATEWAY_EMBEDDING_MODEL`. Chat completion on the same client stays.

### 2026-11-22: Remove unused lib helpers (apps/web)

Tracked by #2790.

#### Removed

- `hasUpstashSearch`, `packChapterSchema`, `JSON_CANVAS_SPEC`, `JSON_CANVAS_SPEC_URL`, and deprecated `resolveBillingEmailFromRequest`. Each had no caller. The files were unchanged since the November 4 lib audit.
- Unused `zipUtf8Files` import in `action-surface.ts`. The export stays; workspace export and its tests still call it.

### 2026-11-22: Anonymous Studio Ship this skips named-tool checks (apps/web)

Dogfood pack `pBsT6v-ciO8` (SeaDance 2.5, Claude Fable 5, Character.ai, Cluely Desktop).

#### Changed

- Named-tool stack checks that UVAI cannot run stay `unknown`. Their label says they can be skipped and are not a production hold. It does not mark them passed.
- The sticky Studio action is **Ship this** (`studio-ide-ship`). It enables from pack exportability (transcript, architecture, artifacts, or stack) and is not disabled by those four checks.
- Signed-in `deployHoldReason` still holds while Vercel, Shopify, or GitHub checks in `pack.stack.tools` are open. Anonymous Studio does not start a G.A.T.E. deploy.

### 2026-11-20: Grok Build project MCP wiring (docs)

#### Added

- `.grok/config.toml`: project-scoped GitHub and Vercel MCP stubs. GitHub uses
  the official remote `https://api.githubcopilot.com/mcp/` with
  `Authorization: Bearer ${GITHUB_TOKEN}`. Vercel uses `https://mcp.vercel.com`
  with `${VERCEL_TOKEN}` (optional `${VERCEL_TEAM_ID}`). Stubs are committed;
  `grok mcp add ... -s project` comments use single-quoted headers so a
  shell-exported token cannot land in the tracked file. (#2760)

#### Changed

- `AGENTS.md`: remaining locked public facts (repo of record, extractor model
  id, pack store resource name, no-bounce list, 50/50 exit). README points
  `grok inspect --cwd` at those instructions. (#2760)

### 2026-11-19: Nightly audit cleanup (apps/web)

Tracked by #2756.

#### Removed

- Unwired HTTP surfaces with no in-repo caller: legacy `/api/video`, dashboard embed, search, video search, video generate, extract-events, agent dispatch/status, realtime session, training, refinery dataset, studio chat routes, and `/api/v1/video/*` aliases. `/api/agents/actions` stays; the durable review journal imports it.
- Shared in-memory preferences route (`let sessionPreferences`) and its unused client.
- Studio deploy durable workflow. `POST /api/workflows/studio-deploy` stays a 409 G.A.T.E. refusal and does not start a run.
- Unused `agentWorkflowUi` flag, discarded Studio computations, GitHub PR server action with no button, unused field/empty/label/separator primitives, styled-jsx types, and two unreferenced public PNGs.

#### Changed

- Public privacy, terms, API docs, and `GET /api` name the product UVAI.
- Renew panel, spec-review button, and alert use the light studio tokens.
- Studio chat `POST /api/chat` uses `AbortSignal.timeout(30_000)`.
- `test:gate` no longer lists the deleted `OneLoopStudio.gate.test.tsx`.
- Pricing no longer carries the hidden billing-marker paragraphs. Checkout still names Turnstile in visible copy.
- Pack admission fixtures no longer use the banned video id.
- The home smoke spec matches the current heading.

`apps/hybrid-workspace` is unchanged. Auth-path entries for the removed URLs stay, so those paths remain session-gated. `apps/backend/requirements.txt` pins the pydantic 2.14.3 and pydantic-core 2.50.4 versions already resolved for that file on main.

### 2026-11-13: Agent staff governance (docs)

#### Added

- `docs/agent-staff-governance.md`: five rules, a single human approval gate
  (production deploys, live DB, billing/spend, credentials/access), a standing
  CI-green merge policy (POL-001), the inconsistency-to-policy loop, and the
  agent hiring brief.
- Summary section in `AGENTS.md`, `CLAUDE.md` and `GEMINI.md` pointing to it.

### 2026-05-22 — UVAI Phase 1: SEO, a11y, static assets

Baseline pulse identified the following gaps between repo `main` and the live
`uvai.io` deployment (live was stale; assets referenced by `layout.tsx` 404'd):

#### Added

- `apps/web/public/` directory with previously-missing static assets referenced
  by `apps/web/src/app/layout.tsx`:
  - `favicon.ico` (multi-resolution: 16/32/48/64)
  - `icon.svg` (vector, gradient-on-void brand mark)
  - `apple-touch-icon.png` (180x180)
  - `og-image.png` (1200x630 OG/Twitter card)
  - `manifest.json` (PWA manifest with theme colors)
  - `robots.txt` (allow all, sitemap pointer)
- `apps/web/src/app/sitemap.ts` — Next.js Metadata Route sitemap generator
  for `/`, `/dashboard`, `/pricing`, `/features`, `/playground`.
- JSON-LD structured data (`Organization`, `WebSite`, `SoftwareApplication`)
  injected via `apps/web/src/app/layout.tsx`.
- Skip-to-main-content link in `layout.tsx` for keyboard / screen-reader users.

### Changed

- `apps/web/src/app/layout.tsx`: `metadataBase` and `openGraph.url` corrected
  from `https://v0-uvai.vercel.app` to canonical `https://uvai.io`. Added
  `alternates.canonical`.
- `apps/web/src/app/page.tsx`: `<main>` now has `id="main"` to receive the
  skip link target.
- `apps/web/src/components/landing/LandingNav.tsx`: added `aria-label="Primary"`
  on `<nav>`, `aria-label` on the GitHub external link with "(opens in new tab)"
  hint, `aria-label="UVAI home"` on the brand link, and visible focus rings on
  all interactive elements.
- `apps/web/src/components/landing/HeroSection.tsx`: visible focus rings on
  primary and secondary CTAs; `prefers-reduced-motion` honored for the marquee
  animation.

### Notes / known follow-ups (not in this change)

- ~~`apps/web/next.config.js` contains duplicate `redirects()` / `headers()`
  function declarations~~ — resolved since: the file now contains exactly one
  `redirects()` and one `headers()` declaration.
- Live `uvai.io` title `UVAI — Video to Software` is stale vs `main`
  (`UVAI — The Action Layer for Video`). Resolving requires redeploy and is
  out of scope for this PR (no production / Vercel access used).

### 2026-05-22 — Review fixes for PR #202

#### Changed

- `apps/web/src/app/layout.tsx`: replaced `dangerouslySetInnerHTML` JSON-LD
  injection with React `<script>{jsonLdString}</script>` children, escaping
  `<` as `<` to prevent any nested `</script>` breakout. Complies with
  the repo's no-`dangerouslySetInnerHTML` policy.
- `apps/web/src/app/layout.tsx`: moved `id="main"` onto the root layout's
  content wrapper so the skip-to-main link works on every route, not only
  the homepage.
- `apps/web/src/app/page.tsx`: removed the now-duplicate `id="main"` from
  the homepage `<main>` element.
- `apps/web/src/lib/site.ts` (new): single `SITE_URL` constant. Adopted by
  `layout.tsx` and `sitemap.ts` so canonical URL changes happen in one place.

#### Fixed

- `CHANGELOG.md`: markdownlint MD022 — added blank lines after `#### Added`,
  `### Changed`, and `### Notes / known follow-ups (not in this change)`
  headings.
