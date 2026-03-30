"""
MCP Server Registry - Unified server management

Consolidates server registration, discovery, and health monitoring across
all MCP implementations in EventRelay.
"""

import asyncio
import logging
import time
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Optional

import aiohttp

from .types import MCPCapability, MCPServerConfig, MCPServerState, ServerStatus

logger = logging.getLogger(__name__)


class MCPServerRegistry:
    """
    Unified MCP Server Registry

    Consolidates functionality from:
    - src/youtube_extension/core/mcp/server_registry.py
    - src/mcp/mcp_ecosystem_coordinator.py
    - mcp-servers/shared-state/state_coordinator.py
    """

    def __init__(self, config_path: Optional[str] = None):
        """Initialize the unified server registry"""
        self.config_path = config_path or "./.runtime/mcp_servers.json"
        self.servers: dict[str, MCPServerConfig] = {}
        self.server_states: dict[str, MCPServerState] = {}
        self.capability_index: dict[MCPCapability, set[str]] = defaultdict(set)

        # Health monitoring
        self.monitoring_active = False
        self.health_check_task: Optional[asyncio.Task] = None

        logger.info("MCP Server Registry initialized")

    def register_server(
        self,
        server_id: str,
        name: str,
        endpoint: str,
        capabilities: list[MCPCapability],
        **kwargs: Any,
    ) -> MCPServerConfig:
        """
        Register a new MCP server

        Args:
            server_id: Unique server identifier
            name: Human-readable server name
            endpoint: Server endpoint URL
            capabilities: List of server capabilities
            **kwargs: Additional server configuration

        Returns:
            Registered server configuration
        """
        if server_id in self.servers:
            logger.warning(f"Server {server_id} already registered, updating...")

        config = MCPServerConfig(
            id=server_id, name=name, endpoint=endpoint, capabilities=capabilities, **kwargs
        )

        self.servers[server_id] = config

        # Initialize server state
        self.server_states[server_id] = MCPServerState(
            server_id=server_id, status=ServerStatus.OFFLINE
        )

        # Update capability index
        for capability in capabilities:
            self.capability_index[capability].add(server_id)

        logger.info(
            f"Registered MCP server: {name} ({server_id}) with {len(capabilities)} capabilities"
        )

        return config

    def unregister_server(self, server_id: str) -> bool:
        """
        Unregister a server

        Args:
            server_id: Server identifier

        Returns:
            True if server was removed
        """
        if server_id not in self.servers:
            return False

        config = self.servers[server_id]

        # Remove from capability index
        for capability in config.capabilities:
            self.capability_index[capability].discard(server_id)
            if not self.capability_index[capability]:
                del self.capability_index[capability]

        # Remove server and state
        del self.servers[server_id]
        if server_id in self.server_states:
            del self.server_states[server_id]

        logger.info(f"Unregistered server: {server_id}")
        return True

    def get_server(self, server_id: str) -> Optional[MCPServerConfig]:
        """Get server configuration by ID"""
        return self.servers.get(server_id)

    def get_server_state(self, server_id: str) -> Optional[MCPServerState]:
        """Get server runtime state by ID"""
        return self.server_states.get(server_id)

    def find_servers_by_capability(
        self,
        capability: MCPCapability,
        status_filter: Optional[ServerStatus] = ServerStatus.ONLINE,
    ) -> list[tuple[MCPServerConfig, MCPServerState]]:
        """
        Find servers by capability

        Args:
            capability: Required capability
            status_filter: Optional status filter

        Returns:
            List of (config, state) tuples sorted by load and performance
        """
        server_ids = self.capability_index.get(capability, set())
        results = []

        for server_id in server_ids:
            if server_id not in self.servers:
                continue

            config = self.servers[server_id]
            state = self.server_states.get(server_id)

            if not state:
                continue

            # Apply status filter
            if status_filter and state.status != status_filter:
                continue

            results.append((config, state))

        # Sort by load factor (lower is better) and error rate
        results.sort(key=lambda x: (x[1].load_factor, x[1].error_rate))

        return results

    def get_best_server_for_task(
        self, requirements: list[MCPCapability], priority: int = 3
    ) -> Optional[str]:
        """
        Find the best server for a task based on requirements

        Args:
            requirements: Required capabilities
            priority: Task priority (1=critical, 5=low)

        Returns:
            Server ID of best match, or None
        """
        if not requirements:
            return None

        # Find servers that have ALL required capabilities
        candidate_ids = None
        for capability in requirements:
            server_ids = self.capability_index.get(capability, set())
            if candidate_ids is None:
                candidate_ids = server_ids.copy()
            else:
                candidate_ids &= server_ids

        if not candidate_ids:
            logger.warning(f"No servers found with all required capabilities: {requirements}")
            return None

        # Score candidates
        best_server_id = None
        best_score = -1.0

        for server_id in candidate_ids:
            config = self.servers.get(server_id)
            state = self.server_states.get(server_id)

            if not config or not state:
                continue

            # Only consider online servers
            if state.status != ServerStatus.ONLINE:
                continue

            # Check if server can handle more tasks
            if state.current_tasks >= config.max_concurrent_tasks:
                continue

            # Calculate composite score
            # Higher priority tasks prefer higher priority servers
            priority_score = (6 - config.priority) / 5.0  # 1=best, 5=worst
            priority_match = 1.0 - abs(config.priority - priority) / 5.0

            # Lower load is better
            load_score = 1.0 - state.load_factor

            # Lower error rate is better
            reliability_score = 1.0 - state.error_rate

            # Faster response time is better (normalized)
            speed_score = 1.0 if state.average_response_time == 0 else min(
                1.0, 1.0 / (state.average_response_time + 0.1)
            )

            # Composite score with weights
            score = (
                priority_match * 0.3
                + load_score * 0.3
                + reliability_score * 0.25
                + speed_score * 0.15
            )

            if score > best_score:
                best_score = score
                best_server_id = server_id

        return best_server_id

    def update_server_state(
        self, server_id: str, **updates: Any
    ) -> Optional[MCPServerState]:
        """
        Update server state

        Args:
            server_id: Server identifier
            **updates: State fields to update

        Returns:
            Updated state, or None if server not found
        """
        if server_id not in self.server_states:
            return None

        state = self.server_states[server_id]

        for key, value in updates.items():
            if hasattr(state, key):
                setattr(state, key, value)

        state.last_updated = datetime.utcnow()
        return state

    async def check_server_health(self, server_id: str) -> bool:
        """
        Check health of a specific server

        Args:
            server_id: Server identifier

        Returns:
            True if server is healthy
        """
        config = self.servers.get(server_id)
        state = self.server_states.get(server_id)

        if not config or not state:
            return False

        try:
            start_time = time.time()

            async with aiohttp.ClientSession() as session:
                url = f"{config.endpoint}/health"
                headers = {}

                if config.auth_token:
                    headers["Authorization"] = f"Bearer {config.auth_token}"

                async with session.get(
                    url, headers=headers, timeout=aiohttp.ClientTimeout(total=config.timeout)
                ) as response:
                    response_time = time.time() - start_time

                    if response.status == 200:
                        # Update state
                        state.status = ServerStatus.ONLINE
                        state.last_health_check = datetime.utcnow()
                        state.consecutive_failures = 0

                        # Update average response time (exponential moving average)
                        if state.average_response_time == 0:
                            state.average_response_time = response_time
                        else:
                            state.average_response_time = (
                                0.7 * state.average_response_time + 0.3 * response_time
                            )

                        return True
                    else:
                        state.status = ServerStatus.ERROR
                        state.consecutive_failures += 1
                        return False

        except asyncio.TimeoutError:
            logger.warning(f"Health check timeout for server {server_id}")
            state.status = ServerStatus.OFFLINE
            state.consecutive_failures += 1
            return False
        except Exception as e:
            logger.warning(f"Health check failed for server {server_id}: {e}")
            state.status = ServerStatus.ERROR
            state.consecutive_failures += 1
            return False

    async def start_monitoring(self) -> None:
        """Start health monitoring loop"""
        if self.monitoring_active:
            logger.warning("Monitoring already active")
            return

        self.monitoring_active = True
        self.health_check_task = asyncio.create_task(self._monitoring_loop())
        logger.info("Server health monitoring started")

    async def stop_monitoring(self) -> None:
        """Stop health monitoring"""
        self.monitoring_active = False
        if self.health_check_task:
            self.health_check_task.cancel()
            try:
                await self.health_check_task
            except asyncio.CancelledError:
                # Expected when cancelling the health check task; safe to ignore.
                ...
        logger.info("Server health monitoring stopped")

    async def _monitoring_loop(self) -> None:
        """Background health monitoring loop"""
        monitoring_interval = 10  # seconds
        while self.monitoring_active:
            try:
                loop_start_time = time.time()

                # Check all servers that need health checking
                tasks = []
                for server_id, config in self.servers.items():
                    state = self.server_states.get(server_id)
                    if not state:
                        continue

                    # Check if health check is due
                    if (
                        not state.last_health_check
                        or datetime.utcnow() - state.last_health_check
                        > timedelta(seconds=config.health_check_interval)
                    ):
                        tasks.append(self.check_server_health(server_id))

                if tasks:
                    await asyncio.gather(*tasks, return_exceptions=True)

                # Calculate uptime for online servers
                current_time = datetime.utcnow()
                for state in self.server_states.values():
                    # Reset uptime when server transitions to ONLINE
                    if state.status == ServerStatus.ONLINE:
                        if not state.last_online_time:
                            state.last_online_time = current_time
                        # Calculate uptime from when server came online
                        elapsed = (current_time - state.last_online_time).total_seconds()
                        state.uptime_seconds = int(elapsed)
                    else:
                        # Clear online transition time for non-online servers
                        state.last_online_time = None

            except Exception as e:
                logger.error(f"Monitoring loop error: {e}")

            loop_elapsed = time.time() - loop_start_time
            sleep_time = max(0, monitoring_interval - loop_elapsed)
            await asyncio.sleep(sleep_time)

    def get_registry_status(self) -> dict[str, Any]:
        """Get comprehensive registry status"""
        status_counts = defaultdict(int)
        for state in self.server_states.values():
            status_counts[state.status.value] += 1

        capability_coverage = {}
        for capability, server_ids in self.capability_index.items():
            online_count = sum(
                1
                for sid in server_ids
                if self.server_states.get(sid)
                and self.server_states[sid].status == ServerStatus.ONLINE
            )
            capability_coverage[capability.value] = {
                "total": len(server_ids),
                "online": online_count,
                "coverage": f"{online_count}/{len(server_ids)}",
            }

        return {
            "total_servers": len(self.servers),
            "status_breakdown": dict(status_counts),
            "capability_coverage": capability_coverage,
            "monitoring_active": self.monitoring_active,
        }


# Global registry instance
_registry = None


def get_registry() -> MCPServerRegistry:
    """Get the global MCP server registry instance"""
    global _registry
    if _registry is None:
        _registry = MCPServerRegistry()
    return _registry
