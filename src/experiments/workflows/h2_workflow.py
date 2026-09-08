"""Hypothesis h2 workflow."""

from __future__ import annotations

from typing import Any, Mapping

from .base import HypothesisWorkflow


class H2Workflow(HypothesisWorkflow):
    hypothesis_id = "h2"
    title = "Structured context compression"
    description = "Validate that compressed context preserves enough signal for action quality."
    expected_signals = ("context_density", "hallucination_rate", "action_quality")

    def run(self, context: Mapping[str, Any] | None = None) -> dict[str, Any]:
        data = super().run(context)
        data["steps"] = [
            "compress context to a summary",
            "compare baseline vs compressed prompts",
            "measure task quality drift",
        ]
        return data
