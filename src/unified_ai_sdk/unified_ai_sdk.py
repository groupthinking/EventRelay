"""Unified interface for Gemini, Anthropic, and OpenAI requests."""

from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable

from .rate_limiter import ModelProvider, RateLimiter

logger = logging.getLogger(__name__)

try:
    from google import genai as _genai
    from google.genai import types as _genai_types

    _GENAI_AVAILABLE = True
except ImportError:
    _genai = None
    _genai_types = None
    _GENAI_AVAILABLE = False

try:
    import anthropic as _anthropic_sdk

    _ANTHROPIC_AVAILABLE = True
except ImportError:
    _anthropic_sdk = None
    _ANTHROPIC_AVAILABLE = False

try:
    import openai as _openai_sdk

    _OPENAI_AVAILABLE = True
except ImportError:
    _openai_sdk = None
    _OPENAI_AVAILABLE = False


class TaskType(Enum):
    """Task types for AI processing."""

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
    """Request object for AI operations."""

    prompt: str
    model: str
    provider: ModelProvider | str
    task_type: TaskType
    temperature: float = 0.7
    max_tokens: int = 4000
    structured_output: bool = False


@dataclass
class AIResponse:
    """Response object from AI operations."""

    content: str
    model: str
    provider: str
    success: bool = True
    tokens_used: int = 0
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class UnifiedAISDK:
    """Unified AI client with provider-specific routing and retries."""

    def __init__(self, config: dict[str, Any] | None = None):
        self.config = config if config is not None else {}
        self.retry_attempts = max(1, int(self.config.get("retry_attempts", 3)))
        self.retry_base_delay = float(self.config.get("retry_base_delay", 1.0))
        self.retry_max_delay = float(self.config.get("retry_max_delay", 8.0))
        self.rate_limiter = RateLimiter(self.config.get("rate_limits"))

        self._gemini_key = (
            self.config.get("gemini_api_key")
            or os.getenv("GEMINI_API_KEY")
            or os.getenv("GOOGLE_GENERATIVE_AI_API_KEY")
            or os.getenv("GOOGLE_API_KEY")
        )
        self._anthropic_key = (
            self.config.get("anthropic_api_key") or os.getenv("ANTHROPIC_API_KEY")
        )
        self._openai_key = self.config.get("openai_api_key") or os.getenv(
            "OPENAI_API_KEY"
        )

        self._gemini_client: object | None = None
        self._anthropic_client: object | None = None
        self._openai_client: object | None = None

        self._init_clients()

    async def unified_request(self, request: AIRequest) -> AIResponse:
        """Execute a provider-specific request with retry handling."""
        provider_name = self._normalize_provider(request.provider)
        provider = self._rate_limit_provider(provider_name)

        for attempt in range(1, self.retry_attempts + 1):
            try:
                await self.rate_limiter.wait_if_needed(provider, request.max_tokens)
                content, tokens_used = await asyncio.to_thread(
                    self._dispatch_sync, provider_name, request
                )
                return AIResponse(
                    content=content,
                    model=request.model,
                    provider=provider_name,
                    success=True,
                    tokens_used=tokens_used,
                    metadata={
                        "task_type": request.task_type.value,
                        "temperature": request.temperature,
                        "max_tokens": request.max_tokens,
                        "attempts": attempt,
                    },
                )
            except Exception as exc:
                logger.warning(
                    "UnifiedAISDK %s attempt %s/%s failed: %s",
                    provider_name,
                    attempt,
                    self.retry_attempts,
                    exc,
                )
                if attempt >= self.retry_attempts:
                    return AIResponse(
                        content="",
                        model=request.model,
                        provider=provider_name,
                        success=False,
                        error=str(exc),
                        metadata={
                            "task_type": request.task_type.value,
                            "temperature": request.temperature,
                            "max_tokens": request.max_tokens,
                            "attempts": attempt,
                        },
                    )

                delay = min(
                    self.retry_base_delay * (2 ** (attempt - 1)),
                    self.retry_max_delay,
                )
                if delay > 0:
                    await asyncio.sleep(delay)

    async def health_check(self) -> dict[str, Any]:
        """Report which providers are ready for live traffic."""
        providers = {
            "gemini": {
                "configured": bool(self._gemini_key),
                "sdk_available": _GENAI_AVAILABLE,
                "ready": self._gemini_client is not None,
            },
            "anthropic": {
                "configured": bool(self._anthropic_key),
                "sdk_available": _ANTHROPIC_AVAILABLE,
                "ready": self._anthropic_client is not None,
            },
            "openai": {
                "configured": bool(self._openai_key),
                "sdk_available": _OPENAI_AVAILABLE,
                "ready": self._openai_client is not None,
            },
        }
        ready_count = sum(1 for info in providers.values() if info["ready"])
        return {
            "status": "ok" if ready_count else "degraded",
            "ready_providers": ready_count,
            "providers": providers,
        }

    def _init_clients(self) -> None:
        if _GENAI_AVAILABLE and self._gemini_key:
            try:
                self._gemini_client = _genai.Client(api_key=self._gemini_key)
            except Exception as exc:
                logger.warning("UnifiedAISDK failed to init Gemini client: %s", exc)

        if _ANTHROPIC_AVAILABLE and self._anthropic_key:
            try:
                self._anthropic_client = _anthropic_sdk.Anthropic(
                    api_key=self._anthropic_key
                )
            except Exception as exc:
                logger.warning("UnifiedAISDK failed to init Anthropic client: %s", exc)

        if _OPENAI_AVAILABLE and self._openai_key:
            try:
                self._openai_client = _openai_sdk.OpenAI(api_key=self._openai_key)
            except Exception as exc:
                logger.warning("UnifiedAISDK failed to init OpenAI client: %s", exc)

    def _normalize_provider(self, provider: ModelProvider | str) -> str:
        provider_name = (
            provider.value if isinstance(provider, ModelProvider) else str(provider)
        ).lower()
        if provider_name in {"claude", "anthropic"}:
            return "claude"
        if provider_name in {"openai", "gemini"}:
            return provider_name
        raise ValueError(f"Unsupported provider: {provider_name}")

    def _rate_limit_provider(self, provider_name: str) -> ModelProvider:
        if provider_name == "claude":
            return ModelProvider.CLAUDE
        if provider_name == "openai":
            return ModelProvider.OPENAI
        return ModelProvider.GEMINI

    def _dispatch_sync(self, provider_name: str, request: AIRequest) -> tuple[str, int]:
        handlers: dict[str, Callable[[AIRequest], tuple[str, int]]] = {
            "openai": self._generate_openai,
            "claude": self._generate_anthropic,
            "gemini": self._generate_gemini,
        }
        handler = handlers[provider_name]
        content, tokens_used = handler(request)
        if not content:
            raise RuntimeError(f"{provider_name} returned empty content")
        return content, tokens_used

    def _generate_openai(self, request: AIRequest) -> tuple[str, int]:
        if self._openai_client is None:
            raise RuntimeError("OpenAI client is not configured")
        response = self._openai_client.chat.completions.create(  # type: ignore[attr-defined]
            model=request.model,
            messages=[{"role": "user", "content": request.prompt}],
            max_tokens=request.max_tokens,
            temperature=request.temperature,
        )
        content = response.choices[0].message.content or ""
        usage = getattr(response, "usage", None)
        tokens_used = int(getattr(usage, "total_tokens", 0) or 0)
        return content, tokens_used

    def _generate_anthropic(self, request: AIRequest) -> tuple[str, int]:
        if self._anthropic_client is None:
            raise RuntimeError("Anthropic client is not configured")
        response = self._anthropic_client.messages.create(  # type: ignore[attr-defined]
            model=request.model,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
            thinking={"type": "adaptive"},
            messages=[{"role": "user", "content": request.prompt}],
        )
        text_blocks = [block.text for block in response.content if block.type == "text"]
        usage = getattr(response, "usage", None)
        input_tokens = int(getattr(usage, "input_tokens", 0) or 0)
        output_tokens = int(getattr(usage, "output_tokens", 0) or 0)
        return "\n".join(text_blocks), input_tokens + output_tokens

    def _generate_gemini(self, request: AIRequest) -> tuple[str, int]:
        if self._gemini_client is None:
            raise RuntimeError("Gemini client is not configured")
        kwargs: dict[str, Any] = {"model": request.model, "contents": request.prompt}
        if _GENAI_AVAILABLE and _genai_types is not None:
            kwargs["config"] = _genai_types.GenerateContentConfig(
                temperature=request.temperature,
                max_output_tokens=request.max_tokens,
            )
        response = self._gemini_client.models.generate_content(**kwargs)  # type: ignore[attr-defined]
        text = response.text
        if text is None and response.candidates:
            parts = response.candidates[0].content.parts
            text_parts = [part.text for part in parts if getattr(part, "text", None)]
            text = "\n".join(text_parts) if text_parts else ""
        usage = getattr(response, "usage_metadata", None)
        tokens_used = int(getattr(usage, "total_token_count", 0) or 0)
        return text or "", tokens_used
