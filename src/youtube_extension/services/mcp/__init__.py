"""
MCP (Model Context Protocol) Services - Unified Orchestrator

This module provides the unified MCP orchestration layer for EventRelay,
consolidating scattered MCP functionality into a single, cohesive system.

Architecture:
- Unified Orchestrator: Central coordination point for all MCP operations
- Server Registry: Manages MCP server connections and discovery
- Context Manager: Handles context lifecycle and sharing
- Protocol Bridge: Integrates with external protocols
- State Coordinator: Cross-server communication and state management

Key Features:
- Protocol-first composability with zero manual glue code
- Agent-to-Agent (A2A) communication
- Cross-device state continuity
- Intelligent task routing and load balancing
- Health monitoring and auto-recovery
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
