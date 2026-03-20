"""
MCP Orchestrator Dependency Injection

Provides FastAPI dependencies for accessing the MCP orchestrator.
"""

from typing import Annotated

from fastapi import Depends

from ..containers.service_container import get_service_container


def get_mcp_orchestrator_service():
    """
    Dependency to get the MCP orchestrator service.

    Returns:
        MCPOrchestrator instance
    """
    container = get_service_container()
    return container.get_service("mcp_orchestrator")


def get_mcp_registry_service():
    """
    Dependency to get the MCP server registry.

    Returns:
        MCPServerRegistry instance
    """
    from ...services.mcp import get_registry

    return get_registry()


# Type annotations for dependency injection
MCPOrchestratorDep = Annotated[object, Depends(get_mcp_orchestrator_service)]
MCPRegistryDep = Annotated[object, Depends(get_mcp_registry_service)]
