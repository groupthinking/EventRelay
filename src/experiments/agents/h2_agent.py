"""Hypothesis h2 agent."""

from __future__ import annotations

from typing import Any, Mapping

from .base import HypothesisAgent


class H2Agent(HypothesisAgent):
    hypothesis_id = "h2"
    role = "context optimizer"

    def run(self, workflow_result: Mapping[str, Any] | None = None) -> dict[str, Any]:
        payload = super().run(workflow_result)
        payload["summary"] = "Context compression must retain task-critical signals for h2."
        return payload
