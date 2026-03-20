# MCP Servers Ecosystem

This directory contains the Model Context Protocol (MCP) servers used in the EventRelay (UVAI) ecosystem.

## Canonical Orchestrator — `mcpc/` ✅

**`mcpc/`** is the **single canonical MCP server** for EventRelay. It consolidates functionality from 8 previously scattered repositories into one unified TypeScript package.

| Consolidated Origin | Feature Ported |
|---|---|
| MCPC (canonical, TypeScript) | Server infrastructure |
| MCP_ROUND_TABLE | `round_table` — multi-agent consensus |
| Mcpcserver (JavaScript) | Merged into server infrastructure |
| mcp-tools-extension | `list_tools` / `execute_tool_chain` |
| shared-state | `state_set` / `state_get` / `state_list` / `state_delete` |
| MCP_IOS | `platforms/ios/` _(future)_ |
| MCP-management | **Archived** |
| MESH | **Archived** |

See [`mcpc/README.md`](mcpc/README.md) for full documentation.

## Core Python Suite (`python-suite/`)

The primary intelligence suite for video processing and code analysis.

| Server                             | Description                      | Key Tools                                              |
| ---------------------------------- | -------------------------------- | ------------------------------------------------------ |
| `youtube_uvai_mcp.py`              | Primary UVAI Processor           | `process_video`, `get_transcript`, `ai_reasoning`      |
| `video_agent_server.py`            | Video Pipeline Orchestrator      | `transcribe_media`, `generate_actions`                 |
| `code_analysis_server.py`          | Automated Code Review            | `scan_security`, `analyze_performance`, `check_style`  |
| `cloudflare_server.py`             | Cloudflare Gateway Proxy         | `get_gateway_url`                                      |
| `learning_analytics_mcp_server.py` | Analytics Engine                 | `get_learning_stats`, `track_event`                    |
| `embeddings_mcp_server.py`         | pgvector Semantic Search         | `embed_text`, `search_similar`, `embed_video_analysis` |

## Specialized Servers

- **`litert-mcp/`**: Google LiteRT-LM edge inference.
- **`genkit-wrapper/`**: Firebase Genkit integration for model orchestration.
- **`puppeteer-server/`**: Browser automation and web scraping. (External)
- **`metacognition-tools/`**: Advanced reasoning tools (Fermi estimation, Red Teaming).
- **`mcp-profiling/`**: Internal performance profiling and verification.
- **`unified-analytics/`**: Metrics collection and graph analysis engine.

## External Active Servers

- **`grok-server/`**: xAI Grok integration.
- **`perplexity-mcp/`**: Perplexity AI search.
- **`github/`**: Custom GitHub integration.

## Central Coordination

- **MCPC Orchestrator** (`mcpc/`): canonical tool dispatch, round-table, state, and tool-chain execution.
- **MCPC Python Adapter** (`src/mcp/mcpc_adapter.py`): connects EventRelay's Python backend to MCPC via stdio transport.
- **Registry** (`src/mcp/mcp_registry.json`): lists all active MCP servers; `mcpc` is the `canonical_orchestrator`.

## Maintenance & Archiving

Redundant or prototype versions of these servers have been moved to `knowledge/prototypes/mcp-servers/` to maintain repository hygiene.

---

_Last Updated: March 2026 — MCP Consolidation complete_
