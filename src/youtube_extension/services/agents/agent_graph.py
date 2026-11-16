"""
Agent Graph Execution Engine for EventRelay.
Supports DAG execution, fork-join parallel delegation, conditional branching,
and cyclic self-correction loops with termination guards.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, Callable

from .agent_handoff import AgentHandoffEnvelope
from .base_agent import AgentResult, BaseAgent
from .dto import AgentRequest

logger = logging.getLogger(__name__)


@dataclass
class LoopResult:
    """Result of a cyclic evaluation/self-correction loop."""
    success: bool
    iterations: int
    final_output: dict[str, Any]
    history: list[dict[str, Any]] = field(default_factory=list)
    error: str | None = None


class AgentGraph:
    """
    Execution graph composed of Agent nodes, condition nodes, and cyclic loops.
    """

    def __init__(self, name: str = "default_agent_graph"):
        self.name = name
        self.nodes: dict[str, BaseAgent] = {}
        self.edges: list[tuple[str, str, Callable[[dict[str, Any]], bool] | None]] = []
        self._conditions: dict[str, Callable[[dict[str, Any]], str]] = {}

    def add_agent_node(self, name: str, agent: BaseAgent) -> AgentGraph:
        """Add an agent node to the graph."""
        self.nodes[name] = agent
        return self

    def add_edge(
        self,
        from_node: str,
        to_node: str,
        condition: Callable[[dict[str, Any]], bool] | None = None,
    ) -> AgentGraph:
        """Add a directed edge between two nodes with an optional condition predicate."""
        self.edges.append((from_node, to_node, condition))
        return self

    def add_conditional_router(
        self,
        from_node: str,
        router_fn: Callable[[dict[str, Any]], str],
    ) -> AgentGraph:
        """Add dynamic routing logic determining the next node based on output."""
        self._conditions[from_node] = router_fn
        return self

    async def execute_pipeline(
        self,
        initial_node: str,
        initial_payload: dict[str, Any],
        trace_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Execute the graph starting from initial_node until a terminal node is reached.
        """
        current_node_name = initial_node
        current_envelope = AgentHandoffEnvelope(
            trace_id=trace_id or "",
            sender_agent="graph_entrypoint",
            recipient_agent=current_node_name,
            intent="execute_node",
            payload=initial_payload,
        )

        outputs: dict[str, Any] = {}
        visited: list[str] = []

        while current_node_name in self.nodes:
            visited.append(current_node_name)
            agent = self.nodes[current_node_name]
            current_envelope.acknowledge()

            req = AgentRequest(task=current_envelope.intent, params=current_envelope.payload)
            res: AgentResult = await agent.run(req)
            node_output = res.output if isinstance(res.output, dict) else {"result": res.output}
            outputs[current_node_name] = node_output
            current_envelope.payload.update(node_output)

            # Check dynamic router
            if current_node_name in self._conditions:
                next_node = self._conditions[current_node_name](node_output)
                if next_node and next_node in self.nodes:
                    current_envelope = current_envelope.forward(
                        next_recipient=next_node,
                        next_intent="execute_node",
                        updated_payload=node_output,
                    )
                    current_node_name = next_node
                    continue
                break

            # Find matching outgoing edges
            next_node = None
            for from_n, to_n, cond in self.edges:
                if from_n == current_node_name:
                    if cond is None or cond(node_output):
                        next_node = to_n
                        break

            if next_node and next_node in self.nodes:
                current_envelope = current_envelope.forward(
                    next_recipient=next_node,
                    next_intent="execute_node",
                    updated_payload=node_output,
                )
                current_node_name = next_node
            else:
                break

        return {
            "success": True,
            "visited_nodes": visited,
            "outputs": outputs,
            "final_payload": current_envelope.payload,
        }

    async def execute_fork_join(
        self,
        subagent_names: list[str],
        shared_input: dict[str, Any],
        intent: str = "parallel_subtask",
    ) -> dict[str, Any]:
        """
        Execute multiple agents in parallel (fork) and aggregate their outputs (join).
        """
        tasks = []
        for name in subagent_names:
            agent = self.nodes.get(name)
            if not agent:
                raise ValueError(f"Agent {name} not registered in graph.")
            envelope = AgentHandoffEnvelope(
                sender_agent="fork_join",
                recipient_agent=name,
                intent=intent,
                payload=shared_input,
            )
            envelope.acknowledge()
            tasks.append(agent.run(AgentRequest(task=intent, params=envelope.payload)))

        results = await asyncio.gather(*tasks, return_exceptions=True)
        aggregated: dict[str, Any] = {}
        for name, res in zip(subagent_names, results):
            if isinstance(res, Exception):
                aggregated[name] = {"error": str(res), "status": "error"}
            else:
                aggregated[name] = res.output if isinstance(res.output, dict) else {"result": res.output}

        return aggregated

    async def execute_self_correction_loop(
        self,
        generator_name: str,
        evaluator_fn: Callable[[dict[str, Any]], tuple[bool, str | None]],
        initial_input: dict[str, Any],
        max_iterations: int = 3,
    ) -> LoopResult:
        """
        Execute a cyclic generator-evaluator loop until the evaluator accepts
        or max_iterations is reached.
        """
        agent = self.nodes.get(generator_name)
        if not agent:
            return LoopResult(
                success=False,
                iterations=0,
                final_output={},
                error=f"Generator agent {generator_name} not found in graph.",
            )

        payload = dict(initial_input)
        history = []

        for i in range(1, max_iterations + 1):
            req = AgentRequest(task="generate", params=payload)
            res: AgentResult = await agent.run(req)
            output = res.output if isinstance(res.output, dict) else {"result": res.output}

            passed, critique = evaluator_fn(output)
            history.append({
                "iteration": i,
                "output": output,
                "passed": passed,
                "critique": critique,
            })

            if passed:
                return LoopResult(
                    success=True,
                    iterations=i,
                    final_output=output,
                    history=history,
                )

            # Inject differential feedback for the next cycle
            payload["previous_critique"] = critique
            payload["iteration"] = i + 1

        return LoopResult(
            success=False,
            iterations=max_iterations,
            final_output=output,
            history=history,
            error=f"Exceeded max iterations ({max_iterations}) without passing evaluation.",
        )
