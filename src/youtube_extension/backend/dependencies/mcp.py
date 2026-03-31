"""
MCP Orchestrator Dependency Injection

Provides FastAPI dependencies for accessing the MCP orchestrator.
"""

from typing import Annotated

from fastapi import Depends

from ..containers.service_container import get_service_container
from ...services.mcp import MCPOrchestrator, MCPServerRegistry, get_registry


def get_mcp_orchestrator_service() -> MCPOrchestrator:
    """
    Dependency to get the MCP orchestrator service.

    Returns:
        MCPOrchestrator instance
    """
    container = get_service_container()
    return container.get_service("mcp_orchestrator")  # type: ignore[return-value]


def get_mcp_registry_service() -> MCPServerRegistry:
    """
    Dependency to get the MCP server registry.

    Returns:
        MCPServerRegistry instance
    """
    return get_registry()


# Type annotations for dependency injection
MCPOrchestratorDep = Annotated[MCPOrchestrator, Depends(get_mcp_orchestrator_service)]
MCPRegistryDep = Annotated[MCPServerRegistry, Depends(get_mcp_registry_service)]
