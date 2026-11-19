# Frontend Visual Integrity & Cross-Page Cohesion Rules

## 1. Mandatory Screen-Recording Gate (No Static-Only Sign-Off)
- Never declare a UI, layout, or styling change complete using only static above-the-fold screenshots or unit tests.
- Before committing or reporting completion on any `apps/web` visual change, record a continuous screen recording (`chrome-devtools-mcp` `screencast_start` -> full-page scroll + multi-route walkthrough -> `screencast_stop`), save it to the artifact directory, and inspect the video via `read_file`.
- Verify at **three viewports**: half-screen (`720x900`), standard desktop (`1440x900`), and wide desktop (`1920x1080+`), plus **both Dark and Light themes**.

## 2. Cross-Page Cohesion & Single-Purpose Routes
- **One Shell System**: `/`, `/studio`, `/pricing`, and `/docs/api` must share a consistent visual language, typography rhythm, and predictable navigation chrome—never mix unrelated page shells across sibling routes without explicit user approval.
- **No Redundant Checkout Slabs**: `/pricing` owns plan comparison and checkout. Do not embed a second full-size checkout/Turnstile slab at the bottom of `/` that consumes >25% of landing-page height.
- **No Narrow Floating Islands**: Workbenches (`/studio`) and rail-backed pages must fluidly occupy the available inline space (`1fr` beside the rail) rather than leaving wide dead gutters between the rail and main content.
- **Theme Parity**: Every custom surface (including showcase cards and gradients) must honor Light, Dark, and High-Contrast tokens—never hardcode dark card backgrounds that clash in Light mode.

## 3. Modern Web Guidance First
- Before architecting or refactoring CSS layout, grid/subgrid, container queries, or responsive shells, query `npx -y modern-web-guidance@latest search "<query>"` and `retrieve "<id>"`.
- Prefer intrinsic sizing (`fr`, `minmax()`, `grid-template-areas`, `@container`, `dvh`/`dvw`, `scrollbar-gutter: stable`) over brittle fixed pixel widths or `overflow: hidden` band-aids.
