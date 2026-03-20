# MCP Servers Ecosystem

Unified MCP entry points and shared infrastructure for EventRelay.

## Canonical Server (MCPC)
- **Path:** `mcp-servers/mcpc/server.py`
- **Tools:** `mcpc_status`, `route_task`, `ios_handoff`
- **Merged:** MCPC + MCP_ROUND_TABLE + Mcpcserver + MCP_IOS (mobile hand-off)
- **Archived:** MCP_ROUND_TABLE, MCP-CORE, MCP-management, MESH, mcp-tools-extension

EventRelay consumes this server via `src/mcp/mcp_registry.json`.

## Specialized Servers
- `litert-mcp/` — LiteRT-LM MCP server for local/edge inference.
- `shared-state/` — State coordinator and continuity fabric.

## Shared Libraries
- `lib/` — Shared MCP connectors, agents, and client utilities.

## Directory Map
```
mcp-servers/
├── mcpc/            # Canonical MCPC unified server (platforms/ios for mobile)
├── litert-mcp/      # LiteRT-LM MCP server
├── shared-state/    # Coordinator and state fabric
└── lib/             # Reusable connectors + agents
```
