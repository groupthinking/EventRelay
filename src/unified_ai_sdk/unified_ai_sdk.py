"""Unified interface for Gemini, Anthropic, and OpenAI requests."""

from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Awaitable

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
        self.config = dict(config or {})
        retry_attempts = int(self.config.get("retry_attempts", 3))
        if retry_attempts < 1:
            raise ValueError("retry_attempts must be at least 1")
        self.retry_attempts = retry_attempts
        self.retry_base_delay = float(self.config.get("retry_base_delay", 1.0))
        self.retry_max_delay = float(self.config.get("retry_max_delay", 8.0))
        # Bound per-request latency.
        self.request_timeout = float(self.config.get("request_timeout", 60.0))
        self.rate_limiter = RateLimiter(self.config.get("rate_limits"))

        self._gemini_key = (
            self.config.get("gemini_api_key")
            or os.getenv("GEMINI_API_KEY")
            or os.getenv("GOOGLE_GENERATIVE_AI_API_KEY")
            or os.getenv("GOOGLE_API_KEY")
        )
        self._anthropic_key = self.config.get("anthropic_api_key") or os.getenv(
            "ANTHROPIC_API_KEY"
        )
        self._openai_key = self.config.get("openai_api_key") or os.getenv(
            "OPENAI_API_KEY"
        )
        self._grok_key = (
            self.config.get("grok_api_key")
            or os.getenv("GROK_API_KEY")
            or os.getenv("XAI_API_KEY")
            or os.getenv("XAI_GROK4_API")
        )

        self._gemini_client: Any | None = None
        self._anthropic_client: Any | None = None
        self._openai_client: Any | None = None
        self._grok_client: Any | None = None

        self._handlers: dict[str, Callable[[AIRequest], Awaitable[tuple[str, int]]]] = {
            "openai": self._generate_openai,
            "claude": self._generate_anthropic,
            "gemini": self._generate_gemini,
            "grok": self._generate_grok,
        }

        self._init_clients()

    async def unified_request(self, request: AIRequest) -> AIResponse:
        """Execute a provider-specific request with retry handling."""
        try:
            provider_name = self._normalize_provider(request.provider)
        except ValueError as exc:
            return AIResponse(
                content="",
                model=request.model,
                provider=str(request.provider),
                success=False,
                error=str(exc),
                metadata={
                    "task_type": request.task_type.value,
                    "temperature": request.temperature,
                    "max_tokens": request.max_tokens,
                    "attempts": 0,
                },
            )
        provider = self._rate_limit_provider(provider_name)

        for attempt in range(1, self.retry_attempts + 1):
            try:
                await self.rate_limiter.wait_if_needed(provider, request.max_tokens)

                handler = self._handlers[provider_name]
                content, tokens_used = await handler(request)

                if not content:
                     raise RuntimeError(f"{provider_name} (model={request.model}) returned empty content")

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

                # Determine if we should retry
                should_retry = self._should_retry(exc)

                if attempt >= self.retry_attempts or not should_retry:
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

        raise RuntimeError("unified_request exhausted retries without returning")

    def _should_retry(self, exc: Exception) -> bool:
        """Determine if an exception warrants a retry."""
        # OpenAI/Grok exceptions
        if _OPENAI_AVAILABLE:
            if isinstance(exc, _openai_sdk.RateLimitError):
                return True
            if isinstance(exc, (_openai_sdk.APITimeoutError, _openai_sdk.InternalServerError)):
                return True
            if isinstance(exc, _openai_sdk.APIStatusError):
                # Retry on 5xx, but not 4xx (except 429)
                return exc.status_code >= 500

        # Anthropic exceptions
        if _ANTHROPIC_AVAILABLE:
            if isinstance(exc, _anthropic_sdk.RateLimitError):
                return True
            if isinstance(exc, (_anthropic_sdk.APITimeoutError, _anthropic_sdk.InternalServerError)):
                return True
            if isinstance(exc, _anthropic_sdk.APIStatusError):
                return exc.status_code >= 500

        # General network errors or specific string-based checks for Gemini
        exc_str = str(exc).lower()
        if "timeout" in exc_str or "deadline exceeded" in exc_str:
            return True
        if "rate limit" in exc_str or "429" in exc_str:
            return True
        if "internal server error" in exc_str or "500" in exc_str or "503" in exc_str:
            return True

        # Auth and Validation errors should not be retried
        if any(term in exc_str for term in ["authentication", "unauthorized", "api_key", "invalid_request", "400", "401", "403"]):
            return False

        return True

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
            "grok": {
                "configured": bool(self._grok_key),
                "sdk_available": _OPENAI_AVAILABLE,
                "ready": self._grok_client is not None,
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
                self._anthropic_client = _anthropic_sdk.AsyncAnthropic(
                    api_key=self._anthropic_key
                )
            except Exception as exc:
                logger.warning("UnifiedAISDK failed to init Anthropic client: %s", exc)

        if _OPENAI_AVAILABLE and self._openai_key:
            try:
                self._openai_client = _openai_sdk.AsyncOpenAI(api_key=self._openai_key)
            except Exception as exc:
                logger.warning("UnifiedAISDK failed to init OpenAI client: %s", exc)

        if _OPENAI_AVAILABLE and self._grok_key:
            try:
                self._grok_client = _openai_sdk.AsyncOpenAI(
                    api_key=self._grok_key,
                    base_url="https://api.x.ai/v1"
                )
            except Exception as exc:
                logger.warning("UnifiedAISDK failed to init Grok client: %s", exc)

    def _normalize_provider(self, provider: ModelProvider | str) -> str:
        provider_name = (
            provider.value if isinstance(provider, ModelProvider) else str(provider)
        ).lower()
        if provider_name in {"claude", "anthropic"}:
            return "claude"
        if provider_name in {"openai", "gemini", "grok"}:
            return provider_name
        raise ValueError(f"Unsupported provider: {provider_name}")

    def _rate_limit_provider(self, provider_name: str) -> ModelProvider:
        if provider_name == "claude":
            return ModelProvider.CLAUDE
        if provider_name == "openai":
            return ModelProvider.OPENAI
        if provider_name == "grok":
            return ModelProvider.GROK
        return ModelProvider.GEMINI

    async def _generate_openai(self, request: AIRequest) -> tuple[str, int]:
        if self._openai_client is None:
            raise RuntimeError(f"OpenAI client is not configured for {request.model}")

        kwargs: dict[str, Any] = {
            "model": request.model,
            "messages": [{"role": "user", "content": request.prompt}],
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
            "timeout": self.request_timeout,
        }

        if request.structured_output:
            kwargs["response_format"] = {"type": "json_object"}

        try:
            response = await self._openai_client.chat.completions.create(**kwargs)
            choices = getattr(response, "choices", None)
            if not choices or len(choices) == 0:
                raise RuntimeError(f"OpenAI ({request.model}) returned no choices")

            content = choices[0].message.content or ""
            usage = getattr(response, "usage", None)
            tokens_used = int(getattr(usage, "total_tokens", 0) or 0)
            return content, tokens_used

        except _openai_sdk.RateLimitError as exc:
            logger.error("OpenAI Rate Limit: %s", exc)
            raise
        except _openai_sdk.APITimeoutError as exc:
            logger.error("OpenAI Timeout: %s", exc)
            raise
        except _openai_sdk.APIStatusError as exc:
            logger.error("OpenAI Status Error (status=%s): %s", exc.status_code, exc.message)
            raise
        except Exception as exc:
            logger.error("OpenAI Unexpected Error: %s", exc)
            raise

    async def _generate_anthropic(self, request: AIRequest) -> tuple[str, int]:
        if self._anthropic_client is None:
            raise RuntimeError(f"Anthropic client is not configured for {request.model}")

        kwargs: dict[str, Any] = {
            "model": request.model,
            "max_tokens": request.max_tokens,
            "messages": [{"role": "user", "content": request.prompt}],
            "timeout": self.request_timeout,
        }

        # Handle adaptive thinking (requires no temperature != 1)
        # Based on existing codebase patterns
        kwargs["thinking"] = {"type": "adaptive"}

        if request.structured_output:
            # Anthropic doesn't have a direct equivalent to response_format="json"
            # in the same way, but we can nudge it via system prompt or
            # assume the user does it. For robustness, we'll just log and proceed.
            logger.debug("Anthropic: structured_output requested, ensure prompt specifies JSON.")

        try:
            response = await self._anthropic_client.messages.create(**kwargs)
            text_blocks = [
                getattr(block, "text", "")
                for block in response.content
                if getattr(block, "type", None) == "text"
            ]
            usage = getattr(response, "usage", None)
            input_tokens = int(getattr(usage, "input_tokens", 0) or 0)
            output_tokens = int(getattr(usage, "output_tokens", 0) or 0)
            return "\n".join(text_blocks), input_tokens + output_tokens

        except _anthropic_sdk.RateLimitError as exc:
            logger.error("Anthropic Rate Limit: %s", exc)
            raise
        except _anthropic_sdk.APITimeoutError as exc:
            logger.error("Anthropic Timeout: %s", exc)
            raise
        except _anthropic_sdk.APIStatusError as exc:
            logger.error("Anthropic Status Error (status=%s): %s", exc.status_code, exc.message)
            raise
        except Exception as exc:
            logger.error("Anthropic Unexpected Error: %s", exc)
            raise

    async def _generate_gemini(self, request: AIRequest) -> tuple[str, int]:
        if self._gemini_client is None:
            raise RuntimeError(f"Gemini client is not configured for {request.model}")

        config_kwargs: dict[str, Any] = {
            "temperature": request.temperature,
            "max_output_tokens": request.max_tokens,
        }

        if request.structured_output:
            config_kwargs["response_mime_type"] = "application/json"

        try:
            # Use the asynchronous aio namespace
            response = await self._gemini_client.aio.models.generate_content(
                model=request.model,
                contents=request.prompt,
                config=_genai_types.GenerateContentConfig(**config_kwargs) if _genai_types else None
            )

            text = response.text
            if text is None and not getattr(response, "candidates", None):
                raise RuntimeError(f"Gemini ({request.model}) returned no candidates")
            if text is None:
                parts = response.candidates[0].content.parts
                text_parts = [part.text for part in parts if getattr(part, "text", None)]
                text = "\n".join(text_parts) if text_parts else ""

            usage = getattr(response, "usage_metadata", None)
            tokens_used = int(getattr(usage, "total_token_count", 0) or 0)
            return text or "", tokens_used

        except Exception as exc:
            logger.error("Gemini Unexpected Error: %s", exc)
            raise

    async def _generate_grok(self, request: AIRequest) -> tuple[str, int]:
        if self._grok_client is None:
            raise RuntimeError(f"Grok client is not configured for {request.model}")

        kwargs: dict[str, Any] = {
            "model": request.model,
            "messages": [{"role": "user", "content": request.prompt}],
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
            "timeout": self.request_timeout,
        }

        # Grok API supports similar response_format as OpenAI
        if request.structured_output:
            kwargs["response_format"] = {"type": "json_object"}

        try:
            response = await self._grok_client.chat.completions.create(**kwargs)
            choices = getattr(response, "choices", None)
            if not choices or len(choices) == 0:
                raise RuntimeError(f"Grok ({request.model}) returned no choices")

            content = choices[0].message.content or ""
            usage = getattr(response, "usage", None)
            tokens_used = int(getattr(usage, "total_tokens", 0) or 0)
            return content, tokens_used

        except _openai_sdk.RateLimitError as exc:
            logger.error("Grok Rate Limit: %s", exc)
            raise
        except _openai_sdk.APITimeoutError as exc:
            logger.error("Grok Timeout: %s", exc)
            raise
        except _openai_sdk.APIStatusError as exc:
            logger.error("Grok Status Error (status=%s): %s", exc.status_code, exc.message)
            raise
        except Exception as exc:
            logger.error("Grok Unexpected Error: %s", exc)
            raise
