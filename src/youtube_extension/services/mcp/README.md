# MCP Unified Orchestrator

## Overview

The MCP (Model Context Protocol) Unified Orchestrator consolidates scattered MCP functionality across EventRelay into a single, cohesive system that provides protocol-first composability with zero manual glue code.

## Architecture

```
EventRelay MCP Architecture
├── Core Layer (src/youtube_extension/services/mcp/)
│   ├── orchestrator.py      # Central coordination and task execution
│   ├── registry.py           # Server management and discovery
│   ├── types.py              # Unified type definitions
│   └── __init__.py           # Public API
│
├── Foundation Layer (src/youtube_extension/core/mcp/)
│   ├── context_manager.py    # Context lifecycle management
│   ├── server_registry.py    # Legacy server registry (deprecated)
│   ├── protocol_bridge.py    # External protocol integration
│   └── validation.py         # Context validation
│
├── MCP Servers (mcp-servers/)
│   ├── litert-mcp/           # LiteRT model inference
│   ├── shared-state/         # Cross-server state coordination
│   └── lib/                  # Shared libraries
│
└── Integration Points
    ├── backend/api/v1/        # REST API endpoints
    ├── backend/services/      # Service layer integration
    └── services/workflows/    # Workflow integration
```

## Key Features

### 1. Unified Orchestration
- **Single coordination point** for all MCP operations
- **Intelligent task routing** based on server capabilities and load
- **Dependency management** for complex workflows
- **Load balancing** across available servers

### 2. Server Management
- **Dynamic registration** and discovery
- **Health monitoring** with automatic recovery
- **Capability-based routing** to appropriate servers
- **Performance tracking** and optimization

### 3. Protocol-First Design
- **Zero manual glue code** - servers compose automatically
- **Type-safe** operations with Pydantic models
- **Async-first** architecture for high performance
- **Extensible** - easy to add new server types

## Usage

### Basic Task Submission

```python
from youtube_extension.services.mcp import get_orchestrator, MCPCapability

# Get orchestrator instance
orchestrator = get_orchestrator()

# Submit a video processing task
task_id = await orchestrator.submit_task(
    task_type="video_transcription",
    payload={"video_url": "https://youtube.com/watch?v=..."},
    requirements=[
        MCPCapability.VIDEO_TRANSCRIPTION,
        MCPCapability.AI_INFERENCE
    ],
    priority=1,  # Critical task
    timeout=300
)

# Check task status
task = await orchestrator.get_task_status(task_id)
print(f"Task status: {task.status}")
```

### Server Registration

```python
from youtube_extension.services.mcp import get_registry, MCPCapability

# Get registry instance
registry = get_registry()

# Register a new MCP server
config = registry.register_server(
    server_id="video-processor-01",
    name="Video Processing Server",
    endpoint="http://localhost:8010",
    capabilities=[
        MCPCapability.VIDEO_PROCESSING,
        MCPCapability.VIDEO_TRANSCRIPTION,
        MCPCapability.AI_INFERENCE
    ],
    priority=1,  # Critical server
    max_concurrent_tasks=10
)

# Start health monitoring
await registry.start_monitoring()
```

### Finding Servers by Capability

```python
from youtube_extension.services.mcp import get_registry, MCPCapability

registry = get_registry()

# Find all servers capable of video analysis
servers = registry.find_servers_by_capability(
    MCPCapability.VIDEO_ANALYSIS,
    status_filter=ServerStatus.ONLINE
)

for config, state in servers:
    print(f"{config.name}: load={state.load_factor:.2f}")
```

## Consolidation Strategy

### Phase 1: Internal Consolidation (Current)

The unified orchestrator consolidates functionality from:

1. **`src/mcp/mcp_ecosystem_coordinator.py`**
   - Task routing logic
   - Load balancing
   - Performance monitoring

2. **`src/youtube_extension/core/mcp/server_registry.py`**
   - Server registration
   - Capability indexing
   - Health checking

3. **`mcp-servers/shared-state/state_coordinator.py`**
   - Cross-server communication
   - State management
   - WebSocket coordination

### Phase 2: External Integration (Future)

External MCP repositories that should be integrated:

1. **MCPC (5.6MB, TypeScript)** - Keep as canonical
   - Port relevant features into unified orchestrator
   - Maintain TypeScript implementation for Node.js compatibility

2. **MCP_ROUND_TABLE (2.1MB, TypeScript)**
   - Extract multi-agent coordination features
   - Integrate round-robin and consensus mechanisms

3. **Mcpcserver (2.9MB, JavaScript)**
   - Consolidate server implementations
   - Migrate to unified architecture

4. **MCP_IOS (6.2MB, Python)**
   - Move to `mcp-servers/platforms/ios/`
   - Integrate mobile-specific capabilities

5. **Archive (Stale Repos)**
   - MCP-management (39KB, stale since June 2025)
   - MESH (243KB, stale since June 2025)
   - mcp-tools-extension (967KB, stale since July 2025)

## API Reference

### MCPOrchestrator

Main orchestration class for task coordination.

**Methods:**
- `submit_task()` - Submit a task for execution
- `get_task_status()` - Get current task status
- `cancel_task()` - Cancel a pending/executing task
- `execute_task()` - Execute a specific task
- `start_orchestration()` - Start orchestration loop
- `stop_orchestration()` - Stop orchestration loop
- `get_orchestrator_status()` - Get comprehensive status

### MCPServerRegistry

Server management and discovery.

**Methods:**
- `register_server()` - Register a new MCP server
- `unregister_server()` - Remove a server
- `get_server()` - Get server configuration
- `get_server_state()` - Get server runtime state
- `find_servers_by_capability()` - Find servers by capability
- `get_best_server_for_task()` - Find optimal server for task
- `check_server_health()` - Check server health
- `start_monitoring()` - Start health monitoring
- `stop_monitoring()` - Stop health monitoring

## Configuration

### Server Configuration

Servers are configured via `MCPServerConfig`:

```python
{
    "id": "unique-server-id",
    "name": "Human Readable Name",
    "endpoint": "http://localhost:8000",
    "capabilities": ["VIDEO_PROCESSING", "AI_INFERENCE"],
    "protocol": "http",
    "port": 8000,
    "priority": 1,  # 1=critical, 5=low
    "max_concurrent_tasks": 10,
    "health_check_interval": 30,
    "timeout": 30
}
```

### Environment Variables

- `MCP_REGISTRY_PATH` - Path to server registry config (default: `./.runtime/mcp_servers.json`)
- `MCP_CONTEXT_PATH` - Path to context storage (default: `./data/mcp_contexts/`)
- `MCP_MONITORING_INTERVAL` - Health check interval in seconds (default: 30)

## Migration Guide

### Migrating from Old MCP Code

#### 1. Replace old registry imports

**Before:**
```python
from youtube_extension.core.mcp.server_registry import get_server_registry
registry = get_server_registry()
```

**After:**
```python
from youtube_extension.services.mcp import get_registry
registry = get_registry()
```

#### 2. Update capability enums

**Before:**
```python
from youtube_extension.core.mcp.server_registry import ServerCapability
capability = ServerCapability.AI_INFERENCE
```

**After:**
```python
from youtube_extension.services.mcp import MCPCapability
capability = MCPCapability.AI_INFERENCE
```

#### 3. Use unified orchestrator for tasks

**Before:**
```python
from src.mcp.mcp_ecosystem_coordinator import MCPEcosystemCoordinator
coordinator = MCPEcosystemCoordinator()
task_id = coordinator.submit_task(...)
```

**After:**
```python
from youtube_extension.services.mcp import get_orchestrator
orchestrator = get_orchestrator()
task_id = await orchestrator.submit_task(...)
```

## Testing

### Unit Tests

```bash
# Run MCP orchestrator tests
pytest tests/unit/services/mcp/test_orchestrator.py -v

# Run registry tests
pytest tests/unit/services/mcp/test_registry.py -v

# Run all MCP tests
pytest tests/unit/services/mcp/ -v
```

### Integration Tests

```bash
# Run full MCP integration tests
pytest tests/integration/mcp/ -v --slow
```

## Performance

The unified orchestrator is designed for high performance:

- **Async-first**: All operations are async for non-blocking execution
- **Connection pooling**: Reuses HTTP connections to servers
- **Smart caching**: Caches server states and task results
- **Load balancing**: Distributes tasks based on server load and performance
- **Health monitoring**: Automatically removes unhealthy servers from rotation

## Troubleshooting

### Server Not Found

If a server cannot be found for a task:
1. Check server registration: `registry.get_registry_status()`
2. Verify server capabilities match task requirements
3. Ensure at least one server is ONLINE
4. Check server health: `await registry.check_server_health(server_id)`

### Task Stuck in Pending

If a task remains in PENDING status:
1. Check task dependencies: `task.dependencies`
2. Verify all dependency tasks completed successfully
3. Ensure orchestration loop is running: `await orchestrator.start_orchestration()`

### High Error Rate

If servers show high error rates:
1. Check server logs for errors
2. Verify server endpoint is accessible
3. Review server health check failures
4. Consider increasing timeout values

## Contributing

When adding new MCP functionality:

1. **Add capabilities** to `MCPCapability` enum in `types.py`
2. **Register servers** with new capabilities in registry
3. **Update tests** to cover new functionality
4. **Document** new features in this README

## References

- [Model Context Protocol Specification](https://modelcontextprotocol.io/docs)
- [EventRelay Architecture](../../README.md)
- [MCP Server Implementation Guide](../../../mcp-servers/README.md)
