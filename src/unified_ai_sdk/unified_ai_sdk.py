"""Unified interface for Gemini, Anthropic, and OpenAI requests."""

from __future__ import annotations

import asyncio
import logging
import os
import re
from collections.abc import Awaitable
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
    from anthropic import APIStatusError as AnthropicAPIStatusError
    from anthropic import APITimeoutError as AnthropicAPITimeoutError
    from anthropic import InternalServerError as AnthropicInternalServerError
    from anthropic import RateLimitError as AnthropicRateLimitError

    _ANTHROPIC_AVAILABLE = True
except (ImportError, AttributeError):
    _anthropic_sdk = None
    AnthropicRateLimitError = type("AnthropicRateLimitError", (Exception,), {})
    AnthropicAPITimeoutError = type("AnthropicAPITimeoutError", (Exception,), {})
    AnthropicAPIStatusError = type("AnthropicAPIStatusError", (Exception,), {})
    AnthropicInternalServerError = type("AnthropicInternalServerError", (Exception,), {})
    _ANTHROPIC_AVAILABLE = False

try:
    import openai as _openai_sdk
    from openai import APIStatusError as OpenAIAPIStatusError
    from openai import APITimeoutError as OpenAIAPITimeoutError
    from openai import InternalServerError as OpenAIInternalServerError
    from openai import RateLimitError as OpenAIRateLimitError

    _OPENAI_AVAILABLE = True
except (ImportError, AttributeError):
    _openai_sdk = None
    OpenAIRateLimitError = type("OpenAIRateLimitError", (Exception,), {})
    OpenAIAPITimeoutError = type("OpenAIAPITimeoutError", (Exception,), {})
    OpenAIAPIStatusError = type("OpenAIAPIStatusError", (Exception,), {})
    OpenAIInternalServerError = type("OpenAIInternalServerError", (Exception,), {})
    _OPENAI_AVAILABLE = False


class TaskType(Enum):
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
    prompt: str
    model: str
    provider: ModelProvider | str
    task_type: TaskType
    temperature: float = 0.7
    max_tokens: int = 4000
    structured_output: bool = False


@dataclass
class AIResponse:
    content: str
    model: str
    provider: str
    success: bool = True
    tokens_used: int = 0
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class UnifiedAISDK:
    def __init__(self, config: dict[str, Any] | None = None):
        self.config = dict(config or {})
        retry_attempts = int(self.config.get("retry_attempts", 3))
        if retry_attempts < 1:
            raise ValueError("retry_attempts must be at least 1")
        self.retry_attempts = retry_attempts
        self.retry_base_delay = float(self.config.get("retry_base_delay", 1.0))
        self.retry_max_delay = float(self.config.get("retry_max_delay", 8.0))
        self.request_timeout = float(self.config.get("request_timeout", 60.0))
        self.rate_limiter = RateLimiter(self.config.get("rate_limits"))
        self._gemini_key = (
            self.config.get("gemini_api_key")
            or os.getenv("GEMINI_API_KEY")
            or os.getenv("GOOGLE_GENERATIVE_AI_API_KEY")
            or os.getenv("GOOGLE_API_KEY")
        )
        self._anthropic_key = self.config.get("anthropic_api_key") or os.getenv("ANTHROPIC_API_KEY")
        self._openai_key = self.config.get("openai_api_key") or os.getenv("OPENAI_API_KEY")
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
