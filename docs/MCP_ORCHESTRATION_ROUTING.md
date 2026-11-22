# MCP routing clarity (AUDIT-009)

## Layers

| Component | Role |
| --- | --- |
| `src/youtube_extension/core/mcp/server_registry.py` | MCP server registration and discovery |
| `src/youtube_extension/core/mcp/protocol_bridge.py` | Protocol translation for external services |
| `src/youtube_extension/core/mcp/context_manager.py` | MCP context lifecycle |
| `mcp-servers/` | Standalone MCP servers (`langextract`, `vercel`) |
| `tools/mcp/` | Repository tooling servers |

`src/youtube_extension/services/mcp/` and `src/mcp/` are not in this tree.

## Routing rule

External MCP clients use `mcp-servers/` or hosted MCP endpoints. In-process server discovery goes through `src/youtube_extension/core/mcp/`.
