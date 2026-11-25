"""Base workflow contract used by all experiment hypotheses."""

from __future__ import annotations

from typing import Any, Mapping


class HypothesisWorkflow:
    """Common interface for all hypothesis validation workflows."""

    hypothesis_id: str = ""
    title: str = ""
    description: str = ""
    expected_signals: tuple[str, ...] = ()

    def run(self, context: Mapping[str, Any] | None = None) -> dict[str, Any]:
        payload = dict(context or {})
        return {
            "hypothesis": self.hypothesis_id,
            "title": self.title,
            "description": self.description,
            "status": "ready",
            "context": payload,
            "steps": ["define hypothesis", "collect evidence", "validate outcome"],
            "signals": list(self.expected_signals),
        }
