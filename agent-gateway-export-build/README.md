# AI Gateway + Agent Export Build

This is a drop-in implementation scaffold for the requested feature:

- Vercel AI Gateway smoke test using the `ai` SDK.
- Server-side AI streaming route.
- Agent Substrate export schema.
- Durable workflow-style export orchestration using `"use workflow"` and `"use step"` boundaries.
- Inspector Sidebar `Download` button that exports the selected agent's knowledge, connections, and event history as JSON.
- Tests for redaction, validation, and export behavior.

## Setup

```bash
npm install
vc env pull .env.local
npm run ai:smoke
npm run typecheck
npm test
npm run build
```

`vc env pull .env.local` can provide `VERCEL_OIDC_TOKEN` so the local smoke script can authenticate this app to AI Gateway. That token does not authorize HTTP callers.

`POST /api/ai/stream` stays disabled until both `AI_STREAM_ENABLED=1` and `AI_STREAM_AUTH_TOKEN` (at least 16 characters) are set. Callers must send `Authorization: Bearer <AI_STREAM_AUTH_TOKEN>` with one ASCII space and no extra padding. Scheme case may vary; every accepted form shares one request budget. The model comes only from `AI_GATEWAY_MODEL` (default `openai/gpt-5.5`); a different `model` in the body is rejected. Prompts are capped at 4000 characters, completions at 1024 output tokens, and each token is limited to 6 requests per minute in the current instance.

## Files to integrate into your existing app

```txt
index.mjs
src/app/api/ai/stream/route.ts
src/app/api/agents/[agentId]/export/route.ts
src/components/InspectorSidebar.tsx
src/lib/agent-substrate/schema.ts
src/lib/agent-substrate/store.ts
src/workflows/agentExport/index.ts
src/workflows/agentExport/steps.ts
tests/export.test.mjs
```

## Replace the demo store

`src/lib/agent-substrate/store.ts` is intentionally an adapter boundary. Replace its in-memory functions with your real Agent Substrate persistence layer.

Keep the exported function names stable so the workflow and API route do not need to change:

- `getAgentById(agentId)`
- `getAgentKnowledge(agentId)`
- `getAgentConnections(agentId)`
- `getAgentEventHistoryPage(agentId, cursor)`
- `recordAgentExportAuditEvent(agentId, payload)`

## User flow

1. User selects an agent.
2. Inspector Sidebar enables `Download`.
3. Button calls `/api/agents/{agentId}/export`.
4. Backend runs the export workflow.
5. API returns a JSON attachment.
6. Browser downloads `agent-{name}-{date}.json`.

## Security guarantees

Connection exports include useful metadata but redact secrets:

- API keys
- Access tokens
- Refresh tokens
- Client secrets
- Authorization headers
- Password-like fields
- Raw environment values

## Failure framework

The implementation uses structured error classes:

- `auth`
- `not_found`
- `schema_invalid`
- `gateway_unavailable`
- `event_history_partial`
- `download_client_error`

Transient step-level failures should be retried by the workflow runtime when you plug this into your production workflow engine.
