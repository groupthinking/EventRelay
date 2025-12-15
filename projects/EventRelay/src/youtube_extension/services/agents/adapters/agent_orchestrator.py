#!/usr/bin/env python3
"""
Agent Orchestrator Service
===========================

Centralized orchestration for AI agents with task delegation,
parallel processing, and intelligent routing.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional, Type
from datetime import datetime
from dataclasses import dataclass, field

from ..base_agent import BaseAgent, AgentResult
from .transcript_action_agent import TranscriptActionAgent


@dataclass
class OrchestrationResult:
    """Result from agent orchestration"""
    success: bool
    results: Dict[str, AgentResult] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    total_processing_time: float = 0.0
    agents_used: List[str] = field(default_factory=list)
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
        self._agents: Dict[str, BaseAgent] = {}
        self._task_mappings: Dict[str, List[str]] = {
            "video_analysis": ["video_master", "action_implementer"],
            "content_generation": ["video_master"],
            "action_planning": ["action_implementer"],
            "transcript_action": ["transcript_action"],
        }

    async def get_agent(self, name: str, config: Optional[Dict[str, Any]] = None) -> Optional[BaseAgent]:
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

        try:
            agent_class = get_agent_class(name)
            agent = agent_class(config=config)
            self._agents[name] = agent
            return agent
        except KeyError:
            self.logger.warning(f"Agent not found in registry: {name}")
            return None

    async def execute_task(
        self,
        task_type: str,
        input_data: Dict[str, Any],
        agent_configs: Optional[Dict[str, Dict[str, Any]]] = None
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
                total_processing_time=asyncio.get_event_loop().time() - start_time
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
                    total_processing_time=asyncio.get_event_loop().time() - start_time
                )

        # Execute agents in parallel
        try:
            tasks = [agent.run(AgentRequest(params=input_data)) for agent in agents]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            orchestration_result = OrchestrationResult(success=True)

            for i, result in enumerate(results):
                agent_name = agents[i].name
                orchestration_result.agents_used.append(agent_name)

                if isinstance(result, Exception):
                    orchestration_result.success = False
                    orchestration_result.errors.append(f"Agent {agent_name} failed: {str(result)}")
                else:
                    orchestration_result.results[agent_name] = result
                    if result.status != "ok":
                        orchestration_result.success = False
                        orchestration_result.errors.extend(result.logs)

            orchestration_result.total_processing_time = asyncio.get_event_loop().time() - start_time

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
                total_processing_time=asyncio.get_event_loop().time() - start_time
            )

    async def execute_agents_sequentially(
        self,
        agent_names: List[str],
        input_data: Dict[str, Any],
        agent_configs: Optional[Dict[str, Dict[str, Any]]] = None
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

            result = await agent.run(AgentRequest(params=current_data))
            orchestration_result.results[agent_name] = result
            orchestration_result.agents_used.append(agent_name)

            if result.status != "ok":
                orchestration_result.success = False
                orchestration_result.errors.extend(result.logs)
                break

            # Update current_data with result for next agent
            current_data.update(result.output)

        orchestration_result.total_processing_time = asyncio.get_event_loop().time() - start_time
        return orchestration_result

    def list_agents(self) -> List[str]:
        """List all registered agents"""
        return list(self._agents.keys()) + list(self._agent_types.keys())

    def list_task_types(self) -> List[str]:
        """List all available task types"""
        return list(self._task_mappings.keys())

    def add_task_mapping(self, task_type: str, agent_names: List[str]):
        """
        Add a new task mapping.

        Args:
            task_type: Task type name
            agent_names: List of agent names for this task
        """
        self._task_mappings[task_type] = agent_names
        self.logger.info(f"Added task mapping: {task_type} -> {agent_names}")


# Global orchestrator instance
orchestrator = AgentOrchestrator()
