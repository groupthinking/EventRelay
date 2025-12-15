# xAI Grok Python Wrapper

Full-featured Python client for xAI Grok API with Code Execution, Remote MCP Tools, and advanced agentic features.

## Installation

```bash
pip install httpx
```

## Quick Start

```python
from grok_client import GrokClient, code_execution, web_search

# Basic chat
client = GrokClient()  # Uses $XAI_API_KEY
response = client.chat([
    {"role": "user", "content": "Hello!"}
])
print(response.content)
```

## Understanding Tool Types

### Server-Side Tools (Auto-executed by xAI)
These tools run automatically on xAI's servers - you just enable them:

| Tool | Description |
|------|-------------|
| `web_search()` | Search the web |
| `x_search()` | Search X/Twitter |
| `code_execution()` | Run Python code |

```python
from grok_client import GrokClient, web_search, code_execution

client = GrokClient()
response = client.chat(
    messages=[{"role": "user", "content": "Search for Python best practices"}],
    tools=[web_search(), code_execution()]
)
# Tools execute automatically, response contains results
```

### Client-Side Tools (You Execute)
Custom functions that YOU must run locally:

```python
from grok_client import GrokClient, function_tool

def get_weather(city: str) -> str:
    return f"72°F in {city}"

weather_tool = function_tool(
    name="get_weather",
    description="Get weather for a city",
    parameters={
        "type": "object",
        "properties": {"city": {"type": "string"}},
        "required": ["city"]
    }
)

client = GrokClient()
response = client.chat(
    messages=[{"role": "user", "content": "Weather in NYC?"}],
    tools=[weather_tool]
)

# YOU must execute client-side tools
if response.tool_calls:
    results = client.execute_tool_calls(
        response.tool_calls,
        {"get_weather": get_weather}
    )
```

## Agentic Response Flow

```
User Message → Model decides tools → Server tools auto-execute
                                   → Client tools return to you
                                   → You execute & return results
                                   → Model continues reasoning
                                   → Repeat until done
```

### Automatic Agentic Loop

Let the client handle the entire flow:

```python
def get_stock(symbol: str) -> str:
    return "$185.50"

response = client.run_agentic_loop(
    messages=[{"role": "user", "content": "Get AAPL price and calculate 10% gain"}],
    tools=[stock_tool, code_execution()],
    functions={"get_stock": get_stock},
    max_iterations=5
)
```

### Manual Tool Type Detection

```python
response = client.chat(messages, tools=[...])
agentic = client.parse_agentic_response(response)

if agentic.requires_action:
    for call in agentic.pending_tool_calls:
        # Execute client-side tools
        ...

# Check tool type
for call in response.tool_calls:
    tool_type = client.get_tool_call_type(call)  # SERVER or CLIENT
```

## Features

### 1. Code Execution Tool (Server-side)

```python
from grok_client import GrokClient, GrokModel, code_execution

client = GrokClient(model=GrokModel.GROK_4_FAST_REASONING)
response = client.chat(
    messages=[{"role": "user", "content": "Calculate fibonacci(20)"}],
    tools=[code_execution()]
)
```

### 2. Remote MCP Tools

```python
from grok_client import GrokClient, mcp

client = GrokClient()
response = client.chat(
    messages=[{"role": "user", "content": "Analyze this repo"}],
    tools=[
        mcp(
            server_url="https://mcp.deepwiki.com/mcp",
            server_label="deepwiki",
            allowed_tools=["search", "read_file"]
        )
    ]
)
```

### 3. Streaming with Reasoning Traces

```python
for chunk in client.chat(messages=[...], stream=True):
    if chunk.reasoning_content:
        print(f"[Thinking: {chunk.reasoning_content}]")
    if chunk.content:
        print(chunk.content, end="")
```

### 4. Async Support

```python
from grok_client import AsyncGrokClient

async with AsyncGrokClient() as client:
    response = await client.chat([{"role": "user", "content": "Hi"}])
```

## Available Models

| Model | Use Case |
|-------|----------|
| `grok-code-fast-1` | Fast agentic coding (default) |
| `grok-4-fast-reasoning` | Fast with reasoning traces |
| `grok-4-0709` | Deep reasoning |
| `grok-3` | General purpose |
| `grok-2-image-1212` | Image generation |

## API Endpoints

| Endpoint | Method |
|----------|--------|
| `/v1/chat/completions` | `client.chat()` |
| `/v1/models` | `client.list_models()` |
| `/v1/embeddings` | `client.embeddings()` |
| `/v1/tokenize-text` | `client.tokenize()` |
| `/v1/image/generations` | `client.generate_image()` |

## Cache Optimization

Keep prompt history stable to maximize cache hits:

```python
# Good: Stable prefix
messages = [
    {"role": "system", "content": "..."},  # Keep constant
    {"role": "user", "content": "..."},    # Append only
]
```

## Examples

```bash
python examples.py 1     # Basic chat
python examples.py 2     # Streaming
python examples.py 3     # Code execution
python examples.py 4     # MCP tools
python examples.py 5     # Function calling
python examples.py 6     # Agentic workflow
python examples.py 7     # Hybrid tools
python examples.py 8     # Agentic loop (auto)
python examples.py 9     # Web search
python examples.py 10    # Tool type detection
python examples.py all   # Run all
```

## Environment

```bash
export XAI_API_KEY="xai-..."
```

## Resources

- [xAI Docs](https://docs.x.ai)
- [Tools Overview](https://docs.x.ai/docs/guides/tools/overview)
- [Advanced Usage](https://docs.x.ai/docs/guides/tools/advanced-usage)
- [Code Execution Tool](https://docs.x.ai/docs/guides/tools/code-execution-tool)
- [Remote MCP Tools](https://docs.x.ai/docs/guides/tools/remote-mcp-tools)
- [Function Calling](https://docs.x.ai/docs/guides/function-calling)
- [Prompt Engineering](https://docs.x.ai/docs/guides/grok-code-prompt-engineering)
