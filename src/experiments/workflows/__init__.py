"""Workflow definitions for hypotheses h1, h2, and h3."""

from __future__ import annotations

from .base import HypothesisWorkflow
from .h1 import H1Workflow
from .h2 import H2Workflow
from .h3 import H3Workflow

HYPOTHESIS_WORKFLOWS: dict[str, type[HypothesisWorkflow]] = {
    "h1": H1Workflow,
    "h2": H2Workflow,
    "h3": H3Workflow,
}

__all__ = [
    "HYPOTHESIS_WORKFLOWS",
    "HypothesisWorkflow",
    "H1Workflow",
    "H2Workflow",
    "H3Workflow",
    "build_workflow",
]


def build_workflow(name: str) -> HypothesisWorkflow:
    """Instantiate the workflow for a given hypothesis identifier."""
    normalized = (name or "").strip().lower()
    if normalized not in HYPOTHESIS_WORKFLOWS:
        raise ValueError(f"Unknown hypothesis workflow: {name!r}")
    return HYPOTHESIS_WORKFLOWS[normalized]()
