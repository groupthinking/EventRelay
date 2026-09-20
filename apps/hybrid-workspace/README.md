# Hybrid Workspace (Monaco + Split + iframe + fx)

Cursor-like / Udacity AI Learning Assistant split shell for EventRelay.

Closes #2183.

## Layout

```
[ Embed | Summarize | Extract | Escalate ]
+---------------------------+------------------+
| file tree | Monaco editor | AI chat          |
|           | iframe preview| suggested prompts|
+---------------------------+------------------+
| xterm  (fx when available, local fallback)   |
+----------------------------------------------+
```

## Run

```bash
cd apps/hybrid-workspace
python3 -m http.server 4173
# open http://localhost:4173
```

No build step. Monaco / Split / xterm load from jsDelivr.

## Real fx

1. `npm i libfx @xterm/xterm @xterm/addon-fit` in this folder if you want the native/wasm harness instead of the CDN xterm-only fallback.
2. Export a short-lived `AI_GATEWAY_API_KEY`.
3. Open in Chrome/Edge 137+ with WebAssembly JSPI.
4. `fx-adapter.js` calls `createFxTerminal` + `xtermAdapter` when those exist; otherwise it keeps the local action router so Summarize / Extract / Escalate still work.

## What is not included

YouTube player internals. Preview is a sandboxed iframe of *your* editor HTML. Drop a YouTube embed into that HTML only if the lesson itself needs a player.
