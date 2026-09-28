# MCP routing clarity (AUDIT-009)

## Layers

| Component | Role |
| --- | --- |
| `src/youtube_extension/services/mcp/registry.py` | Tool catalog and registration |
| `src/youtube_extension/services/mcp/orchestrator.py` | Backend dispatch into registered tools |
| `src/mcp/` + `mcp-servers/` | Standalone MCP servers for IDE/agent integrations |

## Routing rule

External MCP clients hit **mcp-servers** or hosted MCP endpoints. The FastAPI backend uses **registry → orchestrator** for in-process tool calls. Do not bypass the registry from API routes.

## Debugging

Enable structured logs on orchestrator entry (`tool_name`, `request_id`); registry misses should fail closed with 404, not silent fallback.
