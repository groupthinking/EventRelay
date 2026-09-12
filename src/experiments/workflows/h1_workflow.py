"""Hypothesis h1 workflow."""

from __future__ import annotations

from typing import Any, Mapping

from .base import HypothesisWorkflow


class H1Workflow(HypothesisWorkflow):
    hypothesis_id = "h1"
    title = "Retrieval quality gating"
    description = "Validate that strong retrieval quality improves downstream task completion."
    expected_signals = ("retrieval_precision", "task_completion", "latency")

    def run(self, context: Mapping[str, Any] | None = None) -> dict[str, Any]:
        data = super().run(context)
        data["steps"] = [
            "measure retrieval precision",
            "compare top-k candidates",
            "score task completion lift",
        ]
        return data
