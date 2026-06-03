"""
Comparative Analysis Service - LFM2-VL vs Existing Models

Kicks off a head-to-head comparison of LiquidAI's LFM2-VL model against the
existing provider pool (Gemini, Claude, Grok, OpenAI) on tasks that arise
from the EventRelay video-processing pipeline.

Reference endpoints:
  LFM2-VL WebGPU demo : https://liquidai-lfm2-vl-webgpu.static.hf.space
  LFM2 MCP server     : https://liquidai-lfm2-mcp.static.hf.space
  HF Space            : https://huggingface.co/spaces/LiquidAI/LFM2-VL-WebGPU
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Optional SDK imports – each is soft-required so the service degrades
# gracefully when only a subset of providers is configured.
# ---------------------------------------------------------------------------
try:
    from google import genai
    from google.genai import types as genai_types

    _GEMINI_AVAILABLE = True
except ImportError:
    _GEMINI_AVAILABLE = False
    logger.warning("Gemini SDK not available – provider will be skipped")

try:
    import anthropic

    _CLAUDE_AVAILABLE = True
except ImportError:
    _CLAUDE_AVAILABLE = False
    logger.warning("Anthropic SDK not available – provider will be skipped")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

LFM2_MCP_BASE_URL = "https://liquidai-lfm2-mcp.static.hf.space"
LFM2_WEBGPU_URL = "https://liquidai-lfm2-vl-webgpu.static.hf.space"
LFM2_HF_SPACE_URL = "https://huggingface.co/spaces/LiquidAI/LFM2-VL-WebGPU"

_DEFAULT_TIMEOUT = 60  # seconds


# ---------------------------------------------------------------------------
# Domain types
# ---------------------------------------------------------------------------


class AnalysisTask(str, Enum):
    """Categories of tasks used to benchmark each provider."""

    TRANSCRIPT_SUMMARY = "transcript_summary"
    EVENT_EXTRACTION = "event_extraction"
    VISION_DESCRIPTION = "vision_description"
    REASONING = "reasoning"


@dataclass
class ProviderResult:
    """Outcome from a single provider for a single prompt."""

    provider: str
    model_name: str
    response: str
    latency_ms: int
    token_estimate: int = 0
    error: str | None = None


@dataclass
class ComparativeReport:
    """Aggregated comparison report for one analysis task."""

    task: AnalysisTask
    prompt: str
    results: list[ProviderResult]
    fastest_provider: str = ""
    most_verbose_provider: str = ""
    summary: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        successful = [r for r in self.results if not r.error]
        if successful:
            self.fastest_provider = min(successful, key=lambda r: r.latency_ms).provider
            self.most_verbose_provider = max(
                successful, key=lambda r: len(r.response)
            ).provider
            self.summary = (
                f"Compared {len(self.results)} providers on '{self.task.value}'. "
                f"Fastest: {self.fastest_provider}. "
                f"Most verbose: {self.most_verbose_provider}."
            )


# ---------------------------------------------------------------------------
# LFM2 MCP client (thin HTTP wrapper)
# ---------------------------------------------------------------------------


class LFM2MCPClient:
    """
    Minimal JSON-RPC 2.0 client for the LiquidAI LFM2 MCP server.

    The server follows the standard MCP HTTP transport so we can call
    tools using the ``tools/call`` method.
    """

    def __init__(
        self,
        base_url: str = LFM2_MCP_BASE_URL,
        api_key: str | None = None,
        timeout: int = _DEFAULT_TIMEOUT,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._request_id = 0
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            headers=headers,
            timeout=httpx.Timeout(timeout),
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> LFM2MCPClient:
        return self

    async def __aexit__(self, *_: Any) -> None:
        await self.close()

    async def generate_text(
        self,
        prompt: str,
        system: str | None = None,
        max_tokens: int = 512,
        temperature: float = 0.7,
    ) -> str:
        """Call the LFM2 ``generate_text`` tool and return the response text."""
        self._request_id += 1
        arguments: dict[str, Any] = {
            "prompt": prompt,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        if system:
            arguments["system"] = system

        payload = {
            "jsonrpc": "2.0",
            "id": self._request_id,
            "method": "tools/call",
            "params": {"name": "generate_text", "arguments": arguments},
        }
        response = await self._client.post("/mcp", json=payload)
        response.raise_for_status()
        data = response.json()
        if "error" in data:
            raise RuntimeError(
                f"LFM2 MCP error {data['error'].get('code')}: {data['error'].get('message')}"
            )
        result = data.get("result", {})
        # The MCP spec wraps content in a list of content objects
        if isinstance(result, dict):
            content = result.get("content", [])
            if isinstance(content, list) and content:
                first = content[0]
                if isinstance(first, dict):
                    return first.get("text", str(result))
            return result.get("text", str(result))
        return str(result)


# ---------------------------------------------------------------------------
# Comparative analysis service
# ---------------------------------------------------------------------------


class ComparativeAnalysisService:
    """
    Run the same prompt through LFM2-VL and the existing provider pool in
    parallel, then collate the results into a :class:`ComparativeReport`.

    All providers are optional – the service skips any provider whose SDK or
    API key is missing and returns whatever results it can gather.
    """

    def __init__(self) -> None:
        self.gemini_api_key = os.environ.get("GEMINI_API_KEY")
        self.claude_api_key = os.environ.get("ANTHROPIC_API_KEY")
        self.grok_api_key = os.environ.get("GROK_API_KEY")
        self.openai_api_key = os.environ.get("OPENAI_API_KEY")
        self.lfm2_api_key = os.environ.get("LIQUIDAI_API_KEY")

        self._gemini_client: Any | None = None
        self._claude_client: Any | None = None

        if _GEMINI_AVAILABLE and self.gemini_api_key:
            self._gemini_client = genai.Client(api_key=self.gemini_api_key)
            logger.info("Gemini client initialised")

        if _CLAUDE_AVAILABLE and self.claude_api_key:
            self._claude_client = anthropic.Anthropic(api_key=self.claude_api_key)
            logger.info("Claude client initialised")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def run_comparison(
        self,
        prompt: str,
        task: AnalysisTask = AnalysisTask.TRANSCRIPT_SUMMARY,
        providers: list[str] | None = None,
        max_tokens: int = 512,
    ) -> ComparativeReport:
        """
        Query all configured providers in parallel and return a
        :class:`ComparativeReport` with per-provider timing and outputs.

        Args:
            prompt:     The text prompt to send to each model.
            task:       Semantic category of the task (used for reporting).
            providers:  Subset of provider names to query.  If ``None``, all
                        available providers are used.
            max_tokens: Maximum tokens each model should generate.

        Returns:
            A :class:`ComparativeReport` with latency, response, and metadata
            for every queried provider.
        """
        available = self._available_providers()
        if providers:
            available = [p for p in available if p in providers]

        logger.info(
            "Starting comparative analysis | task=%s | providers=%s",
            task.value,
            available,
        )

        tasks = []
        for provider in available:
            tasks.append(self._query_provider(provider, prompt, max_tokens))

        raw_results = await asyncio.gather(*tasks, return_exceptions=True)

        results: list[ProviderResult] = []
        for item in raw_results:
            if isinstance(item, ProviderResult):
                results.append(item)
            elif isinstance(item, Exception):
                logger.error("Provider query raised an exception: %s", item)

        report = ComparativeReport(task=task, prompt=prompt, results=results)
        logger.info("Comparative analysis complete: %s", report.summary)
        return report

    async def run_full_suite(
        self,
        video_transcript: str,
        max_tokens: int = 512,
    ) -> dict[str, ComparativeReport]:
        """
        Execute the full benchmark suite (all :class:`AnalysisTask` values)
        against *video_transcript* and return a mapping of task → report.
        """
        prompts: dict[AnalysisTask, str] = {
            AnalysisTask.TRANSCRIPT_SUMMARY: (
                f"Summarise the following video transcript in 3-5 sentences:\n\n{video_transcript}"
            ),
            AnalysisTask.EVENT_EXTRACTION: (
                "Extract a list of key events from the transcript below.  "
                "Format each event as a JSON object with 'timestamp', 'title', and 'description'.\n\n"
                f"{video_transcript}"
            ),
            AnalysisTask.REASONING: (
                "Based on this transcript, what is the main argument being made "
                f"and what evidence supports it?\n\n{video_transcript}"
            ),
        }

        reports: dict[str, ComparativeReport] = {}
        for task, prompt in prompts.items():
            report = await self.run_comparison(
                prompt=prompt, task=task, max_tokens=max_tokens
            )
            reports[task.value] = report

        return reports

    # ------------------------------------------------------------------
    # Provider-level query methods
    # ------------------------------------------------------------------

    async def _query_provider(
        self,
        provider: str,
        prompt: str,
        max_tokens: int,
    ) -> ProviderResult:
        """Dispatch a prompt to a named provider and measure wall-clock time."""
        start = time.monotonic()
        try:
            if provider == "lfm2":
                return await self._query_lfm2(prompt, max_tokens, start)
            if provider == "gemini":
                return await self._query_gemini(prompt, max_tokens, start)
            if provider == "claude":
                return await self._query_claude(prompt, max_tokens, start)
            if provider == "grok":
                return await self._query_grok(prompt, max_tokens, start)
            if provider == "openai":
                return await self._query_openai(prompt, max_tokens, start)
            raise ValueError(f"Unknown provider: {provider}")
        except Exception as exc:  # noqa: BLE001
            latency = int((time.monotonic() - start) * 1000)
            logger.error("Provider '%s' failed: %s", provider, exc)
            return ProviderResult(
                provider=provider,
                model_name=provider,
                response="",
                latency_ms=latency,
                error=str(exc),
            )

    async def _query_lfm2(
        self, prompt: str, max_tokens: int, start: float
    ) -> ProviderResult:
        async with LFM2MCPClient(
            api_key=self.lfm2_api_key, timeout=_DEFAULT_TIMEOUT
        ) as client:
            text = await client.generate_text(prompt=prompt, max_tokens=max_tokens)
        latency = int((time.monotonic() - start) * 1000)
        return ProviderResult(
            provider="lfm2",
            model_name="LFM2-VL",
            response=text,
            latency_ms=latency,
            # Approximate word count – actual BPE token count is not available
            # without a provider-specific tokenizer.
            token_estimate=len(text.split()),
        )

    async def _query_gemini(
        self, prompt: str, max_tokens: int, start: float
    ) -> ProviderResult:
        if not self._gemini_client:
            raise RuntimeError("Gemini client not configured")
        # Run the synchronous SDK call in an executor to avoid blocking
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: self._gemini_client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt,
                config=genai_types.GenerateContentConfig(
                    max_output_tokens=max_tokens,
                    temperature=0.7,
                ),
            ),
        )
        text: str = response.text or ""
        latency = int((time.monotonic() - start) * 1000)
        return ProviderResult(
            provider="gemini",
            model_name="gemini-2.0-flash",
            response=text,
            latency_ms=latency,
            token_estimate=len(text.split()),
        )

    async def _query_claude(
        self, prompt: str, max_tokens: int, start: float
    ) -> ProviderResult:
        if not self._claude_client:
            raise RuntimeError("Claude client not configured")
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: self._claude_client.messages.create(
                model="claude-opus-4-8",
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}],
            ),
        )
        text = response.content[0].text if response.content else ""
        latency = int((time.monotonic() - start) * 1000)
        return ProviderResult(
            provider="claude",
            model_name="claude-opus-4-8",
            response=text,
            latency_ms=latency,
            token_estimate=len(text.split()),
        )

    async def _query_grok(
        self, prompt: str, max_tokens: int, start: float
    ) -> ProviderResult:
        if not self.grok_api_key:
            raise RuntimeError("GROK_API_KEY not set")
        payload = {
            "model": "grok-2-1212",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7,
            "max_tokens": max_tokens,
        }
        async with httpx.AsyncClient(timeout=_DEFAULT_TIMEOUT) as client:
            resp = await client.post(
                "https://api.x.ai/v1/chat/completions",
                headers={"Authorization": f"Bearer {self.grok_api_key}"},
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()
        
        # Validate response structure to avoid silent failures
        if "choices" not in data or not data["choices"]:
            raise ValueError(
                f"Invalid Grok API response: missing or empty 'choices' field in {data}"
            )
        choice = data["choices"][0]
        if "message" not in choice or "content" not in choice.get("message", {}):
            raise ValueError(
                f"Invalid Grok API response: missing 'message.content' in {choice}"
            )
        text = choice["message"]["content"]
        if not isinstance(text, str):
            raise ValueError(
                f"Invalid Grok API response: 'content' is not a string: {type(text)}"
            )
        
        latency = int((time.monotonic() - start) * 1000)
        return ProviderResult(
            provider="grok",
            model_name="grok-2-1212",
            response=text,
            latency_ms=latency,
            token_estimate=len(text.split()),
        )

    async def _query_openai(
        self, prompt: str, max_tokens: int, start: float
    ) -> ProviderResult:
        if not self.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY not set")
        payload = {
            "model": "gpt-4o",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7,
            "max_tokens": max_tokens,
        }
        async with httpx.AsyncClient(timeout=_DEFAULT_TIMEOUT) as client:
            resp = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {self.openai_api_key}"},
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()
        
        # Validate response structure to avoid silent failures
        if "choices" not in data or not data["choices"]:
            raise ValueError(
                f"Invalid OpenAI API response: missing or empty 'choices' field in {data}"
            )
        choice = data["choices"][0]
        if "message" not in choice or "content" not in choice.get("message", {}):
            raise ValueError(
                f"Invalid OpenAI API response: missing 'message.content' in {choice}"
            )
        text = choice["message"]["content"]
        if not isinstance(text, str):
            raise ValueError(
                f"Invalid OpenAI API response: 'content' is not a string: {type(text)}"
            )
        
        latency = int((time.monotonic() - start) * 1000)
        return ProviderResult(
            provider="openai",
            model_name="gpt-4o",
            response=text,
            latency_ms=latency,
            token_estimate=len(text.split()),
        )

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    def _available_providers(self) -> list[str]:
        providers = ["lfm2"]  # LFM2 is always attempted (public endpoint)
        if _GEMINI_AVAILABLE and self.gemini_api_key:
            providers.append("gemini")
        if _CLAUDE_AVAILABLE and self.claude_api_key:
            providers.append("claude")
        if self.grok_api_key:
            providers.append("grok")
        if self.openai_api_key:
            providers.append("openai")
        return providers


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

_service: ComparativeAnalysisService | None = None


def get_comparative_analysis_service() -> ComparativeAnalysisService:
    """Return (and lazily create) the module-level singleton service."""
    global _service
    if _service is None:
        _service = ComparativeAnalysisService()
    return _service
