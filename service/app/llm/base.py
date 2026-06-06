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
        """Run the model and return a parsed JSON object matching `schema`."""
        ...
