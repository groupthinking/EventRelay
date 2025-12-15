## Minimal Deep MCP Agent

This guide shows how to run the example agent at `examples/minimal_deep_mcp_agent.py`.

### Setup

The repository already includes a prepared virtual environment at `/workspace/.venv`.

Activate it:

```bash
source /workspace/.venv/bin/activate
```

Or call Python directly:

```bash
/workspace/.venv/bin/python --version
```

### Dry Run (no LLM call)

```bash
/workspace/.venv/bin/python examples/minimal_deep_mcp_agent.py --dry-run "What tools are available?"
```

### List Tools

```bash
/workspace/.venv/bin/python examples/minimal_deep_mcp_agent.py --list-tools --dry-run
```

### Run with Anthropic

Requires `ANTHROPIC_API_KEY`:

```bash
ANTHROPIC_API_KEY=sk-... /workspace/.venv/bin/python examples/minimal_deep_mcp_agent.py "Plan a short task using tools"
```

### Run with OpenAI

Requires `OPENAI_API_KEY` and `langchain_openai` package:

```bash
/workspace/.venv/bin/python -m pip install langchain_openai
OPENAI_API_KEY=sk-... MODEL="openai:gpt-4o-mini" /workspace/.venv/bin/python examples/minimal_deep_mcp_agent.py "Hello"
```

### Configure MCP Servers

- HTTP/SSE (FastMCP):
  - `MCP_HTTP_URL` (e.g., `http://localhost:8000/mcp`)
  - `MCP_HTTP_TRANSPORT` (optional: `sse` | `http` | `streamable-http`; default `sse`)

- stdio server:
  - `MCP_STDIO_COMMAND` (binary or script path)
  - `MCP_STDIO_ARGS` (optional; space-separated args)

Examples:

```bash
# HTTP/SSE FastMCP server
MCP_HTTP_URL=http://localhost:8000/mcp MCP_HTTP_TRANSPORT=sse \
ANTHROPIC_API_KEY=sk-... /workspace/.venv/bin/python examples/minimal_deep_mcp_agent.py "Use tools to fetch info"

# stdio server
MCP_STDIO_COMMAND="/path/to/mcp-server" MCP_STDIO_ARGS="--flag value" \
ANTHROPIC_API_KEY=sk-... /workspace/.venv/bin/python examples/minimal_deep_mcp_agent.py "Do something with stdio tools"
```

