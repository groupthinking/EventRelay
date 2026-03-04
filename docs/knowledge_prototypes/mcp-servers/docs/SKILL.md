# MCP Server Setup & Configuration Skill

## Description
Rapid scaffolding and configuration of Model Context Protocol (MCP) servers with best practices for the UVAI ecosystem integration.

## When to Use This Skill
- Creating new MCP servers for service integration
- Configuring existing MCP servers
- Debugging MCP connection issues
- Adding MCP servers to Claude Code configuration
- Extending UVAI ecosystem with new capabilities

## MCP Architecture Principles

### Protocol-Compliant Design
- All tools follow MCP specification
- Proper resource management and lifecycle
- Error handling with descriptive messages
- Logging for debugging and monitoring

### UVAI Integration Requirements
- Event emission for data → action pipelines
- Sequential-thinking integration for orchestration
- Files API for persistent state management
- Code execution verification before deployment

## Setup Workflow

### Phase 1: Project Initialization
```bash
# Create MCP server project
mkdir -p ~/mcp-servers/[server-name]
cd ~/mcp-servers/[server-name]

# Initialize with TypeScript or Python
npm init -y && npm install @modelcontextprotocol/sdk
# OR
uv init && uv add mcp
```

### Phase 2: Server Implementation
```typescript
// TypeScript MCP Server Template
import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";

const server = new Server(
  {
    name: "server-name",
    version: "1.0.0",
  },
  {
    capabilities: {
      tools: {},
      resources: {},
    },
  }
);

// Add tools, resources, prompts
server.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: [/* tool definitions */]
}));

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  // Tool implementation
});

// Start server
const transport = new StdioServerTransport();
await server.connect(transport);
```

### Phase 3: Claude Code Configuration
```json
// Add to ~/.claude/config/mcp.json or claude_desktop_config.json
{
  "mcpServers": {
    "server-name": {
      "command": "node",
      "args": ["/Users/garvey/mcp-servers/server-name/build/index.js"],
      "env": {
        "API_KEY": "from-master-file"
      }
    }
  }
}
```

### Phase 4: Testing & Verification
```bash
# Test server directly
node build/index.js

# Verify MCP connection
# Use sequential-thinking to analyze connection status
# Use code execution to test tool invocation
# Check logs for errors
```

## Common MCP Server Types

### API Integration Server
**Purpose**: Connect external APIs to UVAI ecosystem
**Tools**: fetch_data, post_data, stream_events
**Resources**: api_endpoints, rate_limits, schemas

### Data Processing Server
**Purpose**: Transform and analyze data in pipelines
**Tools**: parse, transform, aggregate, validate
**Resources**: transformation_templates, validation_rules

### File System Server
**Purpose**: Enhanced file operations with intelligence
**Tools**: intelligent_search, semantic_organize, batch_process
**Resources**: file_indexes, metadata_stores

### Automation Server
**Purpose**: Execute workflows and orchestrate tasks
**Tools**: run_workflow, schedule_task, monitor_status
**Resources**: workflow_definitions, execution_history

## Configuration Patterns

### Environment Variables (Secure)
```json
{
  "env": {
    "API_KEY": "from-api-master-file",
    "BASE_URL": "https://api.service.com",
    "LOG_LEVEL": "info"
  }
}
```

### Command Arguments
```json
{
  "args": [
    "/path/to/server.js",
    "--config", "/path/to/config.json",
    "--verbose"
  ]
}
```

### Working Directory
```json
{
  "cwd": "/Users/garvey/mcp-servers/server-name"
}
```

## Debugging Checklist

### Connection Issues
- [ ] Server process starts without errors
- [ ] MCP configuration file syntax valid
- [ ] Command path and args correct
- [ ] Environment variables set properly
- [ ] Logs show successful initialization

### Tool Execution Issues
- [ ] Tool schema matches MCP specification
- [ ] Request handler properly registered
- [ ] Input validation working correctly
- [ ] Error handling returns proper format
- [ ] Response structure follows MCP protocol

### Performance Issues
- [ ] Tools execute within timeout limits
- [ ] Resource cleanup after operations
- [ ] Memory usage stays within bounds
- [ ] Concurrent requests handled properly
- [ ] Rate limiting implemented if needed

## Integration with UVAI Ecosystem

### Event-Driven Pipeline Integration
```typescript
// Emit events for UVAI pipeline consumption
server.notification({
  method: "notifications/uvai/event",
  params: {
    eventType: "data_captured",
    payload: data,
    timestamp: Date.now(),
    correlationId: uuid()
  }
});
```

### Self-Correcting Execution
```typescript
// Include retry logic and error recovery
async function executeWithRetry(fn, maxAttempts = 3) {
  for (let attempt = 1; attempt <= maxAttempts; attempt++) {
    try {
      return await fn();
    } catch (error) {
      if (attempt === maxAttempts) throw error;
      await sleep(Math.pow(2, attempt) * 1000);
    }
  }
}
```

### Measurement and Monitoring
```typescript
// Track performance metrics
const metrics = {
  toolCalls: 0,
  successRate: 0,
  avgLatency: 0,
  errorCount: 0
};
```

## Rapid Setup Script
```bash
#!/bin/bash
# Quick MCP server scaffolding

SERVER_NAME=$1
SERVER_PATH=~/mcp-servers/$SERVER_NAME

mkdir -p $SERVER_PATH
cd $SERVER_PATH

# Initialize TypeScript project
npm init -y
npm install @modelcontextprotocol/sdk typescript @types/node

# Create basic structure
mkdir -p src
cat > src/index.ts << 'EOF'
// MCP Server Template
// Implement your tools here
EOF

# Add build script
npx tsc --init

echo "MCP server '$SERVER_NAME' scaffolded at $SERVER_PATH"
```

## Allowed Tools
- Read, Write, Edit (for server code)
- Bash (for npm/uv commands, testing)
- sequential-thinking (for architecture planning)
- code execution (for testing server functionality)
- MCP connector (for integration testing)
- Grep, Glob (for finding configuration files)

## Success Criteria
- MCP server starts without errors
- Tools respond to MCP protocol requests
- Integration with Claude Code verified
- UVAI ecosystem compatibility confirmed
- Documentation complete with examples
- Error handling comprehensive
- Performance metrics within acceptable ranges
