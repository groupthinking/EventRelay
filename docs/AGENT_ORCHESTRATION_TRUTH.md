# Agent orchestration — active path (AUDIT-004)

## Canonical runtime path (today)

1. **Product / Studio** — Next.js workflows and `/api/agents/dispatch` availability probe; heavy lifting on Vercel (`apps/web`).
2. **Backend API** — `src/youtube_extension/services/agents/adapters/agent_orchestrator.py` for Cloud Run–hosted agent dispatch tied to API v1.
3. **Legacy / experimental** — `src/agents/mcp_agent_network.py`, `src/agents/pipeline_orchestrator.py` remain for internal EventRelay experiments; **not** the public UVAI▶ path.

## Rule

New agent features must extend the adapter orchestrator or web workflow layer—do not add a fourth dispatcher without an architecture review.

## Retirement candidates

Files under `src/agents/` that are not imported from `youtube_extension.main` or CI smoke paths should be treated as archive-only until explicitly revived.
