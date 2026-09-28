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
