"""
Unified AI SDK
==============

Provides a unified interface for multiple AI providers: Anthropic Claude,
OpenAI, xAI Grok, and Google Gemini.

API keys are read from the ``config`` dict passed to ``UnifiedAISDK.__init__``
(keys: ``anthropic_api_key``, ``openai_api_key``, ``xai_api_key``,
``gemini_api_key``) or from the corresponding environment variables
(``ANTHROPIC_API_KEY``, ``OPENAI_API_KEY``, ``XAI_API_KEY``/``XAI_GROK4_API``,
``GEMINI_API_KEY``).
"""

import logging
import os
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional, Union

import httpx

# Import ModelProvider from rate_limiter
from .rate_limiter import ModelProvider

logger = logging.getLogger(__name__)


class TaskType(Enum):
    """Task types for AI processing"""
    VIDEO_ANALYSIS = "video_analysis"
    CODE_GENERATION = "code_generation"
    TREND_ANALYSIS = "trend_analysis"
    STRATEGIC_PLANNING = "strategic_planning"
    CONTENT_GENERATION = "content_generation"
    DATA_ANALYSIS = "data_analysis"
    QUESTION_ANSWERING = "question_answering"
    SUMMARIZATION = "summarization"
    TRANSLATION = "translation"
    GENERIC = "generic"


@dataclass
class AIRequest:
    """Request object for AI operations"""
    prompt: str
    model: str
    provider: Union[ModelProvider, str]  # ModelProvider enum or string
    task_type: TaskType
    temperature: float = 0.7
    max_tokens: int = 4000
    structured_output: bool = False


@dataclass
class AIResponse:
    """Response object from AI operations"""
    content: str
    model: str
    provider: str
    success: bool = True
    tokens_used: int = 0
    error: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)


class UnifiedAISDK:
    """Unified interface for multiple AI providers."""

    _ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
    _OPENAI_URL = "https://api.openai.com/v1/chat/completions"
    _GROK_URL = "https://api.x.ai/v1/chat/completions"
    _GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"

    def __init__(self, config: Optional[dict[str, Any]] = None):
        """
        Initialize Unified AI SDK.

        Args:
            config: Configuration dict with API keys and settings.
                    Supported keys: ``anthropic_api_key``, ``openai_api_key``,
                    ``xai_api_key``, ``gemini_api_key``.
        """
        self.config = config if config is not None else {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def unified_request(self, request: AIRequest) -> AIResponse:
        """
        Execute a unified AI request, dispatching to the appropriate provider.

        Returns an ``AIResponse`` with ``success=False`` and a descriptive
        ``error`` field when the provider is not configured or the call fails.
        Never returns a fabricated success payload.
        """
        provider_name = (
            request.provider.value
            if isinstance(request.provider, ModelProvider)
            else str(request.provider)
        )

        try:
            provider = self._resolve_provider(request.provider)
        except ValueError:
            return AIResponse(
                content="",
                model=request.model,
                provider=provider_name,
                success=False,
                error=f"Unknown provider: {request.provider}",
            )

        try:
            if provider == ModelProvider.CLAUDE:
                return await self._call_anthropic(request, provider_name)
            elif provider == ModelProvider.OPENAI:
                return await self._call_openai(request, provider_name)
            elif provider == ModelProvider.GROK:
                return await self._call_grok(request, provider_name)
            elif provider == ModelProvider.GEMINI:
                return await self._call_gemini(request, provider_name)
            else:
                return AIResponse(
                    content="",
                    model=request.model,
                    provider=provider_name,
                    success=False,
                    error=f"Unsupported provider: {provider}",
                )
        except Exception as exc:
            logger.error("unified_request failed for provider %s: %s", provider_name, exc)
            return AIResponse(
                content="",
                model=request.model,
                provider=provider_name,
                success=False,
                error=str(exc),
            )

    async def health_check(self) -> dict[str, Any]:
        """
        Check reachability for each configured provider.

        A provider is reported as ``"ok"`` only when the API key is present
        *and* a lightweight probe succeeds.  Missing keys are reported as
        ``"unconfigured"``.  Network or auth errors are reported as
        ``"error: <message>"``.
        """
        results: dict[str, str] = {}

        checks: list[tuple[str, Optional[str], Any]] = [
            ("claude", self._get_key("anthropic_api_key", "ANTHROPIC_API_KEY"), self._probe_anthropic),
            ("openai", self._get_key("openai_api_key", "OPENAI_API_KEY"), self._probe_openai),
            ("grok", self._get_key("xai_api_key", "XAI_API_KEY", "XAI_GROK4_API"), self._probe_grok),
            ("gemini", self._get_key("gemini_api_key", "GEMINI_API_KEY"), self._probe_gemini),
        ]

        for name, key, probe_fn in checks:
            if not key:
                results[name] = "unconfigured"
                continue
            try:
                await probe_fn(key)
                results[name] = "ok"
            except Exception as exc:
                results[name] = f"error: {exc}"

        overall = "ok" if all(v == "ok" for v in results.values()) else "degraded"
        return {"status": overall, "providers": results}

    # ------------------------------------------------------------------
    # Provider dispatch helpers
    # ------------------------------------------------------------------

    async def _call_anthropic(self, request: AIRequest, provider_name: str) -> AIResponse:
        api_key = self._get_key("anthropic_api_key", "ANTHROPIC_API_KEY")
        if not api_key:
            return AIResponse(
                content="",
                model=request.model,
                provider=provider_name,
                success=False,
                error="Anthropic API key not configured",
            )
        payload = {
            "model": request.model,
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
            "messages": [{"role": "user", "content": request.prompt}],
        }
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                self._ANTHROPIC_URL,
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json=payload,
            )
            response.raise_for_status()
        data = response.json()
        content = data["content"][0]["text"]
        usage = data.get("usage", {})
        return AIResponse(
            content=content,
            model=request.model,
            provider=provider_name,
            success=True,
            tokens_used=usage.get("input_tokens", 0) + usage.get("output_tokens", 0),
            metadata={"task_type": request.task_type.value},
        )

    async def _call_openai(self, request: AIRequest, provider_name: str) -> AIResponse:
        return await self._call_openai_compatible(
            request, provider_name,
            self._get_key("openai_api_key", "OPENAI_API_KEY"),
            self._OPENAI_URL,
            "OpenAI API key not configured",
        )

    async def _call_grok(self, request: AIRequest, provider_name: str) -> AIResponse:
        return await self._call_openai_compatible(
            request, provider_name,
            self._get_key("xai_api_key", "XAI_API_KEY", "XAI_GROK4_API"),
            self._GROK_URL,
            "xAI (Grok) API key not configured",
        )

    async def _call_openai_compatible(
        self,
        request: AIRequest,
        provider_name: str,
        api_key: Optional[str],
        url: str,
        missing_key_error: str,
    ) -> AIResponse:
        if not api_key:
            return AIResponse(
                content="",
                model=request.model,
                provider=provider_name,
                success=False,
                error=missing_key_error,
            )
        payload = {
            "model": request.model,
            "messages": [{"role": "user", "content": request.prompt}],
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
        }
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                url,
                headers={"Authorization": "Bearer " + api_key, "Content-Type": "application/json"},
                json=payload,
            )
            response.raise_for_status()
        data = response.json()
        content = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})
        return AIResponse(
            content=content,
            model=request.model,
            provider=provider_name,
            success=True,
            tokens_used=usage.get("total_tokens", 0),
            metadata={"task_type": request.task_type.value},
        )

    async def _call_gemini(self, request: AIRequest, provider_name: str) -> AIResponse:
        api_key = self._get_key("gemini_api_key", "GEMINI_API_KEY")
        if not api_key:
            return AIResponse(
                content="",
                model=request.model,
                provider=provider_name,
                success=False,
                error="Gemini API key not configured",
            )
        url = f"{self._GEMINI_BASE_URL}/models/{request.model}:generateContent"
        payload = {
            "contents": [{"parts": [{"text": request.prompt}]}],
            "generationConfig": {
                "temperature": request.temperature,
                "maxOutputTokens": request.max_tokens,
            },
        }
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(url, params={"key": api_key}, json=payload)
            response.raise_for_status()
        data = response.json()
        content = data["candidates"][0]["content"]["parts"][0]["text"]
        return AIResponse(
            content=content,
            model=request.model,
            provider=provider_name,
            success=True,
            metadata={"task_type": request.task_type.value},
        )

    # ------------------------------------------------------------------
    # Probe helpers (lightweight reachability checks)
    # ------------------------------------------------------------------

    async def _probe_anthropic(self, api_key: str) -> None:
        """Minimal Anthropic API probe (single-token request)."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                self._ANTHROPIC_URL,
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={"model": "claude-haiku-4-5", "max_tokens": 1, "messages": [{"role": "user", "content": "hi"}]},
            )
            response.raise_for_status()

    async def _probe_openai(self, api_key: str) -> None:
        """Minimal OpenAI models-list probe."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                "https://api.openai.com/v1/models",
                headers={"Authorization": "Bearer " + api_key},
            )
            response.raise_for_status()

    async def _probe_grok(self, api_key: str) -> None:
        """Minimal xAI models-list probe."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                "https://api.x.ai/v1/models",
                headers={"Authorization": "Bearer " + api_key},
            )
            response.raise_for_status()

    async def _probe_gemini(self, api_key: str) -> None:
        """Minimal Gemini models-list probe."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{self._GEMINI_BASE_URL}/models",
                params={"key": api_key},
            )
            response.raise_for_status()

    # ------------------------------------------------------------------
    # Internal utilities
    # ------------------------------------------------------------------

    def _get_key(self, config_key: str, *env_vars: str) -> Optional[str]:
        """Return the first non-empty API key from config or environment."""
        value: str = self.config.get(config_key, "")
        if value:
            return value
        for var in env_vars:
            value = os.getenv(var, "")
            if value:
                return value
        return None

    @staticmethod
    def _resolve_provider(provider: Union[ModelProvider, str]) -> ModelProvider:
        if isinstance(provider, ModelProvider):
            return provider
        try:
            return ModelProvider(str(provider).lower())
        except ValueError:
            raise ValueError(f"Unknown provider: {provider}")
