# MCPC Unified MCP Server

Canonical MCP orchestrator that replaces the scattered MCP repositories with a single entry point for EventRelay.

## What Changed
- **Canonicalized** MCPC as the only MCP server entry point.
- **Ported features** from `MCP_ROUND_TABLE` and `Mcpcserver` into unified capabilities.
- **Mobile** assets from `MCP_IOS` live under `platforms/ios/`.
- **Archived** stale repos: `MCP_ROUND_TABLE`, `MCP-CORE`, `MCP-management`, `MESH`, `mcp-tools-extension`.

## Running
```bash
python3 mcp-servers/mcpc/server.py
```

The server speaks MCP over stdio and exposes tools for:
- Consolidated status/metadata (`mcpc_status`)
- Task routing across merged capabilities (`route_task`)
- iOS hand-off metadata (`ios_handoff`)

## Integration
EventRelay consumes this server via `src/mcp/mcp_registry.json`, which now points to this single MCPC entry. Tooling that previously referenced other MCP repos should point here instead.
