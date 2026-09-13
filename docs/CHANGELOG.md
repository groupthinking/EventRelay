# Changelog

All notable changes to UVAI / EventRelay are documented in this file.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
versioning aims for [SemVer](https://semver.org/).

## [Unreleased]

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
