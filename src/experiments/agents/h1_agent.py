"""Hypothesis h1 agent."""

from __future__ import annotations

from typing import Any, Mapping

from .base import HypothesisAgent


class H1Agent(HypothesisAgent):
    hypothesis_id = "h1"
    role = "retrieval analyst"

    def run(self, workflow_result: Mapping[str, Any] | None = None) -> dict[str, Any]:
        payload = super().run(workflow_result)
        payload["summary"] = "Retrieval quality is the dominant gating signal for h1."
        return payload
