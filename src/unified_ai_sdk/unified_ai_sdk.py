"""
Unified AI SDK
==============

Real provider integrations for OpenAI, Anthropic, and Google Gemini behind a
single async interface. Handles provider routing, API key loading, rate-limiter
integration, structured output, response mapping, retries with exponential
backoff, and per-provider health checks.

Public surface preserved:
    - TaskType
    - AIRequest
    - AIResponse
    - UnifiedAISDK.unified_request(...)
    - UnifiedAISDK.health_check(...)
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import random
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional, Union

from .rate_limiter import ModelProvider, RateLimiter

logger = logging.getLogger(__name__)


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
    provider: Union[ModelProvider, str]
    task_type: TaskType
    temperature: float = 0.7
    max_tokens: int = 4000
    structured_output: bool = False
    system_prompt: Optional[str] = None
    response_schema: Optional[dict[str, Any]] = None


@dataclass
class AIResponse:
    """Response object from AI operations."""

    content: str
    model: str
    provider: str
    success: bool = True
    tokens_used: int = 0
    error: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)


_RETRYABLE_STATUS_CODES = {408, 409, 425, 429, 500, 502, 503, 504}
_DEFAULT_MAX_RETRIES = 3
_DEFAULT_BACKOFF_BASE = 0.5
_DEFAULT_BACKOFF_MAX = 8.0
_HEALTH_CHECK_TIMEOUT = 5.0


def _resolve_provider(
    provider: Union[ModelProvider, str, None],
) -> Optional[ModelProvider]:
    """Coerce a provider input (enum, string, None) into a ModelProvider."""
    if provider is None:
        return None
    if isinstance(provider, ModelProvider):
        return provider
    try:
        return ModelProvider(str(provider).lower())
    except ValueError:
        return None


def _is_retryable_error(exc: BaseException) -> bool:
    """Decide whether an exception looks like a transient, retryable failure."""
    status = getattr(exc, "status_code", None) or getattr(exc, "status", None)
    if isinstance(status, int) and status in _RETRYABLE_STATUS_CODES:
        return True

    response = getattr(exc, "response", None)
    if response is not None:
        resp_status = getattr(response, "status_code", None) or getattr(
            response, "status", None
        )
        if isinstance(resp_status, int) and resp_status in _RETRYABLE_STATUS_CODES:
            return True

    name = type(exc).__name__.lower()
    retryable_markers = (
        "ratelimit",
        "rate_limit",
        "timeout",
        "overloaded",
        "serviceunavailable",
        "service_unavailable",
        "apiconnection",
        "internalserver",
        "resourceexhausted",
        "deadline",
    )
    if any(marker in name for marker in retryable_markers):
        return True

    message = str(exc).lower()
    if any(
        token in message
        for token in ("429", "503", "overloaded", "rate limit", "temporarily unavailable")
    ):
        return True
    return False


async def _with_retries(
    func: Callable[[], Any],
    *,
    max_retries: int = _DEFAULT_MAX_RETRIES,
    base_delay: float = _DEFAULT_BACKOFF_BASE,
    max_delay: float = _DEFAULT_BACKOFF_MAX,
) -> Any:
    """Execute an async callable with exponential backoff on retryable errors."""
    attempt = 0
    while True:
        try:
            return await func()
        except Exception as exc:  # noqa: BLE001 - intentional broad retry boundary
            attempt += 1
            if attempt > max_retries or not _is_retryable_error(exc):
                raise
            delay = min(max_delay, base_delay * (2 ** (attempt - 1)))
            delay += random.uniform(0, delay * 0.2)
            logger.warning(
                "Retryable provider error (attempt %d/%d): %s — sleeping %.2fs",
                attempt,
                max_retries,
                exc,
                delay,
            )
            await asyncio.sleep(delay)


class UnifiedAISDK:
    """Unified interface for OpenAI, Anthropic, and Google Gemini."""

    def __init__(self, config: Optional[dict[str, Any]] = None):
        self.config = config if config is not None else {}
        rate_config = self.config.get("rate_limits") or self.config.get("rate_limiter") or {}
        self.rate_limiter: RateLimiter = self.config.get("rate_limiter_instance") or RateLimiter(
            rate_config
        )

        retry_cfg = self.config.get("retry", {}) or {}
        self.max_retries = int(retry_cfg.get("max_retries", _DEFAULT_MAX_RETRIES))
        self.base_delay = float(retry_cfg.get("base_delay", _DEFAULT_BACKOFF_BASE))
        self.max_delay = float(retry_cfg.get("max_delay", _DEFAULT_BACKOFF_MAX))

        self._api_keys: dict[ModelProvider, Optional[str]] = {
            ModelProvider.OPENAI: self._load_api_key("openai", "OPENAI_API_KEY"),
            ModelProvider.CLAUDE: self._load_api_key(
                "claude", "ANTHROPIC_API_KEY", alt_env=("CLAUDE_API_KEY",)
            ),
            ModelProvider.GEMINI: self._load_api_key(
                "gemini",
                "GEMINI_API_KEY",
                alt_env=("GOOGLE_API_KEY", "GOOGLE_GENAI_API_KEY"),
            ),
            ModelProvider.GROK: self._load_api_key(
                "grok", "GROK_API_KEY", alt_env=("XAI_API_KEY",)
            ),
        }

    def _load_api_key(
        self,
        config_key: str,
        env_key: str,
        alt_env: tuple[str, ...] = (),
    ) -> Optional[str]:
        """Load an API key from config (preferred) or environment."""
        api_keys_cfg = (self.config.get("api_keys") or {}) if self.config else {}
        if api_keys_cfg.get(config_key):
            return str(api_keys_cfg[config_key])
        if self.config.get(f"{config_key}_api_key"):
            return str(self.config[f"{config_key}_api_key"])
        value = os.environ.get(env_key)
        if value:
            return value
        for alt in alt_env:
            value = os.environ.get(alt)
            if value:
                return value
        return None

    async def unified_request(self, request: AIRequest) -> AIResponse:
        """
        Execute an AI request against the requested provider.

        Never raises on provider failure; on final failure returns
        AIResponse(success=False, error=..., content="").
        """
        provider_enum = _resolve_provider(request.provider)
        provider_name = (
            provider_enum.value
            if provider_enum is not None
            else str(request.provider)
        )

        if provider_enum is None:
            return AIResponse(
                content="",
                model=request.model,
                provider=provider_name,
                success=False,
                error=f"Unknown provider: {request.provider!r}",
            )

        api_key = self._api_keys.get(provider_enum)
        if not api_key:
            return AIResponse(
                content="",
                model=request.model,
                provider=provider_name,
                success=False,
                error=f"Missing API key for provider '{provider_name}'",
            )

        try:
            estimated_tokens = min(
                request.max_tokens + len(request.prompt.split()),
                request.max_tokens * 2,
            )
            await self.rate_limiter.wait_if_needed(provider_enum, tokens=estimated_tokens)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Rate limiter failure (non-fatal): %s", exc)

        dispatch = {
            ModelProvider.OPENAI: self._call_openai,
            ModelProvider.CLAUDE: self._call_anthropic,
            ModelProvider.GEMINI: self._call_gemini,
        }
        handler = dispatch.get(provider_enum)
        if handler is None:
            return AIResponse(
                content="",
                model=request.model,
                provider=provider_name,
                success=False,
                error=f"Provider '{provider_name}' is not supported by UnifiedAISDK",
            )

        try:
            return await _with_retries(
                lambda: handler(request, api_key),
                max_retries=self.max_retries,
                base_delay=self.base_delay,
                max_delay=self.max_delay,
            )
        except Exception as exc:  # noqa: BLE001 - final safety net
            logger.exception("unified_request failed for provider=%s", provider_name)
            return AIResponse(
                content="",
                model=request.model,
                provider=provider_name,
                success=False,
                error=f"{type(exc).__name__}: {exc}",
            )

    async def _call_openai(self, request: AIRequest, api_key: str) -> AIResponse:
        from openai import AsyncOpenAI  # type: ignore

        client = AsyncOpenAI(api_key=api_key)
        messages: list[dict[str, str]] = []
        if request.system_prompt:
            messages.append({"role": "system", "content": request.system_prompt})
        messages.append({"role": "user", "content": request.prompt})

        kwargs: dict[str, Any] = {
            "model": request.model,
            "messages": messages,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
        }
        if request.structured_output:
            kwargs["response_format"] = {"type": "json_object"}

        completion = await client.chat.completions.create(**kwargs)
        choice = completion.choices[0] if completion.choices else None
        content = (choice.message.content if choice and choice.message else "") or ""
        usage = getattr(completion, "usage", None)
        tokens_used = int(getattr(usage, "total_tokens", 0) or 0) if usage else 0
        finish_reason = getattr(choice, "finish_reason", None) if choice else None

        parsed: Any = None
        if request.structured_output and content:
            try:
                parsed = json.loads(content)
            except (ValueError, TypeError):
                parsed = None

        return AIResponse(
            content=content,
            model=request.model,
            provider=ModelProvider.OPENAI.value,
            success=True,
            tokens_used=tokens_used,
            metadata={
                "task_type": request.task_type.value,
                "finish_reason": finish_reason,
                "structured": parsed if parsed is not None else None,
                "raw_id": getattr(completion, "id", None),
            },
        )

    async def _call_anthropic(self, request: AIRequest, api_key: str) -> AIResponse:
        from anthropic import AsyncAnthropic  # type: ignore

        client = AsyncAnthropic(api_key=api_key)
        kwargs: dict[str, Any] = {
            "model": request.model,
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
            "messages": [{"role": "user", "content": request.prompt}],
        }
        system_prompt = request.system_prompt
        if request.structured_output:
            json_instruction = (
                "Respond with a single JSON object only. No prose, no markdown fences."
            )
            system_prompt = (
                f"{system_prompt}\n\n{json_instruction}" if system_prompt else json_instruction
            )
        if system_prompt:
            kwargs["system"] = system_prompt

        message = await client.messages.create(**kwargs)

        parts: list[str] = []
        for block in getattr(message, "content", []) or []:
            text = getattr(block, "text", None)
            if text:
                parts.append(text)
        content = "".join(parts)

        usage = getattr(message, "usage", None)
        tokens_used = 0
        if usage is not None:
            tokens_used = int(getattr(usage, "input_tokens", 0) or 0) + int(
                getattr(usage, "output_tokens", 0) or 0
            )

        parsed: Any = None
        if request.structured_output and content:
            try:
                parsed = json.loads(content)
            except (ValueError, TypeError):
                parsed = None

        return AIResponse(
            content=content,
            model=request.model,
            provider=ModelProvider.CLAUDE.value,
            success=True,
            tokens_used=tokens_used,
            metadata={
                "task_type": request.task_type.value,
                "stop_reason": getattr(message, "stop_reason", None),
                "structured": parsed if parsed is not None else None,
                "raw_id": getattr(message, "id", None),
            },
        )

    async def _call_gemini(self, request: AIRequest, api_key: str) -> AIResponse:
        import google.generativeai as genai  # type: ignore

        generation_config: dict[str, Any] = {
            "temperature": request.temperature,
            "max_output_tokens": request.max_tokens,
        }
        if request.structured_output:
            generation_config["response_mime_type"] = "application/json"
            if request.response_schema:
                generation_config["response_schema"] = request.response_schema

        def _invoke() -> Any:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel(
                model_name=request.model,
                system_instruction=request.system_prompt,
                generation_config=generation_config,
            )
            return model.generate_content(request.prompt)

        response = await asyncio.to_thread(_invoke)

        content = getattr(response, "text", None)
        if not content:
            parts: list[str] = []
            for cand in getattr(response, "candidates", []) or []:
                cand_content = getattr(cand, "content", None)
                for part in getattr(cand_content, "parts", []) or []:
                    text = getattr(part, "text", None)
                    if text:
                        parts.append(text)
            content = "".join(parts)
        content = content or ""

        usage = getattr(response, "usage_metadata", None)
        tokens_used = 0
        if usage is not None:
            tokens_used = int(getattr(usage, "total_token_count", 0) or 0)
            if not tokens_used:
                tokens_used = int(
                    getattr(usage, "prompt_token_count", 0) or 0
                ) + int(getattr(usage, "candidates_token_count", 0) or 0)

        parsed: Any = None
        if request.structured_output and content:
            try:
                parsed = json.loads(content)
            except (ValueError, TypeError):
                parsed = None

        finish_reason = None
        candidates = getattr(response, "candidates", None)
        if candidates:
            finish_reason = getattr(candidates[0], "finish_reason", None)
            if finish_reason is not None and hasattr(finish_reason, "name"):
                finish_reason = finish_reason.name

        return AIResponse(
            content=content,
            model=request.model,
            provider=ModelProvider.GEMINI.value,
            success=True,
            tokens_used=tokens_used,
            metadata={
                "task_type": request.task_type.value,
                "finish_reason": finish_reason,
                "structured": parsed if parsed is not None else None,
            },
        )

    async def health_check(self) -> dict[str, Any]:
        """
        Check health of each configured provider with a 5-second per-call timeout.

        Returns a dict with:
            status: "healthy" | "degraded" | "unhealthy"
            providers: {provider_name: {"status": ..., "detail": ...}}
        """
        checks = {
            ModelProvider.OPENAI: self._health_openai,
            ModelProvider.CLAUDE: self._health_anthropic,
            ModelProvider.GEMINI: self._health_gemini,
        }

        results: dict[str, dict[str, Any]] = {}
        for provider, fn in checks.items():
            api_key = self._api_keys.get(provider)
            if not api_key:
                results[provider.value] = {
                    "status": "unconfigured",
                    "detail": "API key not set",
                }
                continue
            try:
                detail = await asyncio.wait_for(fn(api_key), timeout=_HEALTH_CHECK_TIMEOUT)
                results[provider.value] = {"status": "healthy", "detail": detail}
            except asyncio.TimeoutError:
                results[provider.value] = {
                    "status": "unhealthy",
                    "detail": f"timeout after {_HEALTH_CHECK_TIMEOUT}s",
                }
            except Exception as exc:  # noqa: BLE001
                results[provider.value] = {
                    "status": "unhealthy",
                    "detail": f"{type(exc).__name__}: {exc}",
                }

        configured = [r for r in results.values() if r["status"] != "unconfigured"]
        healthy = [r for r in configured if r["status"] == "healthy"]
        if not configured:
            aggregate = "unhealthy"
        elif len(healthy) == len(configured):
            aggregate = "healthy"
        elif healthy:
            aggregate = "degraded"
        else:
            aggregate = "unhealthy"

        return {"status": aggregate, "providers": results}

    async def _health_openai(self, api_key: str) -> str:
        from openai import AsyncOpenAI  # type: ignore

        client = AsyncOpenAI(api_key=api_key)
        page = await client.models.list()
        data = getattr(page, "data", None)
        count = len(list(data)) if data is not None else 0
        return f"models_listed={count}"

    async def _health_anthropic(self, api_key: str) -> str:
        from anthropic import AsyncAnthropic  # type: ignore

        client = AsyncAnthropic(api_key=api_key)
        models = getattr(client, "models", None)
        if models is not None and hasattr(models, "list"):
            page = await models.list()
            data = getattr(page, "data", None)
            count = len(list(data)) if data is not None else 0
            return f"models_listed={count}"
        await client.messages.create(
            model="claude-3-5-haiku-latest",
            max_tokens=1,
            messages=[{"role": "user", "content": "ping"}],
        )
        return "message_ok"

    async def _health_gemini(self, api_key: str) -> str:
        import google.generativeai as genai  # type: ignore

        def _probe() -> int:
            genai.configure(api_key=api_key)
            count = 0
            for _ in genai.list_models():
                count += 1
                if count >= 1:
                    break
            return count

        count = await asyncio.to_thread(_probe)
        return f"models_listed={count}"
