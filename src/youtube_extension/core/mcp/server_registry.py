"""
MCP Server Registry - Server Management and Discovery

This module provides the MCP server registry system for managing connections
to MCP-compatible servers and services across the UVAI system.

Key Responsibilities:
- Server registration and discovery
- Connection management and health monitoring
- Server capability tracking
- Load balancing and failover
- Server configuration management
"""

import asyncio
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Protocol
from dataclasses import dataclass, field
from enum import Enum
import aiohttp
import hashlib

from pydantic import BaseModel, Field, validator

# Configure logging
logger = logging.getLogger(__name__)


class ServerStatus(Enum):
    """MCP Server Status Enumeration"""

    ONLINE = "online"
    OFFLINE = "offline"
    MAINTENANCE = "maintenance"
    ERROR = "error"


class ServerCapability(Enum):
    """MCP Server Capability Types"""

    CONTEXT_MANAGEMENT = "context_management"
    AI_INFERENCE = "ai_inference"
    DATA_PROCESSING = "data_processing"
    FILE_OPERATIONS = "file_operations"
    NETWORKING = "networking"
    MONITORING = "monitoring"


class MCPServer(BaseModel):
    """
    MCP Server Model - Server connection and capability information

    Represents a single MCP server with its connection details,
    capabilities, and operational status.
    """

    id: str = Field(..., description="Unique server identifier")
    name: str = Field(..., description="Human-readable server name")
    endpoint: str = Field(..., description="Server endpoint URL")
    capabilities: List[ServerCapability] = Field(
        default_factory=list, description="Server capabilities"
    )

    # Connection details
    protocol: str = Field(default="http", description="Communication protocol")
    port: Optional[int] = Field(default=8000, description="Server port")
    auth_token: Optional[str] = None

    # Operational status
    status: ServerStatus = Field(default=ServerStatus.OFFLINE)
    last_health_check: Optional[datetime] = None
    health_check_interval: int = Field(
        default=30, description="Health check interval in seconds"
    )
    response_time: Optional[float] = None

    # Metadata
    version: str = Field(default="1.0.0", description="Server version")
    description: Optional[str] = None
    tags: List[str] = Field(
        default_factory=list, description="Server tags for categorization"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional server metadata"
    )

    # System fields
    registered_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    @validator("endpoint")
    def validate_endpoint(cls, value):
        """Validate endpoint format"""
        if not value.startswith(("http://", "https://", "ws://", "wss://")):
            raise ValueError("Endpoint must be a valid HTTP/HTTPS/WebSocket URL")
        return value

    def get_full_endpoint(self) -> str:
        """Get the full endpoint URL including port if specified"""
        if self.port and self.port not in [80, 443]:
            base_url = self.endpoint.rstrip("/")
            return f"{base_url}:{self.port}"
        return self.endpoint

    def has_capability(self, capability: ServerCapability) -> bool:
        """Check if server has a specific capability"""
        return capability in self.capabilities

    def is_healthy(self) -> bool:
        """Check if server is currently healthy"""
        if self.status != ServerStatus.ONLINE:
            return False

        if not self.last_health_check:
            return False

        # Consider healthy if checked within 2x the interval
        max_age = timedelta(seconds=self.health_check_interval * 2)
        return datetime.utcnow() - self.last_health_check < max_age

    def update_status(
        self, status: ServerStatus, response_time: Optional[float] = None
    ) -> None:
        """Update server status and response time"""
        self.status = status
        self.last_health_check = datetime.utcnow()
        if response_time is not None:
            self.response_time = response_time
        self.updated_at = datetime.utcnow()


class MCPServerRegistry:
    """
    MCP Server Registry - Central server management and discovery

    Manages the registration, discovery, and health monitoring of MCP servers
    across the UVAI system, providing load balancing and failover capabilities.
    """

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the MCP Server Registry

        Args:
            config_path: Optional path for server configuration storage
        """
        self.config_path = config_path or "./config/mcp_servers.json"
        self.servers: Dict[str, MCPServer] = {}
        self.capability_index: Dict[ServerCapability, Set[str]] = {}

        # Health monitoring
        self.health_check_task: Optional[asyncio.Task] = None
        self.monitoring_active = False

        # Load existing configuration
        self._load_config()

        logger.info(f"MCP Server Registry initialized with {len(self.servers)} servers")

    async def start_monitoring(self) -> None:
        """Start the server health monitoring loop"""
        if self.monitoring_active:
            return

        self.monitoring_active = True
        self.health_check_task = asyncio.create_task(self._health_monitoring_loop())
        logger.info("MCP Server Registry monitoring started")

    async def stop_monitoring(self) -> None:
        """Stop the server health monitoring"""
        self.monitoring_active = False
        if self.health_check_task:
            self.health_check_task.cancel()
            try:
                await self.health_check_task
            except asyncio.CancelledError:
                pass
        logger.info("MCP Server Registry monitoring stopped")

    def register_server(
        self,
        id: str,
        name: str,
        endpoint: str,
        capabilities: List[ServerCapability],
        **kwargs,
    ) -> MCPServer:
        """
        Register a new MCP server

        Args:
            id: Unique server identifier
            name: Human-readable server name
            endpoint: Server endpoint URL
            capabilities: List of server capabilities
            **kwargs: Additional server configuration

        Returns:
            Registered MCPServer instance
        """
        if id in self.servers:
            raise ValueError(f"Server with ID '{id}' already registered")

        server = MCPServer(
            id=id, name=name, endpoint=endpoint, capabilities=capabilities, **kwargs
        )

        self.servers[id] = server

        # Update capability index
        for capability in capabilities:
            if capability not in self.capability_index:
                self.capability_index[capability] = set()
            self.capability_index[capability].add(id)

        # Persist configuration
        self._save_config()

        logger.info(
            f"Registered MCP server: {name} ({id}) with capabilities: {[c.value for c in capabilities]}"
        )

        return server

    def unregister_server(self, server_id: str) -> bool:
        """
        Unregister an MCP server

        Args:
            server_id: Server identifier to remove

        Returns:
            True if server was removed, False if not found
        """
        if server_id not in self.servers:
            return False

        server = self.servers[server_id]

        # Remove from capability index
        for capability in server.capabilities:
            if capability in self.capability_index:
                self.capability_index[capability].discard(server_id)
                if not self.capability_index[capability]:
                    del self.capability_index[capability]

        # Remove server
        del self.servers[server_id]

        # Persist configuration
        self._save_config()

        logger.info(f"Unregistered MCP server: {server_id}")

        return True

    def get_server(self, server_id: str) -> Optional[MCPServer]:
        """
        Get a server by ID

        Args:
            server_id: Server identifier

        Returns:
            MCPServer if found, None otherwise
        """
        return self.servers.get(server_id)

    def find_servers_by_capability(
        self,
        capability: ServerCapability,
        status_filter: Optional[ServerStatus] = ServerStatus.ONLINE,
    ) -> List[MCPServer]:
        """
        Find servers by capability

        Args:
            capability: Required server capability
            status_filter: Optional status filter (default: ONLINE only)

        Returns:
            List of servers with the required capability
        """
        server_ids = self.capability_index.get(capability, set())
        servers = [self.servers[sid] for sid in server_ids if sid in self.servers]

        if status_filter:
            servers = [s for s in servers if s.status == status_filter]

        # Sort by response time (fastest first)
        servers.sort(key=lambda s: s.response_time or float("inf"))

        return servers

    def get_servers_by_status(self, status: ServerStatus) -> List[MCPServer]:
        """
        Get all servers with a specific status

        Args:
            status: Server status to filter by

        Returns:
            List of servers with the specified status
        """
        return [server for server in self.servers.values() if server.status == status]

    def get_all_servers(self) -> List[MCPServer]:
        """
        Get all registered servers

        Returns:
            List of all registered servers
        """
        return list(self.servers.values())

    async def check_server_health(self, server: MCPServer) -> bool:
        """
        Check the health of a specific server

        Args:
            server: Server to check

        Returns:
            True if server is healthy, False otherwise
        """
        try:
            start_time = time.time()

            async with aiohttp.ClientSession() as session:
                url = f"{server.get_full_endpoint()}/health"
                headers = {}

                if server.auth_token:
                    headers["Authorization"] = f"Bearer {server.auth_token}"

                async with session.get(url, headers=headers, timeout=10) as response:
                    response_time = time.time() - start_time

                    if response.status == 200:
                        server.update_status(ServerStatus.ONLINE, response_time)
                        return True
                    else:
                        server.update_status(ServerStatus.ERROR, response_time)
                        return False

        except Exception as e:
            logger.warning(f"Health check failed for server {server.id}: {e}")
            server.update_status(ServerStatus.ERROR)
            return False

    async def _health_monitoring_loop(self) -> None:
        """Background health monitoring loop"""
        while self.monitoring_active:
            try:
                # Check all servers
                tasks = []
                for server in self.servers.values():
                    # Only check servers that need health checking
                    if (
                        not server.last_health_check
                        or datetime.utcnow() - server.last_health_check
                        > timedelta(seconds=server.health_check_interval)
                    ):
                        tasks.append(self.check_server_health(server))

                if tasks:
                    await asyncio.gather(*tasks, return_exceptions=True)

                # Save updated configuration
                self._save_config()

            except Exception as e:
                logger.error(f"Health monitoring error: {e}")

            # Wait before next check
            await asyncio.sleep(10)

    def _load_config(self) -> None:
        """Load server configuration from file"""
        try:
            import os

            if not os.path.exists(self.config_path):
                return

            with open(self.config_path, "r") as f:
                data = json.load(f)

            for server_data in data.get("servers", []):
                try:
                    # Convert string capabilities back to enum
                    capabilities = []
                    for cap_str in server_data.get("capabilities", []):
                        try:
                            capabilities.append(ServerCapability(cap_str))
                        except ValueError:
                            logger.warning(f"Unknown capability: {cap_str}")

                    # Convert string status back to enum
                    status_str = server_data.get("status", "offline")
                    try:
                        status = ServerStatus(status_str)
                    except ValueError:
                        status = ServerStatus.OFFLINE

                    server = MCPServer(
                        **{
                            k: v
                            for k, v in server_data.items()
                            if k not in ["capabilities", "status"]
                        },
                        capabilities=capabilities,
                        status=status,
                    )

                    self.servers[server.id] = server

                    # Update capability index
                    for capability in server.capabilities:
                        if capability not in self.capability_index:
                            self.capability_index[capability] = set()
                        self.capability_index[capability].add(server.id)

                except Exception as e:
                    logger.error(f"Failed to load server config: {e}")

        except Exception as e:
            logger.error(f"Failed to load server registry config: {e}")

    def _save_config(self) -> None:
        """Save server configuration to file"""
        try:
            import os

            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)

            data = {
                "servers": [
                    {
                        **server.dict(),
                        "capabilities": [c.value for c in server.capabilities],
                        "status": server.status.value,
                    }
                    for server in self.servers.values()
                ],
                "last_updated": datetime.utcnow().isoformat(),
            }

            with open(self.config_path, "w") as f:
                json.dump(data, f, indent=2, default=str)

        except Exception as e:
            logger.error(f"Failed to save server registry config: {e}")


# Global server registry instance
_server_registry = None


def get_server_registry() -> MCPServerRegistry:
    """Get the global MCP server registry instance"""
    global _server_registry
    if _server_registry is None:
        _server_registry = MCPServerRegistry()
    return _server_registry


async def register_ai_server(
    name: str, endpoint: str, capabilities: List[ServerCapability]
) -> MCPServer:
    """Convenience function to register an AI server"""
    server_id = f"ai-{name.lower().replace(' ', '-')}-{hashlib.md5(endpoint.encode()).hexdigest()[:8]}"
    return get_server_registry().register_server(
        id=server_id, name=name, endpoint=endpoint, capabilities=capabilities
    )


def find_ai_servers(capability: ServerCapability) -> List[MCPServer]:
    """Convenience function to find AI servers by capability"""
    return get_server_registry().find_servers_by_capability(capability)
