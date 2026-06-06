"""Test double for the model seam.

Not a production path. Returns canned responses in order, so the pipeline's
parsing/validation/lifecycle can be tested without a live provider. This is a
dependency-injected test fake, not a mock baked into production code.
"""
from __future__ import annotations

from typing import Any


class FakeLLMClient:
    def __init__(self, responses: list[dict[str, Any]]) -> None:
        self._responses = list(responses)
        self._i = 0
        self.calls: list[dict[str, Any]] = []

    async def generate_json(
        self, *, system: str, prompt: str, schema: dict[str, Any]
    ) -> dict[str, Any]:
        self.calls.append({"system": system, "prompt": prompt, "schema": schema})
        if self._i >= len(self._responses):
            raise AssertionError("FakeLLMClient: no more canned responses")
        response = self._responses[self._i]
        self._i += 1
        return response
