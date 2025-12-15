# MCP Server Configuration for EventRelay

This document describes the Model Context Protocol (MCP) server configuration for the EventRelay project.

## MCP Servers Available

### 1. Self-Correcting Executor MCP Server
**Purpose**: Provides code analysis, protocol validation, and self-correction capabilities.

**Location**: `development/agents/mcp_ecosystem_coordinator.py`

**Available Tools**:
- `code_analyzer`: AST-based code analysis with complexity metrics
- `protocol_validator`: MCP protocol compliance validation
- `self_corrector`: Code issue detection and correction suggestions

**Configuration**:
```json
{
  "mcpServers": {
    "self-correcting-executor": {
      "command": "python",
      "args": [
        "-m",
        "development.agents.mcp_ecosystem_coordinator"
      ],
      "env": {
        "PYTHONPATH": "${workspaceFolder}",
        "MCP_TIMEOUT": "300",
        "MCP_MAX_CONCURRENT": "5"
      }
    }
  }
}
```

### 2. YouTube MCP Server
**Purpose**: YouTube video data extraction and processing.

**Location**: `mcp_youtube-0.2.0/mcp_youtube.py`

**Available Tools**:
- YouTube video metadata extraction
- Transcript fetching
- Video analysis

**Configuration**:
```json
{
  "mcpServers": {
    "youtube": {
      "command": "python",
      "args": [
        "mcp_youtube-0.2.0/mcp_youtube.py"
      ],
      "env": {
        "PYTHONPATH": "${workspaceFolder}",
        "YOUTUBE_API_KEY": "${env:YOUTUBE_API_KEY}"
      }
    }
  }
}
```

### 3. GitHub MCP Server
**Purpose**: Manage GitHub repository data (issues, pull requests, metadata) directly through MCP-aware tools.

**Package**: `@modelcontextprotocol/server-github`

**Configuration**:
```json
{
  "mcpServers": {
    "github": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-github"
      ],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "${env:GITHUB_PERSONAL_ACCESS_TOKEN}"
      }
    }
  }
}
```

### 4. Git Workflow MCP Server (Local Git Automation)
**Purpose**: Safely run `git status/add/commit/pull/push` via MCP so agents can manage repository state without direct shell access.

**Location**: `tools/mcp/git_workflow_server.mjs`

**Configuration**:
```json
{
  "mcpServers": {
    "git-workflow": {
      "command": "node",
      "args": [
        "${workspaceFolder}/tools/mcp/git_workflow_server.mjs"
      ],
      "env": {
        "GIT_WORKSPACE_ROOT": "${workspaceFolder}",
        "GIT_DEFAULT_REMOTE": "origin"
      }
    }
  }
}
```

**Tools exposed**:
- `git_status` – porcelain status snapshot
- `git_diff` – unstaged or staged diff preview
- `git_add` – stage explicit files or directories
- `git_commit` – commit staged changes with a message
- `git_pull` / `git_push` – sync with the configured remote (defaults to `origin`)

## Environment Variables

Create a `.env` file with the following variables:

```bash
# MCP Configuration
MCP_TIMEOUT=300
MCP_MAX_CONCURRENT=5
MCP_RETRY_ATTEMPTS=3
MCP_BATCH_SIZE=3
MCP_ENABLE_CIRCUIT_BREAKER=true

# API Keys
YOUTUBE_API_KEY=your_youtube_api_key
GEMINI_API_KEY=your_gemini_api_key
OPENAI_API_KEY=your_openai_api_key

# GitHub (used by server-github)
GITHUB_PERSONAL_ACCESS_TOKEN=your_github_pat  # use the same PAT as GITHUB_TOKEN with repo scope

# Git Automation (git-workflow MCP)
GIT_WORKSPACE_ROOT=/Users/garvey/Dev/OpenAI_Hub/projects/EventRelay
GIT_DEFAULT_REMOTE=origin

# Google Cloud (for Speech-to-Text)
GOOGLE_SPEECH_PROJECT_ID=your_project_id
GOOGLE_SPEECH_LOCATION=us-central1
GOOGLE_SPEECH_RECOGNIZER=transcript-recognizer
GOOGLE_SPEECH_GCS_BUCKET=your_gcs_bucket
```

## Using MCP Servers

### With GitHub Copilot
GitHub Copilot can use MCP servers to enhance its capabilities. Configure by adding the above JSON configuration to your workspace settings.

### With Cursor
Place MCP configuration in `.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "self-correcting-executor": {
      "command": "python",
      "args": ["-m", "development.agents.mcp_ecosystem_coordinator"]
    },
    "youtube": {
      "command": "python",
      "args": ["mcp_youtube-0.2.0/mcp_youtube.py"]
    },
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"]
    },
    "git-workflow": {
      "command": "node",
      "args": ["${workspaceFolder}/tools/mcp/git_workflow_server.mjs"]
    }
  }
}
```

### Programmatically
Use the MCP client in Python:

```python
from mcp import MCPClient

# Initialize client
client = MCPClient(server_url="stdio://")

# Call a tool
result = await client.call_tool(
    "code_analyzer",
    {
        "code": "def hello(): return 'world'",
        "language": "python"
    }
)
```

## Testing MCP Servers

Run the test script to verify MCP server functionality:

```bash
python scripts/mcp_performance_monitor.py
```

## Troubleshooting

### Common Issues

**Issue**: MCP server not responding
**Solution**: Check environment variables are set correctly, verify Python path

**Issue**: Tool not found
**Solution**: Ensure server is initialized correctly, check tool name spelling

**Issue**: Timeout errors
**Solution**: Increase `MCP_TIMEOUT` value in environment variables

### Debug Mode

Enable debug logging:

```bash
export MCP_DEBUG=true
export LOG_LEVEL=DEBUG
```

## Best Practices

1. **Error Handling**: Always handle MCP errors gracefully with fallbacks
2. **Timeouts**: Set appropriate timeouts based on tool complexity
3. **Resource Limits**: Use `MCP_MAX_CONCURRENT` to prevent resource exhaustion
4. **Validation**: Always validate tool inputs before sending to MCP server
5. **Logging**: Enable comprehensive logging for debugging

## MCP Protocol Compliance

All MCP servers in this project follow:
- **JSON-RPC 2.0** protocol specification
- **MCP Protocol** version 2024-11-05
- Proper error codes and messages
- Schema validation for all tool inputs/outputs

## Security Considerations

1. **API Keys**: Never hardcode API keys, use environment variables
2. **Input Validation**: All tool inputs are validated before processing
3. **Context Isolation**: MCP servers maintain separate contexts to prevent leakage
4. **Rate Limiting**: Implement rate limiting for external API calls
5. **Error Information**: Avoid exposing sensitive information in error messages

## Performance Metrics

Target performance for MCP operations:
- **Tool Call Latency**: <200ms for analysis tools
- **Throughput**: Handle 5+ concurrent requests
- **Error Rate**: <0.1%
- **Availability**: 99.9% uptime

## Future Enhancements

Planned MCP server additions:
- [ ] Code generation MCP server
- [ ] Multi-modal analysis server
- [ ] RAG integration server
- [ ] A2A orchestration server
- [ ] Deployment automation server

## References

- [MCP Protocol Specification](https://modelcontextprotocol.io/docs)
- [JSON-RPC 2.0 Specification](https://www.jsonrpc.org/specification)
- [EventRelay MCP Documentation](../development/agents/tasks/FIX_MCP_NOW.md)
