# LiquidAI LFM2-VL MCP Server

Bridges the public [LiquidAI LFM2-VL HuggingFace Space](https://huggingface.co/spaces/LiquidAI/LFM2-VL-WebGPU) into the EventRelay MCP ecosystem so that the agent network can route tasks to LFM2-VL alongside the existing providers (Gemini, Claude, Grok, OpenAI).

## Upstream endpoints

| Purpose | URL |
|---------|-----|
| WebGPU interactive demo | https://liquidai-lfm2-vl-webgpu.static.hf.space |
| MCP server | https://liquidai-lfm2-mcp.static.hf.space |
| HuggingFace Space | https://huggingface.co/spaces/LiquidAI/LFM2-VL-WebGPU |

## Running the server

```bash
python mcp-servers/liquidai-lfm2/server.py
```

## Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `LIQUIDAI_API_KEY` | _(none)_ | Bearer token for authenticated deployments |
| `LFM2_MCP_BASE_URL` | `https://liquidai-lfm2-mcp.static.hf.space` | Override upstream URL |
| `LFM2_MAX_TOKENS` | `512` | Default max tokens for generation |

## Exposed tools

| Tool | Description |
|------|-------------|
| `generate_text` | Text generation using LFM2-VL |
| `analyze_vision` | Image understanding using LFM2-VL's vision capabilities |
| `chat_completion` | Multi-turn chat interface |

## Integration with Claude Desktop / Cursor

Add to your MCP configuration:

```json
{
  "mcpServers": {
    "liquidai-lfm2": {
      "command": "python",
      "args": ["mcp-servers/liquidai-lfm2/server.py"],
      "env": {
        "LIQUIDAI_API_KEY": "${env:LIQUIDAI_API_KEY}"
      }
    }
  }
}
```
