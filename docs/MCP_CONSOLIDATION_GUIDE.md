# MCP Repository Consolidation Guide

## Overview

This guide explains how to migrate external MCP repositories into the unified EventRelay MCP orchestrator.

## Consolidated Internal Structure

EventRelay now has a unified MCP layer at `src/youtube_extension/services/mcp/`:

```
src/youtube_extension/services/mcp/
├── __init__.py          # Public API
├── orchestrator.py      # Central task coordination
├── registry.py          # Server management
├── types.py             # Type definitions
└── README.md            # Documentation
```

This consolidates functionality that was previously scattered across:
- `src/mcp/mcp_ecosystem_coordinator.py`
- `src/youtube_extension/core/mcp/server_registry.py`
- `mcp-servers/shared-state/state_coordinator.py`

## External Repositories to Migrate

### 1. MCPC (5.6MB, TypeScript) - **CANONICAL**

**Repository**: `@groupthinking/MCPC`
**Language**: TypeScript
**Size**: 5.6MB
**Status**: Keep as canonical MCP implementation

**Migration Steps**:

1. **Clone the repository**:
   ```bash
   git clone https://github.com/groupthinking/MCPC.git /tmp/MCPC
   ```

2. **Extract core MCP protocol implementation**:
   ```bash
   # Create target directory
   mkdir -p mcp-servers/mcpc-canonical

   # Copy TypeScript MCP implementation
   cp -r /tmp/MCPC/src/* mcp-servers/mcpc-canonical/
   cp /tmp/MCPC/package.json mcp-servers/mcpc-canonical/
   cp /tmp/MCPC/tsconfig.json mcp-servers/mcpc-canonical/
   ```

3. **Update package.json** to integrate with EventRelay workspace:
   ```json
   {
     "name": "@eventrelay/mcpc-canonical",
     "version": "1.0.0",
     "description": "Canonical MCP implementation for EventRelay",
     "private": true,
     "main": "dist/index.js",
     "types": "dist/index.d.ts",
     "scripts": {
       "build": "tsc",
       "dev": "tsc --watch",
       "test": "jest"
     },
     "dependencies": {
       "@modelcontextprotocol/sdk": "^1.26.0"
     }
   }
   ```

4. **Add to workspace** in root `package.json`:
   ```json
   {
     "workspaces": [
       "apps/*",
       "packages/*",
       "mcp-servers/*",
       "mcp-servers/mcpc-canonical"
     ]
   }
   ```

5. **Register server** in Python backend:
   ```python
   from youtube_extension.services.mcp import get_registry, MCPCapability

   registry = get_registry()
   registry.register_server(
       server_id="mcpc-canonical",
       name="MCPC Canonical Server",
       endpoint="http://localhost:8100",
       capabilities=[
           MCPCapability.CONTEXT_MANAGEMENT,
           MCPCapability.AI_INFERENCE,
           MCPCapability.STATE_COORDINATION
       ],
       priority=1
   )
   ```

### 2. MCP_ROUND_TABLE (2.1MB, TypeScript)

**Repository**: `@groupthinking/MCP_ROUND_TABLE`
**Language**: TypeScript
**Size**: 2.1MB

**Relevant Features**:
- Multi-agent round-robin coordination
- Consensus mechanisms
- Agent communication protocols

**Migration Strategy**:

1. **Extract coordination logic**:
   ```bash
   mkdir -p mcp-servers/round-table
   cp -r /tmp/MCP_ROUND_TABLE/coordination/* mcp-servers/round-table/
   ```

2. **Port to Python** (optional) or keep as TypeScript microservice:
   - If keeping TypeScript: Add to workspace
   - If porting: Integrate into `src/youtube_extension/services/mcp/coordination.py`

3. **Create coordination module**:
   ```python
   # src/youtube_extension/services/mcp/coordination.py
   class RoundTableCoordinator:
       """Multi-agent round-robin coordination"""

       def __init__(self, orchestrator):
           self.orchestrator = orchestrator

       async def coordinate_agents(self, agents, task):
           """Coordinate multiple agents in round-robin fashion"""
           # Implementation based on MCP_ROUND_TABLE logic
   ```

### 3. Mcpcserver (2.9MB, JavaScript)

**Repository**: `@groupthinking/Mcpcserver`
**Language**: JavaScript
**Size**: 2.9MB

**Migration Strategy**:

1. **Migrate to TypeScript** for consistency:
   ```bash
   mkdir -p mcp-servers/mcpc-js
   cp -r /tmp/Mcpcserver/* mcp-servers/mcpc-js/

   # Convert to TypeScript
   cd mcp-servers/mcpc-js
   npm install --save-dev typescript @types/node
   # Manual conversion or use ts-migrate
   ```

2. **Consolidate with MCPC canonical**:
   - Review for unique functionality
   - Merge unique features into MCPC canonical
   - Archive redundant code

### 4. MCP_IOS (6.2MB, Python)

**Repository**: `@groupthinking/MCP_IOS`
**Language**: Python
**Size**: 6.2MB

**Platform**: iOS mobile integration

**Migration Strategy**:

1. **Create platforms directory**:
   ```bash
   mkdir -p mcp-servers/platforms/ios
   cp -r /tmp/MCP_IOS/* mcp-servers/platforms/ios/
   ```

2. **Register iOS-specific capabilities**:
   ```python
   # Add to types.py
   class MCPCapability(str, Enum):
       # ... existing capabilities ...

       # iOS-specific
       IOS_NOTIFICATION = "ios_notification"
       IOS_LOCATION = "ios_location"
       IOS_CAMERA = "ios_camera"
   ```

3. **Create iOS bridge**:
   ```python
   # src/youtube_extension/services/mcp/platforms/ios.py
   class IOSBridge:
       """Bridge for iOS MCP integration"""

       async def register_ios_capabilities(self):
           """Register iOS-specific MCP servers"""
   ```

### 5. Archive Stale Repositories

**Repositories to Archive**:
- MCP-management (39KB, stale since June 2025)
- MESH (243KB, stale since June 2025)
- mcp-tools-extension (967KB, stale since July 2025)

**Archive Process**:

```bash
# Create archive directory
mkdir -p .archive/mcp-legacy

# Move stale repos
for repo in MCP-management MESH mcp-tools-extension; do
    if [ -d "/tmp/$repo" ]; then
        mv "/tmp/$repo" ".archive/mcp-legacy/$repo"
        echo "Archived: $(date)" > ".archive/mcp-legacy/$repo/ARCHIVED.txt"
    fi
done
```

## Integration Checklist

For each external repository being migrated:

- [ ] Clone external repository
- [ ] Review codebase for unique functionality
- [ ] Identify redundant code to archive
- [ ] Extract unique features
- [ ] Integrate into unified orchestrator
- [ ] Update type definitions if needed
- [ ] Register server in registry
- [ ] Add tests for new functionality
- [ ] Update documentation
- [ ] Archive original repository

## Post-Migration Validation

After migrating all repositories:

1. **Run tests**:
   ```bash
   pytest tests/unit/services/mcp/ -v
   pytest tests/integration/mcp/ -v
   ```

2. **Verify server registration**:
   ```python
   from youtube_extension.services.mcp import get_registry

   registry = get_registry()
   status = registry.get_registry_status()
   print(f"Total servers: {status['total_servers']}")
   print(f"Capabilities: {list(status['capability_coverage'].keys())}")
   ```

3. **Test task execution**:
   ```python
   from youtube_extension.services.mcp import get_orchestrator, MCPCapability

   orchestrator = get_orchestrator()
   task_id = await orchestrator.submit_task(
       task_type="test_task",
       payload={"test": "data"},
       requirements=[MCPCapability.CONTEXT_MANAGEMENT]
   )
   ```

4. **Check metrics**:
   ```python
   status = orchestrator.get_orchestrator_status()
   print(f"Active tasks: {status['active_tasks']}")
   print(f"Metrics: {status['metrics']}")
   ```

## Troubleshooting

### Import Errors

If you encounter import errors after migration:

```python
# Ensure PYTHONPATH includes EventRelay root
export PYTHONPATH=/path/to/EventRelay:$PYTHONPATH

# Or use editable install
pip install -e .
```

### TypeScript Compilation Errors

```bash
# Install dependencies
npm install

# Build TypeScript
turbo run build

# Or specific package
cd mcp-servers/mcpc-canonical && npm run build
```

### Server Registration Issues

If servers don't appear in registry:

```python
# Check registry status
from youtube_extension.services.mcp import get_registry

registry = get_registry()
print(registry.get_registry_status())

# Manually register if needed
registry.register_server(...)
```

## Next Steps

1. **Port remaining MCP functionality** from old locations
2. **Deprecate old MCP code** once migration is complete
3. **Update all imports** to use unified orchestrator
4. **Add comprehensive tests** for all migrated functionality
5. **Document API changes** for external consumers

## Resources

- [MCP Specification](https://modelcontextprotocol.io/docs)
- [EventRelay MCP README](../../../src/youtube_extension/services/mcp/README.md)
- [Architecture Documentation](../../../CLAUDE.md)
