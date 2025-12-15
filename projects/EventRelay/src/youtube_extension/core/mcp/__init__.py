"""
MCP (Model Context Protocol) Foundation Layer

This module provides the universal AI integration layer for structured context sharing
across all components of the UVAI YouTube Extension system.

Key Features:
- Structured context management and validation
- MCP server registry and discovery
- Protocol bridging for external AI services
- Context persistence and recovery
- Cross-component communication

Architecture:
- Context Manager: Handles MCP context lifecycle
- Server Registry: Manages MCP server connections
- Protocol Bridge: Integrates with external protocols
- Validation: Ensures context integrity
"""

from .context_manager import MCPContextManager, MCPContext
from .server_registry import MCPServerRegistry, MCPServer
from .protocol_bridge import MCPProtocolBridge
from .validation import MCPValidator, ContextValidationError

__all__ = [
    "MCPContextManager",
    "MCPContext",
    "MCPServerRegistry",
    "MCPServer",
    "MCPProtocolBridge",
    "MCPValidator",
    "ContextValidationError"
]
