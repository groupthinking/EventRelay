"""
Unified AI SDK
==============

Provides unified interface for multiple AI providers.
Requires provider API keys to be configured via environment variables
or passed in the config dict.
"""

import logging
import os
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional, Union

import httpx

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
    """
    Unified interface for multiple AI providers.

    Dispatches requests to the configured provider (OpenAI, Anthropic/Claude,
    Gemini, or Grok). Requires the appropriate API key to be set in the config
    or as an environment variable.
    """

    def __init__(self, config: Optional[dict[str, Any]] = None):
        """
        Initialize Unified AI SDK.

        Args:
            config: Configuration dict with API keys and settings.
                    Keys: openai_api_key, anthropic_api_key, gemini_api_key,
                          grok_api_key (or XAI_GROK4_API env var)
        """
        self.config = config if config is not None else {}
        self._client: Optional[httpx.AsyncClient] = None

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=60.0)
        return self._client

    def _get_api_key(self, provider_name: str) -> Optional[str]:
        """Resolve API key from config or environment."""
        key_map = {
            "openai": ("openai_api_key", "OPENAI_API_KEY"),
            "claude": ("anthropic_api_key", "ANTHROPIC_API_KEY"),
            "gemini": ("gemini_api_key", "GEMINI_API_KEY"),
            "grok": ("grok_api_key", "XAI_GROK4_API"),
        }
        config_key, env_key = key_map.get(provider_name, (None, None))
        if config_key:
            return self.config.get(config_key) or os.getenv(env_key or "")
        return None

    async def unified_request(self, request: AIRequest) -> AIResponse:
        """
        Execute a unified AI request against the specified provider.

        Returns AIResponse with success=False if the provider is not
        configured or the request fails. Never returns fabricated content.
        """
        provider_name = (
            request.provider.value
            if isinstance(request.provider, ModelProvider)
            else str(request.provider)
        )

        api_key = self._get_api_key(provider_name)
        if not api_key:
            error_msg = (
                f"Provider '{provider_name}' is not configured. "
                f"Set the appropriate API key in config or environment."
            )
            logger.error(error_msg)
            return AIResponse(
                content="",
                model=request.model,
                provider=provider_name,
                success=False,
                error=error_msg,
            )

        try:
            if provider_name == "openai":
                return await self._call_openai(request, api_key)
            elif provider_name == "claude":
                return await self._call_anthropic(request, api_key)
            elif provider_name == "gemini":
                return await self._call_gemini(request, api_key)
            elif provider_name == "grok":
                return await self._call_grok(request, api_key)
            else:
                return AIResponse(
                    content="",
                    model=request.model,
                    provider=provider_name,
                    success=False,
                    error=f"Unsupported provider: {provider_name}",
                )
        except httpx.HTTPStatusError as e:
            error_msg = f"HTTP {e.response.status_code} from {provider_name}: {e.response.text[:200]}"
            logger.error(error_msg)
            return AIResponse(
                content="",
                model=request.model,
                provider=provider_name,
                success=False,
                error=error_msg,
            )
        except Exception as e:
            error_msg = f"Request to {provider_name} failed: {e}"
            logger.error(error_msg)
            return AIResponse(
                content="",
                model=request.model,
                provider=provider_name,
                success=False,
                error=error_msg,
            )

    async def _call_openai(self, request: AIRequest, api_key: str) -> AIResponse:
        """Call OpenAI Chat Completions API."""
        client = self._get_client()
        payload = {
            "model": request.model,
            "messages": [{"role": "user", "content": request.prompt}],
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
        }
        resp = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json=payload,
        )
        resp.raise_for_status()
        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        tokens_used = data.get("usage", {}).get("total_tokens", 0)
        return AIResponse(
            content=content,
            model=request.model,
            provider="openai",
            success=True,
            tokens_used=tokens_used,
        )

    async def _call_anthropic(self, request: AIRequest, api_key: str) -> AIResponse:
        """Call Anthropic Messages API."""
        client = self._get_client()
        payload = {
            "model": request.model,
            "max_tokens": request.max_tokens,
            "messages": [{"role": "user", "content": request.prompt}],
        }
        resp = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json=payload,
        )
        resp.raise_for_status()
        data = resp.json()
        content = "".join(
            block["text"] for block in data.get("content", []) if block.get("type") == "text"
        )
        tokens_used = (
            data.get("usage", {}).get("input_tokens", 0)
            + data.get("usage", {}).get("output_tokens", 0)
        )
        return AIResponse(
            content=content,
            model=request.model,
            provider="claude",
            success=True,
            tokens_used=tokens_used,
        )

    async def _call_gemini(self, request: AIRequest, api_key: str) -> AIResponse:
        """Call Google Gemini generateContent API."""
        client = self._get_client()
        model = request.model or "gemini-pro"
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        payload = {
            "contents": [{"parts": [{"text": request.prompt}]}],
            "generationConfig": {
                "temperature": request.temperature,
                "maxOutputTokens": request.max_tokens,
            },
        }
        resp = await client.post(url, json=payload)
        resp.raise_for_status()
        data = resp.json()
        candidates = data.get("candidates", [])
        content = ""
        if candidates:
            parts = candidates[0].get("content", {}).get("parts", [])
            content = "".join(p.get("text", "") for p in parts)
        tokens_used = (
            data.get("usageMetadata", {}).get("totalTokenCount", 0)
        )
        return AIResponse(
            content=content,
            model=model,
            provider="gemini",
            success=True,
            tokens_used=tokens_used,
        )

    async def _call_grok(self, request: AIRequest, api_key: str) -> AIResponse:
        """Call xAI Grok API (OpenAI-compatible endpoint)."""
        client = self._get_client()
        payload = {
            "model": request.model,
            "messages": [{"role": "user", "content": request.prompt}],
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
        }
        resp = await client.post(
            "https://api.x.ai/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json=payload,
        )
        resp.raise_for_status()
        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        tokens_used = data.get("usage", {}).get("total_tokens", 0)
        return AIResponse(
            content=content,
            model=request.model,
            provider="grok",
            success=True,
            tokens_used=tokens_used,
        )

    async def health_check(self) -> dict[str, Any]:
        """
        Check which providers have API keys configured.

        Returns a dict indicating availability (key present) for each provider.
        """
        providers = {}
        for provider in ["openai", "claude", "gemini", "grok"]:
            key = self._get_api_key(provider)
            providers[provider] = "configured" if key else "unconfigured"

        all_configured = all(v == "configured" for v in providers.values())
        any_configured = any(v == "configured" for v in providers.values())

        if all_configured:
            status = "healthy"
        elif any_configured:
            status = "partial"
        else:
            status = "unavailable"

        return {
            "status": status,
            "providers": providers,
        }

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None
