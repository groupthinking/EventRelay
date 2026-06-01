"""
MCP (Model Context Protocol) Services - Unified Orchestrator

This module provides the unified MCP orchestration layer for EventRelay,
consolidating scattered MCP functionality into a single, cohesive system.

Architecture:
- Unified Orchestrator: Central coordination point for all MCP operations
- Server Registry: Manages MCP server connections and discovery
- Shared Types: Common configuration, capability, and task models

The orchestrator and registry together handle context lifecycle and sharing,
protocol integration with external systems, and cross-server state management.

Key Features:
- Protocol-first composability with zero manual glue code
- Intelligent task routing and load balancing
- Health monitoring and auto-recovery
- Type-safe operations with Pydantic models
"""

from .orchestrator import MCPOrchestrator, get_orchestrator
from .registry import MCPServerRegistry, get_registry
from .types import (
    MCPCapability,
    MCPServerConfig,
    MCPTask,
    MCPTaskStatus,
    ServerStatus,
)

__all__ = [
    "MCPOrchestrator",
    "get_orchestrator",
    "MCPServerRegistry",
    "get_registry",
    "MCPCapability",
    "MCPServerConfig",
    "MCPTask",
    "MCPTaskStatus",
    "ServerStatus",
]
