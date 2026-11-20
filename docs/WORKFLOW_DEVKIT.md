# Workflow DevKit (Vercel) in EventRelay

**Status:** Product v1 (2026-08-07) — scaffold + Studio “Act on findings”  
**Package:** `workflow` (monorepo root / apps/web)  
**Next integration:** `withWorkflow` in `apps/web/next.config.js`

## What it is

[Workflow DevKit](https://workflow-sdk.dev) provides durable multi-step runs:

- `"use workflow"` — orchestrator (sandboxed)
- `"use step"` — retryable Node units (full npm access)
- `start()` / `getRun()` from `workflow/api` — fire and poll from route handlers

**Product pipeline today is the Video Pack pipeline** (`POST /api/video/pack` → Upstash → Studio → G.A.T.E.). The legacy FastAPI/`POST /api/pipeline`/SSE path was retired. WDK remains for long transcript → action runs that should survive serverless timeouts.

## Product surface (v1)

| Piece | Path |
|-------|------|
| Workflow | `apps/web/src/workflows/video-to-actions.ts` |
| Start | `POST /api/workflows/video-to-actions` `{ "url", "videoTitle?" }` → `{ runId, statusUrl }` |
| Status | `GET /api/workflows/video-to-actions/:runId` → `{ runStatus, result? }` |
| Client helpers | `apps/web/src/lib/studio-workflow.ts` |
| Studio UI | **Act on findings** button in `OneLoopStudio` (canonical studio) |

Steps: **transcribe** (`fetchTranscript`) → **run action agent** (`runActionAgent`). No self-HTTP loopback.

## Local usage

```bash
cd apps/web
npm run dev
# start
curl -X POST http://localhost:3000/api/workflows/video-to-actions \
  -H 'Content-Type: application/json' \
  --json '{"url":"https://www.youtube.com/watch?v=auJzb1D-fag"}'
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

## Product C — Studio deploy preflight

| Piece | Path |
|-------|------|
| Workflow | Removed. `POST` does not start a durable run. |
| Kickoff / poll lib | `apps/web/src/lib/pipeline-async-job.ts` remains for other jobs. It is not started by Studio deploy. |
| Start | `POST /api/workflows/studio-deploy` returns **409** after G.A.T.E. No `runId` is created. |
| Status | `GET /api/workflows/studio-deploy/:runId` can still read a historical workflow run. |
| Studio UI | No deploy button. The route is the refusal. |

Auth: this route stays **session-gated**. Studio now has a Sign in link. Never use `dQw4w9WgXcQ` as a fixture — use `auJzb1D-fag`.

## Next product steps

1. Stream step progress via `getWritable()` into Studio.  
2. Human approval hooks (`createHook` / `resumeHook`) before deploy.  
3. Optionally route Dashboard “act” through the same durable path.

## Relation to F-series

| Item | Note |
|------|------|
| F3 / F5 / F12 | Studio + actions surfaces already on main; this wires **durable** act-on-findings |
| F11 Payload CMS | Still deferred |
