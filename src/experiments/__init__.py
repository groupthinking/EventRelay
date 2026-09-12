"""Experiment scaffolding for the three core hypotheses.

The repository intentionally keeps the experiment runtime small and explicit so
that hypothesis-driven validation can be exercised without coupling to the full
video pipeline.
"""

from __future__ import annotations

from typing import Any, Mapping

from .agents import HypothesisAgent, build_agent
from .workflows import HypothesisWorkflow, build_workflow

HYPOTHESIS_IDS = ("h1", "h2", "h3")

__all__ = [
    "HYPOTHESIS_IDS",
    "HypothesisAgent",
    "HypothesisWorkflow",
    "build_agent",
    "build_experiment",
    "build_workflow",
    "get_hypothesis_ids",
    "run_hypothesis",
]


def get_hypothesis_ids() -> tuple[str, ...]:
    """Return the canonical set of hypothesis identifiers."""
    return HYPOTHESIS_IDS


def build_experiment(name: str, *, context: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Create the workflow and agent for a given hypothesis."""
    workflow = build_workflow(name)
    agent = build_agent(name)
    payload = dict(context or {})
    result = workflow.run(payload)
    result["agent"] = agent.run(result)
    return result


def run_hypothesis(name: str, *, context: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Run a full hypothesis validation loop."""
    return build_experiment(name, context=context)
