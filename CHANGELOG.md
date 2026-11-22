# Changelog

All notable changes to UVAI / EventRelay are documented in this file.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
versioning aims for [SemVer](https://semver.org/).

## [Unreleased]

### 2026-11-22: Remove pack-build-live re-export barrel (apps/web)

Tracked by #2788.

#### Removed

- `pack-build-live.ts`. It only re-exported `pack-build-live-client`, and the Studio UI already imports the client. The pack-build-live tests now import the client directly.

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
