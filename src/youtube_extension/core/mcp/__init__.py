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

from .context_manager import MCPContext, MCPContextManager
from .protocol_bridge import MCPProtocolBridge
from .server_registry import MCPServer, MCPServerRegistry
from .validation import ContextValidationError, MCPValidator

__all__ = [
    "MCPContextManager",
    "MCPContext",
    "MCPServerRegistry",
    "MCPServer",
    "MCPProtocolBridge",
    "MCPValidator",
    "ContextValidationError"
]
