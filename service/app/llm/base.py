"""The single model-invocation seam.

One interface for "call a model and get structured JSON back". Providers live
behind it. This replaces the legacy repo's five competing seams (gemini_service,
hybrid_processor, llm_router, vercel_gateway, unified_ai_sdk).
"""
from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


class LLMError(RuntimeError):
    """Raised when a provider call fails or returns unusable output."""


@runtime_checkable
class LLMClient(Protocol):
    async def generate_json(
        self, *, system: str, prompt: str, schema: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Invoke the model with the given system instructions and prompt and return a JSON object conforming to the provided schema.
        
        Parameters:
            system (str): System-level instructions or context for the model.
            prompt (str): User-facing prompt to supply to the model.
            schema (dict[str, Any]): JSON-schema-like specification describing the expected structure and types of the returned object; used to validate and parse model output.
        
        Returns:
            dict[str, Any]: Parsed JSON object that conforms to `schema`.
        """
        ...
