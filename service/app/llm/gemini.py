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
import logging
from typing import Any

from .base import LLMError

logger = logging.getLogger(__name__)


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
        schema_summary = {k: type(v).__name__ for k, v in list(schema.items())[:3]}
        logger.info(
            "generate_json: invoking LLM",
            extra={
                "model": self._model,
                "prompt_length": len(prompt),
                "schema_summary": schema_summary,
            },
        )

        def _call() -> str:
            from google.genai import types

            try:
                logger.debug(
                    "_call: calling client.models.generate_content",
                    extra={"model": self._model},
                )
                response = client.models.generate_content(
                    model=self._model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=system,
                        response_mime_type="application/json",
                        response_schema=schema,
                    ),
                )
                logger.debug(
                    "_call: response received",
                    extra={"response_text_length": len(response.text or "")},
                )
                return response.text or ""
            except Exception as exc:
                logger.error(
                    "client.models.generate_content failed",
                    extra={
                        "model": self._model,
                        "error": str(exc),
                        "error_type": type(exc).__name__,
                    },
                    exc_info=True,
                )
                raise LLMError(f"model API call failed: {exc}") from exc

        text = await asyncio.to_thread(_call)
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            logger.error(
                "generate_json: JSON decode failed",
                extra={"text_length": len(text), "error": str(exc)},
                exc_info=True,
            )
            raise LLMError(f"model did not return valid JSON: {exc}") from exc
        if not isinstance(data, dict):
            raise LLMError("model JSON was not an object")
        logger.debug(
            "generate_json: success", extra={"response_keys": list(data.keys())}
        )
        return data
