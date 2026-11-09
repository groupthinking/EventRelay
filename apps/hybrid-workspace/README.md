# UVAI Hybrid Workspace (Monaco + Split + iframe)

Public brand: **UVAI**. EventRelay stays the internal runtime.

This folder is a **studio-pane prototype** for the Cursor / Udacity split UX
(Embed, Summarize, Extract, Escalate). Canonical product surface remains `/studio`.
Do not treat this directory as a second public product.

Closes #2183.

## Run

```bash
cd apps/hybrid-workspace
node --experimental-vm-modules logic.test.mjs
python3 -m http.server 4173
```

Open http://localhost:4173

Monaco / Split / xterm load from jsDelivr. No Gateway key in the browser.

## fx

The bottom pane is an **activity log** with typed commands. A real `libfx`
attach needs a bundler + import map + WASM assets + a **server-side** short-lived
token. `python -m http.server` cannot resolve `libfx/browser` or inject
`AI_GATEWAY_API_KEY`. Do not export that key onto `window`.

## Preview sandbox

The iframe uses `sandbox="allow-scripts"` only (no `allow-same-origin`) so
student JS cannot read the parent page.

## Deterministic boundary verification

From the repository root, after `npm ci`:

```bash
node apps/hybrid-workspace/logic.test.mjs
(cd apps/web && npx --no-install playwright install chromium)
node apps/hybrid-workspace/browser.test.mjs
```

`jsdom` and `playwright` are locked under `apps/web`, so both tests resolve them
from that workspace (`createRequire` anchored at `apps/web/package.json`) rather
than by bare root-level name. To use a system Chromium instead of Playwright's,
set `HYBRID_CHROMIUM_PATH`.

The browser test serves the actual app modules on loopback, substitutes fixture
adapters for the CDN editor/terminal/layout APIs, and stubs every external
request. Each case has a 10 s timeout. It covers (#2202): the preview sandbox is
exactly `allow-scripts`; preview code cannot reach the parent DOM, storage,
cookies, popups, downloads, top navigation, or the parent's
`AI_GATEWAY_API_KEY`; HTML/CSS/JS edits reach the preview; embedded `</script>`
and `</style>` cannot break out; missing assets and repeated edits; Embed,
Summarize, Extract and free-form Ask with escaping; terminal commands; unique
Escalate and terminal ticket IDs; and no key in `window`, storage, URL, or chat.
It writes a JSON receipt (path from `HYBRID_BOUNDARY_RECEIPT`, default in the OS
temp dir) tied to `VERIFIED_HEAD`; CI uploads it as the
`hybrid-workspace-boundary-receipt` artifact. It does not certify live Monaco
compatibility or Gateway execution, and needs no production credentials.

The `Hybrid Workspace Boundary` workflow runs on PRs and pushes to `main` that
touch this directory, the workflow, `package-lock.json`, or `apps/web/package.json`.

## Status

This directory stays a **prototype**. `/studio` is the main product surface; no
redirect or integration into `/studio` has been decided.
