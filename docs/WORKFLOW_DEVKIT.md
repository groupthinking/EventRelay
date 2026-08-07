# Workflow DevKit (Vercel) in EventRelay

**Status:** Product v1 (2026-08-07) — scaffold + Studio “Act on findings”  
**Package:** `workflow` (monorepo root / apps/web)  
**Next integration:** `withWorkflow` in `apps/web/next.config.js`

## What it is

[Workflow DevKit](https://workflow-sdk.dev) provides durable multi-step runs:

- `"use workflow"` — orchestrator (sandboxed)
- `"use step"` — retryable Node units (full npm access)
- `start()` / `getRun()` from `workflow/api` — fire and poll from route handlers

**Product pipeline today still uses** FastAPI agents, `POST /api/pipeline`, SSE (`/api/pipeline/stream`), and Cloud Tasks for full Studio deploy / Dashboard analysis. WDK sits **alongside** that path for long transcript → action runs that should survive serverless timeouts.

## Product surface (v1)

| Piece | Path |
|-------|------|
| Workflow | `apps/web/src/workflows/video-to-actions.ts` |
| Start | `POST /api/workflows/video-to-actions` `{ "url", "videoTitle?" }` → `{ runId, statusUrl }` |
| Status | `GET /api/workflows/video-to-actions/:runId` → `{ runStatus, result? }` |
| Client helpers | `apps/web/src/lib/studio-workflow.ts` |
| Studio UI | **Act on findings** button in `VideoWorkflowStudio` |

Steps: **transcribe** (`fetchTranscript`) → **run action agent** (`runActionAgent`). No self-HTTP loopback.

## Local usage

```bash
cd apps/web
npm run dev
# start
curl -X POST http://localhost:3000/api/workflows/video-to-actions \
  -H 'Content-Type: application/json' \
  --json '{"url":"https://www.youtube.com/watch?v=dQw4w9WgXcQ"}'
# poll (use runId from response)
curl http://localhost:3000/api/workflows/video-to-actions/<runId>
npx workflow web
npx workflow inspect runs
```

## Middleware / rate limits

- `middleware.ts` only matches `/dashboard` and `/api/*`. `/.well-known/workflow/` is **not** matched.
- `/api/workflows` is on the AI rate-limit prefix list in `src/proxy.ts`.

## Turbo

`turbo.json` build outputs include `apps/web/src/app/.well-known/workflow/**` so cache hits keep workflow registration.

## Next product steps

1. **C — Studio deploy durable:** kickoff + poll `/api/pipeline` jobs as WDK steps with automatic retry.  
2. Stream step progress via `getWritable()` into Studio.  
3. Human approval hooks (`createHook` / `resumeHook`) before deploy.  
4. Optionally route Dashboard “act” through the same durable path.

## Relation to F-series

| Item | Note |
|------|------|
| F3 / F5 / F12 | Studio + actions surfaces already on main; this wires **durable** act-on-findings |
| F11 Payload CMS | Still deferred |
