"""Hypothesis h3 workflow."""

from __future__ import annotations

from typing import Any, Mapping

from .base import HypothesisWorkflow


class H3Workflow(HypothesisWorkflow):
    hypothesis_id = "h3"
    title = "Multi-agent coordination advantage"
    description = "Validate that specialized agent roles outperform a single generalist execution loop."
    expected_signals = ("coordination_quality", "coverage", "completion_rate")

    def run(self, context: Mapping[str, Any] | None = None) -> dict[str, Any]:
        data = super().run(context)
        data["steps"] = [
            "route work to specialists",
            "merge outputs into a single delivery",
            "compare coordination against monolithic execution",
        ]
        return data
