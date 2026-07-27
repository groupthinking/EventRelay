"""
MCP Orchestrator - Unified coordination and task execution

Consolidates orchestration logic from:
- src/mcp/mcp_ecosystem_coordinator.py
- mcp-servers/shared-state/state_coordinator.py
- src/youtube_extension/backend/services/agent_orchestrator.py
"""

import asyncio
import logging
import uuid
from collections import deque
from datetime import datetime
from typing import Any, Optional

import aiohttp

from .registry import MCPServerRegistry, get_registry
from .types import MCPCapability, MCPTask, MCPTaskStatus

logger = logging.getLogger(__name__)


class MCPOrchestrator:
    """
    Unified MCP Orchestrator

    Provides centralized coordination for:
    - Task routing and execution
    - Load balancing
    - Dependency management
    - Cross-server communication
    - Performance monitoring
    """

    def __init__(self, registry: Optional[MCPServerRegistry] = None):
        """
        Initialize the orchestrator

        Args:
            registry: Optional MCP server registry (uses global if not provided)
        """
        self.registry = registry or get_registry()

        # Task management
        self.tasks: dict[str, MCPTask] = {}
        self.task_queue: deque[str] = deque()
        self.active_tasks: dict[str, MCPTask] = {}
        self.completed_tasks: deque[MCPTask] = deque(maxlen=1000)

        # Orchestration state
        self.orchestration_active = False
        self.orchestration_task: Optional[asyncio.Task] = None
        self._session: Optional[aiohttp.ClientSession] = None
<<<<<<< HEAD
        # In-flight requests currently borrowing the pooled session. Drained by
        # stop_orchestration() before the session is closed so a direct
        # execute_task() call (which is not tracked in spawned_tasks) cannot have
        # its live HTTP request aborted by shutdown.
        self._pooled_requests: set[asyncio.Task] = set()
=======
>>>>>>> origin/main

        # Track spawned execution tasks by task_id for cancellation support
        self.spawned_tasks: dict[str, asyncio.Task] = {}

        # Maximum concurrent tasks
        self.max_concurrent_spawn = 10

        # Maximum number of tasks to retain in memory (older completed tasks are evicted)
        self.max_tasks_retained = 5000

        # Performance metrics
        self.metrics = {
            "total_tasks": 0,
            "completed_tasks": 0,
            "failed_tasks": 0,
            "cancelled_tasks": 0,
            "average_task_time": 0.0,
        }

        logger.info("MCP Orchestrator initialized")

    async def submit_task(
        self,
        task_type: str,
        payload: dict[str, Any],
        requirements: list[MCPCapability],
        priority: int = 3,
        timeout: int = 300,
        dependencies: Optional[list[str]] = None,
    ) -> str:
        """
        Submit a task for execution

        Args:
            task_type: Type of task to execute
            payload: Task payload/parameters
            requirements: Required server capabilities
            priority: Task priority (1=critical, 5=low)
            timeout: Task timeout in seconds
            dependencies: List of task IDs this task depends on

        Returns:
            Task ID for tracking
        """
        task_id = str(uuid.uuid4())

        task = MCPTask(
            task_id=task_id,
            task_type=task_type,
            payload=payload,
            requirements=requirements,
            priority=priority,
            timeout=timeout,
            dependencies=dependencies or [],
        )

        self.tasks[task_id] = task
        self.metrics["total_tasks"] += 1

        # Evict oldest completed/failed/cancelled tasks if retention limit is exceeded
        if len(self.tasks) > self.max_tasks_retained:
            terminal_states = {MCPTaskStatus.COMPLETED, MCPTaskStatus.FAILED, MCPTaskStatus.CANCELLED}
            evict_ids = sorted(
                [
                    tid for tid, t in self.tasks.items()
                    if t.status in terminal_states and tid not in self.active_tasks
                ],
                key=lambda tid: self.tasks[tid].created_at,
            )
            # Evict enough tasks to bring the count to 90% of the limit
            target_size = int(self.max_tasks_retained * 0.9)
            evict_count = max(1, len(self.tasks) - target_size)
            for tid in evict_ids[:evict_count]:
                del self.tasks[tid]

        # Check if dependencies are met
        if await self._check_dependencies(task_id):
            self.task_queue.append(task_id)
            logger.info(f"Task {task_id} ({task_type}) queued for execution")
        else:
            logger.info(
                f"Task {task_id} ({task_type}) pending dependencies: {task.dependencies}"
            )

        return task_id

    async def get_task_status(self, task_id: str) -> Optional[MCPTask]:
        """
        Get task status

        Args:
            task_id: Task identifier

        Returns:
            Task object with current status, or None if not found
        """
        return self.tasks.get(task_id)

    async def cancel_task(self, task_id: str) -> bool:
        """
        Cancel a pending or executing task

        Args:
            task_id: Task identifier

        Returns:
            True if task was cancelled
        """
        task = self.tasks.get(task_id)
        if not task:
            return False

        if task.status in [MCPTaskStatus.COMPLETED, MCPTaskStatus.FAILED]:
            logger.warning(f"Cannot cancel task {task_id} in status {task.status}")
            return False

        task.status = MCPTaskStatus.CANCELLED
        task.completed_at = datetime.utcnow()

        # Remove from queue if present
        if task_id in self.task_queue:
            self.task_queue.remove(task_id)

        # Cancel the underlying asyncio task if it is currently executing
        if task_id in self.spawned_tasks:
            asyncio_task = self.spawned_tasks.pop(task_id)
            if not asyncio_task.done():
                asyncio_task.cancel()
            # Decrement server counter so load tracking stays consistent
            if task.assigned_server:
                server_state = self.registry.get_server_state(task.assigned_server)
                if server_state and server_state.current_tasks > 0:
                    server_state.current_tasks -= 1
                    server_config = self.registry.get_server(task.assigned_server)
                    if server_config:
                        server_state.load_factor = max(
                            0.0,
                            server_state.current_tasks / server_config.max_concurrent_tasks,
                        )

        # Remove from active tasks
        if task_id in self.active_tasks:
            del self.active_tasks[task_id]

        self.metrics["cancelled_tasks"] += 1
        logger.info(f"Task {task_id} cancelled")

        return True

    async def _execute_task_wrapper(self, task_id: str) -> None:
        """
        Wrapper for execute_task that handles exceptions and cleanup

        Args:
            task_id: Task identifier
        """
        try:
            await self.execute_task(task_id)
        except asyncio.CancelledError:
            # Task was cancelled externally; only update state if not already finalised
            task = self.tasks.get(task_id)
            if task and task.status not in [
                MCPTaskStatus.COMPLETED,
                MCPTaskStatus.FAILED,
                MCPTaskStatus.CANCELLED,
            ]:
                task.status = MCPTaskStatus.CANCELLED
                task.completed_at = datetime.utcnow()
                self.metrics["cancelled_tasks"] += 1
            raise
        except Exception as e:
            logger.error(f"Unhandled exception in task {task_id}: {e}", exc_info=True)
        finally:
            # Always clean up the spawned_tasks entry
            self.spawned_tasks.pop(task_id, None)
    
    async def execute_task(self, task_id: str) -> dict[str, Any]:
        """
        Execute a specific task

        Args:
            task_id: Task identifier

        Returns:
            Task execution result
        """
        task = self.tasks.get(task_id)
        if not task:
            raise ValueError(f"Task not found: {task_id}")

        # Find best server for task
        server_id = self.registry.get_best_server_for_task(
            task.requirements, task.priority
        )

        if not server_id:
            task.status = MCPTaskStatus.FAILED
            task.error = f"No available server for requirements: {task.requirements}"
            task.completed_at = datetime.utcnow()
            self.metrics["failed_tasks"] += 1
            logger.error(f"Task {task_id} failed: {task.error}")
            return {"status": "failed", "error": task.error}

        # Update task status
        task.status = MCPTaskStatus.EXECUTING
        task.assigned_server = server_id
        task.started_at = datetime.utcnow()
        self.active_tasks[task_id] = task

        logger.info(f"Executing task {task_id} on server {server_id}")

        # Initialize server_state before try block to avoid NameError in except block
        server_state = None
        try:
            # Update server state
            server_state = self.registry.get_server_state(server_id)
            server_config = self.registry.get_server(server_id)
            if server_state and server_config:
                server_state.current_tasks += 1
                server_state.load_factor = min(
                    1.0,
                    server_state.current_tasks / server_config.max_concurrent_tasks,
                )

            # Execute task (placeholder - actual implementation would call server)
            result = await self._execute_on_server(server_id, task)

            # Update task with result
            task.status = MCPTaskStatus.COMPLETED
            task.result = result
            task.completed_at = datetime.utcnow()

            # Update metrics
            self.metrics["completed_tasks"] += 1
            task_time = (task.completed_at - task.started_at).total_seconds()
            self._update_average_task_time(task_time)

            # Update server state
            if server_state and server_config:
                server_state.current_tasks -= 1
                server_state.total_tasks_completed += 1
                server_state.load_factor = max(
                    0.0,
                    server_state.current_tasks / server_config.max_concurrent_tasks,
                )

            # Move to completed
            if task_id in self.active_tasks:
                del self.active_tasks[task_id]
            self.completed_tasks.append(task)

            # Check if this completion enables dependent tasks
            await self._check_dependent_tasks(task_id)

            logger.info(f"Task {task_id} completed successfully in {task_time:.2f}s")
            return {"status": "success", "result": result}

        except Exception as e:
            logger.error(f"Task {task_id} failed with error: {e}")

            task.status = MCPTaskStatus.FAILED
            task.error = str(e)
            task.completed_at = datetime.utcnow()

            self.metrics["failed_tasks"] += 1

            # Update server state
            if server_state:
                server_state.current_tasks -= 1
                server_state.total_tasks_failed += 1
                server_state.error_rate = min(
                    1.0,
                    server_state.total_tasks_failed
                    / max(1, server_state.total_tasks_completed + server_state.total_tasks_failed),
                )

            # Move to completed (even though failed)
            if task_id in self.active_tasks:
                del self.active_tasks[task_id]
            self.completed_tasks.append(task)

            return {"status": "failed", "error": str(e)}

    async def _execute_on_server(
        self, server_id: str, task: MCPTask
    ) -> Any:
        """
        Execute task on a specific server via MCP/JSON-RPC.
<<<<<<< HEAD

        Returns the JSON-RPC ``result`` member when the server responds with a
        compliant envelope, or the raw response body otherwise. Raises on a
        JSON-RPC ``error`` envelope or an HTTP-level failure.
=======
>>>>>>> origin/main
        """
        config = self.registry.get_server(server_id)
        if not config:
            raise ValueError(f"Cannot execute task {task.task_id}: MCP server not found: {server_id}")

        headers = {"Content-Type": "application/json"}
        if config.auth_token:
            headers["Authorization"] = f"Bearer {config.auth_token}"

        payload = {
            "jsonrpc": "2.0",
            "method": task.task_type,
            "params": task.payload,
            "id": task.task_id,
        }

        timeout = aiohttp.ClientTimeout(total=config.timeout)

<<<<<<< HEAD
        async def _post(session: aiohttp.ClientSession) -> Any:
=======
        session = self._session
        own_session = session is None
        if own_session:
            session = aiohttp.ClientSession()

        try:
>>>>>>> origin/main
            async with session.post(
                config.endpoint,
                json=payload,
                headers=headers,
                timeout=timeout,
            ) as response:
                response.raise_for_status()
<<<<<<< HEAD
                body = await response.json()

                # JSON-RPC 2.0 servers report application-level failures with an
                # `error` member and an HTTP 200 status. Raise so the caller marks
                # the task FAILED instead of recording the error envelope as a
                # successful result.
                if isinstance(body, dict) and body.get("error") is not None:
                    error = body["error"]
                    if isinstance(error, dict):
                        raise RuntimeError(
                            f"JSON-RPC error {error.get('code')}: "
                            f"{error.get('message', 'Unknown error')}"
                        )
                    raise RuntimeError(f"JSON-RPC error: {error}")

                # Return the `result` member per JSON-RPC 2.0 when present; fall
                # back to the raw body for non-compliant servers.
                if isinstance(body, dict) and "result" in body:
                    return body["result"]
                return body

        try:
            # Reuse the pooled session created by start_orchestration() so tasks
            # share a single connection pool. A direct execute_task() call is not
            # tracked in spawned_tasks, so register the in-flight request in
            # _pooled_requests; stop_orchestration() drains it before closing the
            # session. The active-check and registration below run without an
            # intervening await, so they are atomic relative to shutdown. Fall back
            # to a short-lived session outside an active orchestration loop.
            if (
                self.orchestration_active
                and self._session is not None
                and not self._session.closed
            ):
                request = asyncio.ensure_future(_post(self._session))
                self._pooled_requests.add(request)
                try:
                    return await request
                finally:
                    self._pooled_requests.discard(request)
            async with aiohttp.ClientSession() as session:
                return await _post(session)
=======
                return await response.json()
>>>>>>> origin/main
        except Exception as e:
            logger.error(
                "Failed to execute task %s on server %s: %s",
                task.task_id,
                server_id,
                e,
            )
            raise
<<<<<<< HEAD
=======
        finally:
            if own_session:
                await session.close()
>>>>>>> origin/main

    async def _check_dependencies(self, task_id: str) -> bool:
        """
        Check if all task dependencies are completed

        Args:
            task_id: Task identifier

        Returns:
            True if all dependencies are met
        """
        task = self.tasks.get(task_id)
        if not task or not task.dependencies:
            return True

        for dep_id in task.dependencies:
            dep_task = self.tasks.get(dep_id)
            if not dep_task or dep_task.status != MCPTaskStatus.COMPLETED:
                return False

        return True

    async def _check_dependent_tasks(self, completed_task_id: str) -> None:
        """
        Check for tasks waiting on the completed task

        Args:
            completed_task_id: ID of task that just completed
        """
        for task_id, task in self.tasks.items():
            if (
                completed_task_id in task.dependencies
                and task.status == MCPTaskStatus.PENDING
            ):
                if await self._check_dependencies(task_id):
                    self.task_queue.append(task_id)
                    logger.info(f"Task {task_id} dependencies met, queued for execution")

    def _update_average_task_time(self, task_time: float) -> None:
        """Update average task execution time"""
        if self.metrics["average_task_time"] == 0:
            self.metrics["average_task_time"] = task_time
        else:
            # Exponential moving average
            self.metrics["average_task_time"] = (
                0.8 * self.metrics["average_task_time"] + 0.2 * task_time
            )

    async def start_orchestration(self) -> None:
        """Start the orchestration loop"""
        if self.orchestration_active:
            logger.warning("Orchestration already active")
            return

        self.orchestration_active = True
        if self._session is None:
            self._session = aiohttp.ClientSession()
        self.orchestration_task = asyncio.create_task(self._orchestration_loop())
        logger.info("MCP Orchestration started")

    async def stop_orchestration(self) -> None:
        """Stop the orchestration loop and cancel all spawned tasks"""
        self.orchestration_active = False

        # Cancel all spawned execution tasks
        if self.spawned_tasks:
            logger.info(f"Cancelling {len(self.spawned_tasks)} spawned tasks")
            for asyncio_task in self.spawned_tasks.values():
                if not asyncio_task.done():
                    asyncio_task.cancel()

            # Wait for all tasks to finish
            try:
                await asyncio.gather(*self.spawned_tasks.values(), return_exceptions=True)
            except Exception as e:
                logger.error(f"Error waiting for spawned tasks to cancel: {e}")

            self.spawned_tasks.clear()

        # Cancel the orchestration loop task
        if self.orchestration_task:
            self.orchestration_task.cancel()
            try:
                await self.orchestration_task
            except asyncio.CancelledError:
                pass

<<<<<<< HEAD
        # Drain any requests still borrowing the pooled session (e.g. a direct
        # execute_task() call in flight) before closing it, so shutdown never
        # aborts a live HTTP request. orchestration_active is already False, so no
        # new request will adopt the pooled session past this point.
        if self._pooled_requests:
            await asyncio.gather(*self._pooled_requests, return_exceptions=True)
            self._pooled_requests.clear()

=======
>>>>>>> origin/main
        if self._session:
            await self._session.close()
            self._session = None

        logger.info("MCP Orchestration stopped")

    async def _orchestration_loop(self) -> None:
        """Main orchestration loop"""
        try:
            while self.orchestration_active:
                try:
                    # Clean up completed spawned tasks
                    done_ids = [tid for tid, t in self.spawned_tasks.items() if t.done()]
                    for tid in done_ids:
                        del self.spawned_tasks[tid]

                    # Process queued tasks respecting concurrent limit
                    if self.task_queue:
                        # Calculate how many more tasks we can spawn
                        available_slots = self.max_concurrent_spawn - len(self.spawned_tasks)
                        tasks_to_process = min(available_slots, len(self.task_queue))

                        for _ in range(tasks_to_process):
                            if not self.task_queue:
                                break

                            task_id = self.task_queue.popleft()
                            # Create task using wrapper for proper error handling
                            spawned_task = asyncio.create_task(self._execute_task_wrapper(task_id))
                            self.spawned_tasks[task_id] = spawned_task

                    # Small delay to prevent CPU spinning
                    await asyncio.sleep(0.1)

                except asyncio.CancelledError:
                    raise
                except Exception as e:
                    logger.error(f"Orchestration loop error: {e}", exc_info=True)
                    await asyncio.sleep(1)
        finally:
            # Cleanup: cancel all remaining spawned tasks
            if self.spawned_tasks:
                logger.info(f"Orchestration loop ending, cleaning up {len(self.spawned_tasks)} spawned tasks")
                for asyncio_task in self.spawned_tasks.values():
                    if not asyncio_task.done():
                        asyncio_task.cancel()

    def get_orchestrator_status(self) -> dict[str, Any]:
        """Get comprehensive orchestrator status"""
        return {
            "orchestration_active": self.orchestration_active,
            "queued_tasks": len(self.task_queue),
            "active_tasks": len(self.active_tasks),
            "total_tasks": len(self.tasks),
            "metrics": self.metrics.copy(),
            "registry_status": self.registry.get_registry_status(),
        }


# Global orchestrator instance
_orchestrator = None


def get_orchestrator() -> MCPOrchestrator:
    """Get the global MCP orchestrator instance"""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = MCPOrchestrator()
    return _orchestrator
