# Current architecture (AUDIT-008 / #2170)

**Authority order:** [AGENTS.md](../AGENTS.md) → [README.md](../README.md) → [REPO_MAP.md](REPO_MAP.md) → [NEXT-PHASE.md](NEXT-PHASE.md).

## Canonical user path

1. `/` — paste YouTube URL  
2. `/studio` — `OneLoopStudio` workbench  
3. `/api/video/pack` — hashed Video Pack (Upstash REST in production)  
4. `/api/workflows/video-to-actions` — durable transcript → analyze → review-only actions  
5. `studio.deploy` — Origin G.A.T.E. (`/api/gate/transitions`) + HTTP probe (`/api/gate/probe-live`) before live claims  

## Internal runtime

- FastAPI: `src/youtube_extension/main.py` (`PYTHONPATH=src`)  
- Agents: `youtube_extension.services.agents.adapters.agent_orchestrator` (canonical)  
- MCP: `youtube_extension.services.mcp.registry` + `orchestrator.py`  
- Legacy / experimental: `src/agents/*` (logged warning on use)

## Historical docs

Do not execute as product truth: [video_to_gtm_architecture.md](video_to_gtm_architecture.md) (bannered historical).
