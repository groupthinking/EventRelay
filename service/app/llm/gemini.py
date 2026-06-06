"""Gemini adapter — the default production implementation of the model seam.

Chosen as default because the product pipeline is Gemini-primary (the legacy
flow is three Gemini agents). Anthropic/OpenAI adapters are drop-in: implement
the same `generate_json` and swap in the container.

NOTE: this adapter is not exercised by the test suite (no SDK/key in CI). The
google-genai import is lazy so the package imports cleanly without it.
"""
from __future__ import annotations

import asyncio
import json
from typing import Any

from .base import LLMError


class GeminiLLMClient:
    def __init__(self, api_key: str, model: str = "gemini-2.5-flash") -> None:
        self._api_key = api_key
        self._model = model
        self._client: Any | None = None

    def _ensure_client(self) -> Any:
        if self._client is None:
            try:
                from google import genai
            except ImportError as exc:  # pragma: no cover - depends on optional dep
                raise LLMError("google-genai is not installed") from exc
            self._client = genai.Client(api_key=self._api_key)
        return self._client

    async def generate_json(
        self, *, system: str, prompt: str, schema: dict[str, Any]
    ) -> dict[str, Any]:
        client = self._ensure_client()

        def _call() -> str:
            from google.genai import types

            response = client.models.generate_content(
                model=self._model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system,
                    response_mime_type="application/json",
                    response_schema=schema,
                ),
            )
            return response.text or ""

        text = await asyncio.to_thread(_call)
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise LLMError(f"model did not return valid JSON: {exc}") from exc
        if not isinstance(data, dict):
            raise LLMError("model JSON was not an object")
        return data
