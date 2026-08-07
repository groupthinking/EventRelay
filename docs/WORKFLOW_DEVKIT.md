# Workflow DevKit (Vercel) in EventRelay

**Status:** scaffolded 2026-08-07  
**Package:** `workflow` in the monorepo (workspace root install)  
**Next integration:** `withWorkflow` in `apps/web/next.config.js`

## What it is

[Workflow DevKit](https://workflow-sdk.dev) provides durable multi-step runs:

- `"use workflow"` — orchestrator (sandboxed)
- `"use step"` — retryable Node units (full npm access)
- `start()` from `workflow/api` — fire from route handlers

## First product workflow

| Piece | Path |
|-------|------|
| Workflow | `apps/web/src/workflows/video-to-actions.ts` |
| Trigger | `POST /api/workflows/video-to-actions` `{ "url": "https://…", "videoTitle": "…" }` |

Steps: **transcribe** → **run action agent** (existing `action-agent` / tools).

## Local usage

```bash
cd apps/web
npm run dev
# another terminal:
curl -X POST http://localhost:3000/api/workflows/video-to-actions \
  -H 'Content-Type: application/json' \
  --json '{"url":"https://www.youtube.com/watch?v=dQw4w9WgXcQ"}'
npx workflow web
npx workflow inspect runs
```

## Middleware

`middleware.ts` only matches `/dashboard` and `/api/*`. Workflow internal paths under `/.well-known/workflow/` are **not** matched, so no extra exclusion is required today. If the matcher becomes a catch-all, exclude `.well-known/workflow/`.

## Turbo

`turbo.json` build outputs include generated Workflow routes under `apps/web` so cache hits keep workflow registration.

## Next product steps

1. Wire Studio Deploy to `start(videoToActionsWorkflow)` or a dedicated deploy workflow.
2. Stream step progress via `getWritable()` into Studio UI.
3. Optional human approval hooks before deploy.
