"""
Unified AI SDK - Real Provider Implementation
==============================================

Provides unified interface for multiple AI providers (Claude, OpenAI, Grok/xAI).
Dispatches requests to real provider APIs via httpx with retry logic.
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


# Provider endpoint configuration
_PROVIDER_ENDPOINTS = {
    ModelProvider.CLAUDE: "https://api.anthropic.com/v1/messages",
    ModelProvider.OPENAI: "https://api.openai.com/v1/chat/completions",
    ModelProvider.GROK: "https://api.x.ai/v1/chat/completions",
    ModelProvider.GEMINI: "https://generativelanguage.googleapis.com/v1beta/models",
}

# Environment variable keys for provider API keys
_PROVIDER_KEY_ENV = {
    ModelProvider.CLAUDE: "ANTHROPIC_API_KEY",
    ModelProvider.OPENAI: "OPENAI_API_KEY",
    ModelProvider.GROK: "XAI_API_KEY",
    ModelProvider.GEMINI: "GEMINI_API_KEY",
}


class UnifiedAISDK:
    """
    Unified interface for multiple AI providers.

    Dispatches requests to Claude, OpenAI, Grok, or Gemini APIs via httpx.
    Returns explicit failures when provider keys are missing or calls fail.
    """

    def __init__(self, config: Optional[dict[str, Any]] = None):
        """
        Initialize Unified AI SDK.

        Args:
            config: Configuration dict with API keys and settings.
                    Keys can be provided here or via environment variables.
        """
        self.config = config if config is not None else {}
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Lazily create and return the shared httpx client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=60.0)
        return self._client

    def _get_api_key(self, provider: ModelProvider) -> Optional[str]:
        """Retrieve API key from config or environment."""
        # Check config first (provider-specific keys)
        config_keys = {
            ModelProvider.CLAUDE: "anthropic_api_key",
            ModelProvider.OPENAI: "openai_api_key",
            ModelProvider.GROK: "xai_api_key",
            ModelProvider.GEMINI: "gemini_api_key",
        }
        key = self.config.get(config_keys.get(provider, ""))
        if key:
            return key

        # Fall back to environment variable
        env_var = _PROVIDER_KEY_ENV.get(provider)
        if env_var:
            return os.getenv(env_var)
        return None

    def _resolve_provider(self, request: AIRequest) -> ModelProvider:
        """Resolve provider from request, handling string values."""
        if isinstance(request.provider, ModelProvider):
            return request.provider
        # Try to match string to enum
        provider_str = str(request.provider).lower()
        for member in ModelProvider:
            if member.value == provider_str:
                return member
        # Default to OpenAI if unrecognized
        return ModelProvider.OPENAI

    async def unified_request(self, request: AIRequest) -> AIResponse:
        """
        Execute a unified AI request by dispatching to the real provider API.

        Args:
            request: AIRequest object with prompt and configuration

        Returns:
            AIResponse with the result. success=False if provider is
            unavailable or the API call fails.
        """
        provider = self._resolve_provider(request)
        provider_name = provider.value
        api_key = self._get_api_key(provider)

        if not api_key:
            return AIResponse(
                content="",
                model=request.model,
                provider=provider_name,
                success=False,
                error=f"API key not configured for provider '{provider_name}' "
                      f"(set {_PROVIDER_KEY_ENV.get(provider, 'UNKNOWN')} environment variable)",
            )

        try:
            if provider == ModelProvider.CLAUDE:
                return await self._call_anthropic(request, api_key)
            elif provider == ModelProvider.OPENAI:
                return await self._call_openai(request, api_key)
            elif provider == ModelProvider.GROK:
                return await self._call_grok(request, api_key)
            elif provider == ModelProvider.GEMINI:
                return await self._call_gemini(request, api_key)
            else:
                return AIResponse(
                    content="",
                    model=request.model,
                    provider=provider_name,
                    success=False,
                    error=f"Unsupported provider: {provider_name}",
                )
        except httpx.HTTPStatusError as e:
            logger.error("Provider %s returned HTTP %d: %s", provider_name, e.response.status_code, e.response.text[:200])
            return AIResponse(
                content="",
                model=request.model,
                provider=provider_name,
                success=False,
                error=f"Provider API error (HTTP {e.response.status_code}): {e.response.text[:200]}",
            )
        except httpx.RequestError as e:
            logger.error("Network error calling provider %s: %s", provider_name, e)
            return AIResponse(
                content="",
                model=request.model,
                provider=provider_name,
                success=False,
                error=f"Network error contacting provider '{provider_name}': {e}",
            )
        except Exception as e:
            logger.error("Unexpected error calling provider %s: %s", provider_name, e)
            return AIResponse(
                content="",
                model=request.model,
                provider=provider_name,
                success=False,
                error=f"Unexpected error: {e}",
            )

    async def _call_anthropic(self, request: AIRequest, api_key: str) -> AIResponse:
        """Call the Anthropic Messages API."""
        client = await self._get_client()
        headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        payload = {
            "model": request.model,
            "max_tokens": request.max_tokens,
            "messages": [{"role": "user", "content": request.prompt}],
            "temperature": request.temperature,
        }
        response = await client.post(
            _PROVIDER_ENDPOINTS[ModelProvider.CLAUDE],
            headers=headers,
            json=payload,
        )
        response.raise_for_status()
        data = response.json()
        content = data.get("content", [{}])[0].get("text", "")
        usage = data.get("usage", {})
        tokens_used = usage.get("input_tokens", 0) + usage.get("output_tokens", 0)
        return AIResponse(
            content=content,
            model=data.get("model", request.model),
            provider="claude",
            success=True,
            tokens_used=tokens_used,
            metadata={"stop_reason": data.get("stop_reason")},
        )

    async def _call_openai(self, request: AIRequest, api_key: str) -> AIResponse:
        """Call the OpenAI Chat Completions API."""
        client = await self._get_client()
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": request.model,
            "messages": [{"role": "user", "content": request.prompt}],
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
        }
        response = await client.post(
            _PROVIDER_ENDPOINTS[ModelProvider.OPENAI],
            headers=headers,
            json=payload,
        )
        response.raise_for_status()
        data = response.json()
        content = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})
        tokens_used = usage.get("total_tokens", 0)
        return AIResponse(
            content=content,
            model=data.get("model", request.model),
            provider="openai",
            success=True,
            tokens_used=tokens_used,
            metadata={"finish_reason": data["choices"][0].get("finish_reason")},
        )

    async def _call_grok(self, request: AIRequest, api_key: str) -> AIResponse:
        """Call the xAI/Grok Chat Completions API (OpenAI-compatible)."""
        client = await self._get_client()
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": request.model,
            "messages": [{"role": "user", "content": request.prompt}],
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
        }
        response = await client.post(
            _PROVIDER_ENDPOINTS[ModelProvider.GROK],
            headers=headers,
            json=payload,
        )
        response.raise_for_status()
        data = response.json()
        content = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})
        tokens_used = usage.get("total_tokens", 0)
        return AIResponse(
            content=content,
            model=data.get("model", request.model),
            provider="grok",
            success=True,
            tokens_used=tokens_used,
            metadata={"finish_reason": data["choices"][0].get("finish_reason")},
        )

    async def _call_gemini(self, request: AIRequest, api_key: str) -> AIResponse:
        """Call the Google Gemini generateContent API."""
        client = await self._get_client()
        model_name = request.model
        if not model_name.startswith("models/"):
            model_name = f"models/{model_name}"
        url = f"{_PROVIDER_ENDPOINTS[ModelProvider.GEMINI]}/{model_name}:generateContent?key={api_key}"
        payload = {
            "contents": [{"parts": [{"text": request.prompt}]}],
            "generationConfig": {
                "temperature": request.temperature,
                "maxOutputTokens": request.max_tokens,
            },
        }
        response = await client.post(url, json=payload)
        response.raise_for_status()
        data = response.json()
        candidates = data.get("candidates", [])
        content = ""
        if candidates:
            parts = candidates[0].get("content", {}).get("parts", [])
            content = "".join(p.get("text", "") for p in parts)
        usage_metadata = data.get("usageMetadata", {})
        tokens_used = usage_metadata.get("totalTokenCount", 0)
        return AIResponse(
            content=content,
            model=request.model,
            provider="gemini",
            success=True,
            tokens_used=tokens_used,
            metadata={"finish_reason": candidates[0].get("finishReason") if candidates else None},
        )

    async def health_check(self) -> dict[str, Any]:
        """
        Check reachability of all configured providers.

        Returns a status for each provider: "available" if the API key is set
        and a lightweight request succeeds, "unavailable" with a reason otherwise.
        """
        results: dict[str, Any] = {}

        for provider in ModelProvider:
            api_key = self._get_api_key(provider)
            if not api_key:
                results[provider.value] = {
                    "status": "unavailable",
                    "reason": f"API key not configured ({_PROVIDER_KEY_ENV.get(provider, 'UNKNOWN')})",
                }
                continue

            try:
                client = await self._get_client()
                if provider == ModelProvider.CLAUDE:
                    # Anthropic: HEAD-like check by sending minimal request
                    # Just verify we can reach the endpoint (will get 400 for empty body, but that means reachable)
                    resp = await client.post(
                        _PROVIDER_ENDPOINTS[ModelProvider.CLAUDE],
                        headers={"x-api-key": api_key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
                        json={"model": "claude-3-haiku-20240307", "max_tokens": 1, "messages": [{"role": "user", "content": "hi"}]},
                        timeout=10.0,
                    )
                    # Any non-network response means the endpoint is reachable
                    if resp.status_code in (200, 400, 401, 403, 429):
                        results[provider.value] = {"status": "available" if resp.status_code == 200 else "reachable", "http_status": resp.status_code}
                    else:
                        results[provider.value] = {"status": "unavailable", "reason": f"HTTP {resp.status_code}"}

                elif provider in (ModelProvider.OPENAI, ModelProvider.GROK):
                    endpoint = _PROVIDER_ENDPOINTS[provider]
                    # Use models list endpoint for lightweight check
                    models_url = endpoint.rsplit("/", 1)[0] + "/models"
                    resp = await client.get(
                        models_url,
                        headers={"Authorization": f"Bearer {api_key}"},
                        timeout=10.0,
                    )
                    if resp.status_code in (200, 401, 403, 429):
                        results[provider.value] = {"status": "available" if resp.status_code == 200 else "reachable", "http_status": resp.status_code}
                    else:
                        results[provider.value] = {"status": "unavailable", "reason": f"HTTP {resp.status_code}"}

                elif provider == ModelProvider.GEMINI:
                    # Gemini: list models endpoint
                    resp = await client.get(
                        f"{_PROVIDER_ENDPOINTS[ModelProvider.GEMINI]}?key={api_key}",
                        timeout=10.0,
                    )
                    if resp.status_code in (200, 400, 401, 403, 429):
                        results[provider.value] = {"status": "available" if resp.status_code == 200 else "reachable", "http_status": resp.status_code}
                    else:
                        results[provider.value] = {"status": "unavailable", "reason": f"HTTP {resp.status_code}"}

            except Exception as e:
                results[provider.value] = {"status": "unavailable", "reason": str(e)}

        overall = "healthy" if any(v.get("status") == "available" for v in results.values()) else "degraded"
        return {"status": overall, "providers": results}

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None
