# MCP Servers Ecosystem

This directory contains the Model Context Protocol (MCP) servers used in the EventRelay (UVAI) ecosystem.

## Core Python Suite (`python-suite/`)

The primary intelligence suite for video processing and code analysis.

| Server                             | Description                 | Key Tools                                             |
| ---------------------------------- | --------------------------- | ----------------------------------------------------- |
| `youtube_uvai_mcp.py`              | Primary UVAI Processor      | `process_video`, `get_transcript`, `ai_reasoning`     |
| `video_agent_server.py`            | Video Pipeline Orchestrator | `transcribe_media`, `generate_actions`                |
| `code_analysis_server.py`          | Automated Code Review       | `scan_security`, `analyze_performance`, `check_style` |
| `cloudflare_server.py`             | Cloudflare Gateway Proxy    | `get_gateway_url`                                     |
| `learning_analytics_mcp_server.py` | Analytics Engine            | `get_learning_stats`, `track_event`                   |

## Specialized Servers

- **`gcp-vector-db/`**: Integration with Google Cloud SQL for RAG capabilities.
- **`genkit-wrapper/`**: Firebase Genkit integration for model orchestration.
- **`puppeteer-server/`**: Browser automation and web scraping.
- **`metacognition-tools/`**: Advanced reasoning tools (Fermi estimation, Red Teaming).
- **`mcp-profiling/`**: Internal performance profiling and verification.
- **`unified-analytics/`**: sophisticated metrics collection and graph analysis engine.

## External Active Servers

The following are external or JS-based servers utilized by the system:

- **`grok-server/`**: xAI Grok integration.
- **`perplexity-mcp/`**: Perplexity AI search.
- **`github/`**: Custom GitHub integration.

## Central Coordination

The ecosystem uses a **State Coordinator** for cross-MCP communication and distributed continuity:

- **State Coordinator**: manages current server status and task orchestration.
- **Continuity Fabric** (`shared-state/fabric.py`): The unique value proposition enabling cross-device and cross-application state continuity via vector clocks.
- **Database**: `shared-state/mcp_state.db`

## Maintenance & Archiving

Redundant or prototype versions of these servers have been moved to `knowledge/prototypes/mcp-servers/` to maintain repository hygiene.

---

_Last Updated: January 9, 2026_
