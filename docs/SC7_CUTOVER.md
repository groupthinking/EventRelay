# SC7 Cutover — frontend → pure SDK consumer

Goal (SC7): `apps/web` submits a URL, polls job status, and renders
transcript/events/artifacts **only** through the backend contract. No business
logic and no model calls in the frontend.

> Why this is a checklist and not a single commit: it is a delete-heavy refactor
> of a working app, and it must be executed where TypeScript compiles
> (`npm install` then `npm run build && npm run test` in `apps/web`) — the
> review sandbox has no `node_modules` and cannot verify TS. Run it locally or
> let CI gate each step. Use the **strangler order** below so the app is never
> in a long-lived broken state.

## Already landed (additive, safe)

- `apps/web/src/lib/eventrelay-client.ts` — typed client for the clean
  `/api/v1/jobs` contract. Imports no model SDK.
- `apps/web/src/lib/__tests__/eventrelay-client.test.ts` — unit + structural
  guard (backend-down → typed error; source imports no model SDK).

## The second backend to remove

Route handlers under `apps/web/src/app/api/` (delete **after** callers are
rewired):

```
agents/dispatch/route.ts   agents/status/route.ts   chat/route.ts
dashboard/route.ts         extract-events/route.ts  pipeline/route.ts
pipeline/stream/route.ts   route.ts                 transcribe/route.ts
video/route.ts             video/search/route.ts    training/status/route.ts
training/trigger/route.ts  (+ app/api/__tests__/*)
```

`pipeline/stream/route.ts` is also a **REAL_MODE_ONLY violation**: it fabricates
multi-agent SSE events with `sleep()` timing and invented confidence scores
(0.92/0.88/0.71) and calls Gemini directly. It must go, not be ported.

Model/second-backend libs under `apps/web/src/lib/` to delete once unreferenced:

```
gemini-client.ts  gemini-embedding.ts  gemini-video-analyzer.ts
agent-pipeline.ts  use-agent-pipeline.ts  transcription-service.ts
embedding-store.ts  training-store.ts  cloudevents.ts  api-client.ts
services/builtin-ai.ts  services/agent-service.ts
services/event-service.ts  services/video-service.ts
```

Keep `types.ts`/`agent-types.ts` entries still referenced by surviving
components; prune the rest.

## Strangler order (each step builds + tests green before the next)

1. **Rewire the data layer.** Point the dashboard store
   (`apps/web/src/lib/**/dashboard-store.ts`) at `eventRelay`:
   `submitJob` → `pollUntilDone` → `getTranscript`/`getEvents`/`getArtifacts`.
   Remove the SSE `/api/pipeline/stream` subscription.
2. **Rebind or remove the agent-flow UI.** The synthetic multi-agent
   visualization (`AgentFlowVisualizer`, `PipelineProgress`, `useAgentPipeline`)
   is driven by fabricated events. Either delete it or rebind it to the **real**
   job lifecycle (`queued → running → succeeded/failed`). No invented agents.
3. **Repoint remaining callers** of `apiClient`/`services/*` to `eventRelay`.
4. **Delete** the `app/api/*` routes and the now-unreferenced libs above.
5. **Drop dependencies** that only those files used, from
   `apps/web/package.json`: `@google/genai`, `@google/generative-ai`, `openai`,
   and any others (`@upstash/redis`, `@dataconnect/generated`, …) left with no
   importers. Verify with `npm run build`.
6. **Regenerate the SDK** from `service/openapi.json` via Stainless and replace
   the hand-written `eventrelay-client.ts` with the generated client (or keep
   the thin client if you prefer — it already matches the contract).

## Acceptance test (must pass before merge)

- Unit (landed): backend-down → `EventRelayError`; client imports no model SDK.
- Integration/E2E to add: with the backend unreachable, the dashboard renders an
  **error state** and makes **zero** requests to any `googleapis.com` /
  `openai.com` host. Assert via a network spy in the E2E run.
- With the backend up: every data value on the dashboard originated from an
  `eventRelay.*` call (no client-side extraction).

## Sequencing note

Keep the legacy backend (`src/youtube_extension`) and its 40-path
`openapi/eventrelay.openapi.json` running until step 6 completes and the
frontend no longer references the old contract. Delete the legacy backend last.
