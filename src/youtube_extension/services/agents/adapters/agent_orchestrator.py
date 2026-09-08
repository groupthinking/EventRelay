#!/usr/bin/env python3
"""
Agent Orchestrator Service
===========================

Centralized orchestration for AI agents with task delegation,
parallel processing, and intelligent routing.
"""

import asyncio
import logging
import uuid
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

from ..base_agent import AgentRequest, AgentResult, BaseAgent


@dataclass
class A2AContextMessage:
    """Lightweight A2A context-share message within the orchestrator."""

    sender: str
    recipient: str
    content: dict[str, Any]
    conversation_id: str = ""
    timestamp: str = ""

    def __post_init__(self):
        if not self.conversation_id:
            self.conversation_id = str(uuid.uuid4())
        if not self.timestamp:
            self.timestamp = datetime.utcnow().isoformat()


@dataclass
class OrchestrationResult:
    """Result from agent orchestration"""

    success: bool
    results: dict[str, AgentResult] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    total_processing_time: float = 0.0
    agents_used: list[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)


from ..registry import get as get_agent_class


class AgentOrchestrator:
    """
    Centralized orchestration for AI agents.
    Handles task delegation, parallel processing, and result aggregation.
    """

    def __init__(self):
        """Initialize agent orchestrator"""
        self.logger = logging.getLogger("agent_orchestrator")
        self._agents: dict[str, BaseAgent] = {}
        self._agent_types: dict[str, type[BaseAgent]] = {}
        # Bounded: the module-level `orchestrator` singleton lives for the whole
        # process and every dispatch appends here, so an unbounded list would
        # grow without limit. maxlen evicts the oldest entries automatically.
        self._a2a_log: deque[A2AContextMessage] = deque(maxlen=1000)
        self._task_mappings: dict[str, list[str]] = {
            "video_analysis": [
                "video_master",
                "action_implementer",
                "personality_agent",
                "strategy_agent",
            ],
            "content_generation": ["video_master"],
            "action_planning": ["action_implementer"],
            "transcript_action": ["transcript_action"],
            "strategic_analysis": ["personality_agent", "strategy_agent"],
            "chat_assistance": ["transcript_action"],
        }

    def register_agent_type(self, name: str, agent_class: type[BaseAgent]):
        """
        Register a new agent type.

        Args:
            name: Agent type name
            agent_class: Agent class
        """
        self._agent_types[name] = agent_class
        self.logger.info(f"Registered agent type: {name}")

    async def get_agent(
        self, name: str, config: Optional[dict[str, Any]] = None
    ) -> Optional[BaseAgent]:
        """
        Get agent instance, creating if needed.

        Args:
            name: Agent name
            config: Configuration for agent creation

        Returns:
            Agent instance or None if not found
        """
        if name in self._agents:
            return self._agents[name]

        # Check registered types first
        if name in self._agent_types:
            try:
                agent_class = self._agent_types[name]
                try:
                    agent = agent_class(config=config)
                except TypeError:
                    agent = agent_class()
                self._agents[name] = agent
                return agent
            except Exception as e:
                self.logger.error(f"Failed to instantiate agent {name}: {e}")
                return None

        # Fallback to registry
        try:
            agent_class = get_agent_class(name)
            try:
                agent = agent_class(config=config)
            except TypeError:
                agent = agent_class()
            self._agents[name] = agent
            return agent
        except KeyError:
            self.logger.warning(f"Agent not found in registry: {name}")
            return None

    async def execute_task(
        self,
        task_type: str,
        input_data: dict[str, Any],
        agent_configs: Optional[dict[str, dict[str, Any]]] = None,
    ) -> OrchestrationResult:
        """
        Execute a task using appropriate agents.

        Args:
            task_type: Type of task to execute
            input_data: Input data for processing
            agent_configs: Agent-specific configurations

        Returns:
            OrchestrationResult with aggregated results
        """
        start_time = asyncio.get_event_loop().time()
        agent_configs = agent_configs or {}

        self.logger.info(f"Starting task execution: {task_type}")

        if task_type not in self._task_mappings:
            return OrchestrationResult(
                success=False,
                errors=[f"Unknown task type: {task_type}"],
                total_processing_time=asyncio.get_event_loop().time() - start_time,
            )

        agent_names = self._task_mappings[task_type]
        agents = []

        # Get all required agents
        for agent_name in agent_names:
            config = agent_configs.get(agent_name, {})
            agent = await self.get_agent(agent_name, config)
            if agent:
                agents.append(agent)
            else:
                return OrchestrationResult(
                    success=False,
                    errors=[f"Failed to get agent: {agent_name}"],
                    total_processing_time=asyncio.get_event_loop().time() - start_time,
                )

        # Execute agents in parallel
        try:
            tasks = [
                agent.run(AgentRequest(task=task_type, params=input_data))
                for agent in agents
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            orchestration_result = OrchestrationResult(success=True)

            for i, result in enumerate(results):
                agent_name = agents[i].name
                orchestration_result.agents_used.append(agent_name)

                if isinstance(result, Exception):
                    orchestration_result.success = False
                    orchestration_result.errors.append(
                        f"Agent {agent_name} failed: {str(result)}"
                    )
                else:
                    orchestration_result.results[agent_name] = result
                    if result.status != "ok":
                        orchestration_result.success = False
                        orchestration_result.errors.extend(result.logs)

            orchestration_result.total_processing_time = (
                asyncio.get_event_loop().time() - start_time
            )

            # A2A context sharing: broadcast each agent's output to all others
            if orchestration_result.success and len(orchestration_result.results) > 1:
                conv_id = str(uuid.uuid4())
                for sender_name, sender_result in orchestration_result.results.items():
                    for recipient_name in orchestration_result.results:
                        if recipient_name != sender_name:
                            msg = A2AContextMessage(
                                sender=sender_name,
                                recipient=recipient_name,
                                content={"type": "context_share", "output": sender_result.output},
                                conversation_id=conv_id,
                            )
                            self._a2a_log.append(msg)
                self.logger.debug(
                    "A2A context shared across %d agents (conv=%s)",
                    len(orchestration_result.results),
                    conv_id,
                )

            self.logger.info(
                f"Task execution completed: {task_type} "
                f"(success={orchestration_result.success}, "
                f"time={orchestration_result.total_processing_time:.2f}s)"
            )

            return orchestration_result

        except Exception as e:
            self.logger.error(f"Task execution failed: {e}", exc_info=True)
            return OrchestrationResult(
                success=False,
                errors=[f"Orchestration failed: {str(e)}"],
                total_processing_time=asyncio.get_event_loop().time() - start_time,
            )

    async def execute_agents_sequentially(
        self,
        agent_names: list[str],
        input_data: dict[str, Any],
        agent_configs: Optional[dict[str, dict[str, Any]]] = None,
    ) -> OrchestrationResult:
        """
        Execute agents sequentially, passing results between them.

        Args:
            agent_names: List of agent names to execute in order
            input_data: Initial input data
            agent_configs: Agent-specific configurations

        Returns:
            OrchestrationResult with sequential results
        """
        start_time = asyncio.get_event_loop().time()
        agent_configs = agent_configs or {}

        orchestration_result = OrchestrationResult(success=True)
        current_data = input_data.copy()

        for agent_name in agent_names:
            config = agent_configs.get(agent_name, {})
            agent = await self.get_agent(agent_name, config)

            if not agent:
                orchestration_result.success = False
                orchestration_result.errors.append(f"Failed to get agent: {agent_name}")
                break

            task_name = current_data.get("task") or current_data.get("task_type") or agent_name
            result = await agent.run(AgentRequest(task=task_name, params=current_data))
            orchestration_result.results[agent_name] = result
            orchestration_result.agents_used.append(agent_name)

            if result.status != "ok":
                orchestration_result.success = False
                orchestration_result.errors.extend(result.logs)
                break

            # Update current_data with result for next agent
            current_data.update(result.output)

        orchestration_result.total_processing_time = (
            asyncio.get_event_loop().time() - start_time
        )
        return orchestration_result

    def list_agents(self) -> list[str]:
        """List all registered agents"""
        return list(self._agents.keys()) + list(self._agent_types.keys())

    def list_task_types(self) -> list[str]:
        """List all available task types"""
        return list(self._task_mappings.keys())

    def add_task_mapping(self, task_type: str, agent_names: list[str]):
        """
        Add a new task mapping.

        Args:
            task_type: Task type name
            agent_names: List of agent names for this task
        """
        self._task_mappings[task_type] = agent_names
        self.logger.info(f"Added task mapping: {task_type} -> {agent_names}")

    # --- Single-agent dispatch ---

    async def execute_single(
        self,
        agent_type: str,
        context: dict[str, Any],
        config: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """
        Execute a single agent by type with the given context.

        Used by the agent dispatch system to run one agent against one event.
        The agent is resolved via registered types or the global registry.

        Args:
            agent_type: The agent type/name to execute.
            context: Context data (e.g. the extracted event) passed to the agent.
            config: Optional agent-specific configuration.

        Returns:
            dict with the agent's output, or an error dict if execution fails.
        """
        agent = await self.get_agent(agent_type, config)
        if not agent:
            self.logger.warning(
                "Agent type %s not found for execute_single", agent_type
            )
            # Record the failed dispatch so the session/audit trail is complete
            # (matches the success, agent-failure, and exception paths below).
            self._a2a_log.append(
                A2AContextMessage(
                    sender="orchestrator",
                    recipient=agent_type,
                    content={
                        "type": "agent_dispatch",
                        "agent_type": agent_type,
                        "context": context,
                        "status": "error",
                        "error": "agent_not_found",
                    },
                )
            )
            return {"error": f"Agent type '{agent_type}' not found"}

        try:
            request = AgentRequest(task=agent_type, params=context)
            result = await agent.run(request)

            # Log execution in A2A log for session tracking
            self._a2a_log.append(
                A2AContextMessage(
                    sender="orchestrator",
                    recipient=agent_type,
                    content={
                        "type": "agent_dispatch",
                        "agent_type": agent_type,
                        "context": context,
                        "status": result.status,
                    },
                )
            )

            if result.status == "ok":
                return result.output
            else:
                error_msg = (
                    "; ".join(result.logs) or "Agent execution failed"
                )
                return {"error": error_msg, "output": result.output}
        except Exception as e:
            self.logger.error("execute_single failed for %s: %s", agent_type, e)
            self._a2a_log.append(
                A2AContextMessage(
                    sender="orchestrator",
                    recipient=agent_type,
                    content={
                        "type": "agent_dispatch",
                        "agent_type": agent_type,
                        "context": context,
                        "status": "error",
                        "error": str(e),
                    },
                )
            )
            return {"error": str(e)}

    def get_session_logs(
        self,
        agent_type: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Return agent dispatch session logs, optionally filtered by agent type.

        Session logs track which agents were dispatched, what context they received,
        and their execution status. This enables the recursive feedback loop where
        agent findings can be reviewed and re-dispatched.

        Args:
            agent_type: Filter to a specific agent type, or None for all.
            limit: Maximum entries to return.

        Returns:
            List of session log entries.
        """
        dispatch_msgs = [
            m for m in self._a2a_log
            if m.content.get("type") == "agent_dispatch"
        ]
        if agent_type:
            dispatch_msgs = [
                m for m in dispatch_msgs
                if m.content.get("agent_type") == agent_type
            ]
        return [
            {
                "sender": m.sender,
                "recipient": m.recipient,
                "agent_type": m.content.get("agent_type"),
                "context": m.content.get("context"),
                "status": m.content.get("status"),
                "timestamp": m.timestamp,
                "conversation_id": m.conversation_id,
            }
            for m in dispatch_msgs[-limit:]
        ]

    # --- A2A messaging ---

    async def send_a2a_message(
        self,
        sender: str,
        recipient: str,
        content: dict[str, Any],
        conversation_id: str | None = None,
    ) -> A2AContextMessage:
        """Send an A2A context-share message between agents."""
        msg = A2AContextMessage(
            sender=sender,
            recipient=recipient,
            content=content,
            conversation_id=conversation_id or str(uuid.uuid4()),
        )
        self._a2a_log.append(msg)

        # Deliver to recipient agent if it exists
        agent = self._agents.get(recipient)
        if agent and hasattr(agent, "receive_context"):
            try:
                await agent.receive_context(content)
            except Exception as e:
                self.logger.warning("Agent %s failed to receive context: %s", recipient, e)

        return msg

    def get_a2a_log(
        self,
        conversation_id: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Return recent A2A messages, optionally filtered by conversation."""
        # Materialize to a list so `[-limit:]` slicing works (deque is not
        # sliceable).
        msgs = list(self._a2a_log)
        if conversation_id:
            msgs = [m for m in msgs if m.conversation_id == conversation_id]
        return [
            {
                "sender": m.sender,
                "recipient": m.recipient,
                "content": m.content,
                "conversation_id": m.conversation_id,
                "timestamp": m.timestamp,
            }
            for m in msgs[-limit:]
        ]

    # --- Managed execution backends ---

    async def execute_antigravity_backend(
        self,
        backend: Any,
        task: str,
        context: Optional[dict[str, Any]] = None,
    ) -> Any:
        """Execute one task through the guarded Antigravity provider adapter.

        The adapter owns feature flags, read-only MCP validation, token limits,
        and live-call approval.  The orchestrator records only receipt metadata,
        never the input context or provider credentials.
        """
        receipt = await backend.execute(task=task, context=context or {})
        self._a2a_log.append(
            A2AContextMessage(
                sender="orchestrator",
                recipient="google_antigravity",
                content={
                    "type": "managed_backend_dispatch",
                    "backend": "google_antigravity",
                    "status": receipt.status,
                    "receipt_id": receipt.receipt_id,
                    "interaction_id": receipt.interaction_id,
                    "environment_id": receipt.environment_id,
                    "budget_exceeded": receipt.budget_exceeded,
                },
            )
        )
        return receipt

    # --- Legacy local Antigravity-pattern workflow ---

    async def execute_antigravity_delegation(
        self,
        task_type: str,
        input_data: dict[str, Any],
        subagent_names: Optional[list[str]] = None,
        agent_configs: Optional[dict[str, dict[str, Any]]] = None,
    ) -> OrchestrationResult:
        """
        Execute subagent delegation using Google Antigravity SDK patterns.
        Spawns subagents, orchestrates context passing, and aggregates results.
        Falls back to native execution when Antigravity SDK features are not enabled.

        Args:
            task_type: Core task type to execute.
            input_data: Shared input payload.
            subagent_names: Optional explicit list of subagents to delegate to.
            agent_configs: Configurations for individual subagents.

        Returns:
            OrchestrationResult containing aggregated subagent results and telemetry.
        """
        start_time = asyncio.get_event_loop().time()
        self.logger.info("Executing Antigravity SDK delegation workflow for: %s", task_type)

        target_agents = subagent_names or self._task_mappings.get(task_type, ["video_master"])
        delegation_conv_id = str(uuid.uuid4())

        # Log delegation dispatch start
        for name in target_agents:
            await self.send_a2a_message(
                sender="orchestrator",
                recipient=name,
                content={
                    "type": "agent_dispatch",
                    "task_type": task_type,
                    "agent_type": name,
                    "context": input_data,
                    "status": "delegated",
                    "framework": "google_antigravity_sdk",
                },
                conversation_id=delegation_conv_id,
            )

        # Delegate execution across subagents sequentially
        result = await self.execute_agents_sequentially(
            agent_names=target_agents,
            input_data=input_data,
            agent_configs=agent_configs,
        )
        result.total_processing_time = asyncio.get_event_loop().time() - start_time
        return result


# Global orchestrator instance
orchestrator = AgentOrchestrator()
