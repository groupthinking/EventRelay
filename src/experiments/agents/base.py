"""Base logic shared by all hypothesis agents."""

from __future__ import annotations

from typing import Any, Mapping


class HypothesisAgent:
    """Small agent shell that interprets workflow outputs."""

    hypothesis_id: str = ""
    role: str = "experiment analyst"

    def run(self, workflow_result: Mapping[str, Any] | None = None) -> dict[str, Any]:
        payload = dict(workflow_result or {})
        return {
            "hypothesis": self.hypothesis_id,
            "role": self.role,
            "status": "ready",
            "summary": f"{self.role} validated {self.hypothesis_id}.",
            "signals": payload.get("signals", []),
        }
