# MCPC — Canonical MCP Orchestrator

MCPC is the **single canonical MCP server** for the EventRelay platform. It consolidates functionality that was previously spread across 8 separate repositories into one unified TypeScript package.

## Consolidated Sources

| Origin Repo | Feature | MCPC Location |
|---|---|---|
| MCPC (canonical) | Server infrastructure | `src/index.ts` |
| MCP_ROUND_TABLE | Multi-agent round-table discussion | `src/tools/round_table.ts` |
| Mcpcserver | Server infrastructure (JS) | merged into `src/index.ts` |
| mcp-tools-extension | Tool registry & chaining | `src/tools/tool_manager.ts` |
| shared-state | Cross-agent state continuity | `src/tools/shared_state.ts` |
| MCP_IOS | Mobile platforms | `platforms/ios/` _(future)_ |
| MCP-management | Archived | — |
| MESH | Archived | — |

## Architecture

```
mcp-servers/mcpc/
├── src/
│   ├── index.ts          # Main server entry — JSON-RPC 2.0 over stdio
│   ├── orchestrator.ts   # Central tool dispatch
│   └── tools/
│       ├── round_table.ts   # Multi-agent consensus
│       ├── tool_manager.ts  # Tool registry & chain execution
│       └── shared_state.ts  # Key-value cross-agent state
└── README.md
```

## Exposed Tools

| Tool | Description |
|---|---|
| `round_table` | Run a multi-agent discussion and produce a consensus answer |
| `list_tools` | List all registered MCP tools |
| `execute_tool_chain` | Execute a sequence of tools with variable binding (zero-glue) |
| `state_set` | Write a value to shared state |
| `state_get` | Read a value from shared state |
| `state_list` | List all shared state keys |
| `state_delete` | Delete a shared state key |

## Transport

JSON-RPC 2.0 over **stdio** — compatible with MCP specification `2024-11-05`.

## Usage

```bash
# Build
npm run build --workspace=@repo/mcpc

# Run as MCP server (stdio)
node mcp-servers/mcpc/dist/index.js
```

## Integration with EventRelay

EventRelay's Python backend communicates with MCPC via `src/mcp/mcpc_adapter.py`:

```python
from mcp.mcpc_adapter import MCPCAdapter

adapter = MCPCAdapter()
result = await adapter.call_tool("round_table", {
    "topic": "How should we process this video?",
    "agents": ["gemini", "claude"],
})
```

The registry entry can be found in `src/mcp/mcp_registry.json` under the key `mcpc`.
