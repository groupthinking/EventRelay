"""Test double for the model seam.

Not a production path. Returns canned responses in order, so the pipeline's
parsing/validation/lifecycle can be tested without a live provider. This is a
dependency-injected test fake, not a mock baked into production code.
"""
from __future__ import annotations

from typing import Any


class FakeLLMClient:
    def __init__(self, responses: list[dict[str, Any]]) -> None:
        """
        Initialize the fake LLM client with a sequence of canned JSON-like responses for testing.
        
        Parameters:
            responses (list[dict[str, Any]]): Sequence of predefined response dictionaries; a shallow copy is stored internally and will be returned in order by subsequent invocations.
        
        Notes:
            Sets up internal state:
              - self._responses: copied list of responses
              - self._i: next-response index, initialized to 0
              - self.calls: empty list for recording invocation details
        """
        self._responses = list(responses)
        self._i = 0
        self.calls: list[dict[str, Any]] = []

    async def generate_json(
        self, *, system: str, prompt: str, schema: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Retrieve the next pre-canned JSON-like response and record the invocation details.
        
        Parameters:
            system (str): System-level prompt or instructions supplied to the LLM.
            prompt (str): User-facing prompt text supplied to the LLM.
            schema (dict[str, Any]): JSON schema describing the expected structure of the response.
        
        Returns:
            dict[str, Any]: The next canned response dictionary from the fake client's response sequence.
        
        Raises:
            AssertionError: If there are no remaining canned responses to return.
        """
        self.calls.append({"system": system, "prompt": prompt, "schema": schema})
        if self._i >= len(self._responses):
            raise AssertionError("FakeLLMClient: no more canned responses")
        response = self._responses[self._i]
        self._i += 1
        return response
