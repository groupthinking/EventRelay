#!/usr/bin/env python3
"""
LLM Router
==========

Tries AI providers in priority order and returns the first successful response.

Priority: Gemini → Anthropic (Claude) → OpenAI → Grok (xAI) → Perplexity

Each provider is skipped if its API key is absent or if the call fails.
"""

import asyncio
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Optional SDK imports — each is silently skipped when not installed
# ---------------------------------------------------------------------------

try:
    from google import genai as _genai
    from google.genai import types as _genai_types
    _GENAI_AVAILABLE = True
except ImportError:
    _GENAI_AVAILABLE = False

try:
    import anthropic as _anthropic_sdk
    _ANTHROPIC_AVAILABLE = True
except ImportError:
    _ANTHROPIC_AVAILABLE = False

try:
    import openai as _openai_sdk
    _OPENAI_AVAILABLE = True
except ImportError:
    _OPENAI_AVAILABLE = False


class LLMRouter:
    """
    Routes text-generation requests across multiple providers with automatic
    fallback.  Callers use a single :meth:`generate` method and need not know
    which provider answered.

    Provider priority (first available key wins):
    1. Gemini (``GEMINI_API_KEY``)
    2. Anthropic / Claude (``ANTHROPIC_API_KEY``)
    3. OpenAI (``OPENAI_API_KEY``)
    4. Grok / xAI (``XAI_API_KEY`` or ``XAI_GROK4_API``)
    5. Perplexity (``PERPLEXITY_API_KEY``)
    """

    # Gemini model used for code generation
    _GEMINI_MODEL = "gemini-2.5-flash"
    # Claude model — Opus 4.8 as specified in CLAUDE.md
    _ANTHROPIC_MODEL = "claude-opus-4-8"
    # OpenAI model
    _OPENAI_MODEL = "gpt-4o"
    # Grok model
    _GROK_MODEL = "grok-3"
    # Perplexity model
    _PERPLEXITY_MODEL = "llama-3.1-sonar-large-128k-online"

    def __init__(self) -> None:
        self._gemini_key = os.environ.get("GEMINI_API_KEY")
        self._anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
        self._openai_key = os.environ.get("OPENAI_API_KEY")
        self._grok_key = (
            os.environ.get("XAI_API_KEY")
            or os.environ.get("XAI_GROK4_API")
            or os.environ.get("XAI_GROK4_OR_3_API")
        )
        self._perplexity_key = os.environ.get("PERPLEXITY_API_KEY")

        # Lazy-initialised SDK clients
        self._gemini_client: Optional[object] = None
        self._anthropic_client: Optional[object] = None
        self._openai_client: Optional[object] = None
        self._grok_client: Optional[object] = None
        self._perplexity_client: Optional[object] = None

        self._init_clients()

        available = self._available_providers()
        if available:
            logger.info("🤖 LLMRouter ready — providers: %s", ", ".join(available))
        else:
            logger.warning("LLMRouter: no AI provider keys found — generation disabled")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def has_provider(self) -> bool:
        """Return True if at least one provider is configured."""
        return bool(self._available_providers())

    async def generate(
        self,
        prompt: str,
        max_tokens: int = 8192,
        temperature: float = 1.0,
    ) -> Optional[str]:
        """
        Generate text using the first available provider.

        Runs the blocking SDK calls in a thread pool so the event loop is
        not stalled when called from an async context.

        Returns the generated text, or ``None`` if all providers fail.
        """
        return await asyncio.to_thread(self._dispatch_sync, prompt, max_tokens, temperature)

    def _dispatch_sync(
        self,
        prompt: str,
        max_tokens: int,
        temperature: float,
    ) -> Optional[str]:
        """Synchronous dispatch loop — runs in a thread via :meth:`generate`."""
        providers = [
            ("Gemini", self._generate_gemini),
            ("Anthropic", self._generate_anthropic),
            ("OpenAI", self._generate_openai),
            ("Grok", self._generate_grok),
            ("Perplexity", self._generate_perplexity),
        ]

        for name, fn in providers:
            try:
                result = fn(prompt, max_tokens, temperature)
                if result:
                    logger.debug("LLMRouter: responded via %s", name)
                    return result
            except Exception as exc:
                logger.warning("LLMRouter: %s failed (%s), trying next provider", name, exc)

        logger.error("LLMRouter: all providers failed")
        return None

    # ------------------------------------------------------------------
    # Initialisation helpers
    # ------------------------------------------------------------------

    def _init_clients(self) -> None:
        if _GENAI_AVAILABLE and self._gemini_key:
            try:
                self._gemini_client = _genai.Client(api_key=self._gemini_key)
                logger.debug("LLMRouter: Gemini client initialised")
            except Exception as exc:
                logger.warning("LLMRouter: failed to init Gemini client: %s", exc)

        if _ANTHROPIC_AVAILABLE and self._anthropic_key:
            try:
                self._anthropic_client = _anthropic_sdk.Anthropic(api_key=self._anthropic_key)
                logger.debug("LLMRouter: Anthropic client initialised")
            except Exception as exc:
                logger.warning("LLMRouter: failed to init Anthropic client: %s", exc)

        if _OPENAI_AVAILABLE and self._openai_key:
            try:
                self._openai_client = _openai_sdk.OpenAI(api_key=self._openai_key)
                logger.debug("LLMRouter: OpenAI client initialised")
            except Exception as exc:
                logger.warning("LLMRouter: failed to init OpenAI client: %s", exc)

        if _OPENAI_AVAILABLE and self._grok_key:
            try:
                self._grok_client = _openai_sdk.OpenAI(
                    api_key=self._grok_key,
                    base_url="https://api.x.ai/v1",
                )
                logger.debug("LLMRouter: Grok client initialised")
            except Exception as exc:
                logger.warning("LLMRouter: failed to init Grok client: %s", exc)

        if _OPENAI_AVAILABLE and self._perplexity_key:
            try:
                self._perplexity_client = _openai_sdk.OpenAI(
                    api_key=self._perplexity_key,
                    base_url="https://api.perplexity.ai",
                )
                logger.debug("LLMRouter: Perplexity client initialised")
            except Exception as exc:
                logger.warning("LLMRouter: failed to init Perplexity client: %s", exc)

    def _available_providers(self) -> list[str]:
        available = []
        if self._gemini_client is not None:
            available.append("Gemini")
        if self._anthropic_client is not None:
            available.append("Anthropic")
        if self._openai_client is not None:
            available.append("OpenAI")
        if self._grok_client is not None:
            available.append("Grok")
        if self._perplexity_client is not None:
            available.append("Perplexity")
        return available

    # ------------------------------------------------------------------
    # Per-provider generation methods
    # ------------------------------------------------------------------

    def _generate_gemini(
        self, prompt: str, max_tokens: int, temperature: float
    ) -> Optional[str]:
        if self._gemini_client is None:
            return None
        kwargs: dict = {
            "model": self._GEMINI_MODEL,
            "contents": prompt,
        }
        if _GENAI_AVAILABLE:
            kwargs["config"] = _genai_types.GenerateContentConfig(  # type: ignore[union-attr]
                temperature=temperature,
                max_output_tokens=max_tokens,
            )
        response = self._gemini_client.models.generate_content(**kwargs)  # type: ignore[attr-defined]
        text = response.text
        if text is None and response.candidates:
            parts = response.candidates[0].content.parts
            text_parts = [p.text for p in parts if hasattr(p, "text") and p.text]
            text = "\n".join(text_parts) if text_parts else None
        return text or None

    def _generate_anthropic(
        self, prompt: str, max_tokens: int, temperature: float
    ) -> Optional[str]:
        if self._anthropic_client is None:
            return None
        response = self._anthropic_client.messages.create(  # type: ignore[attr-defined]
            model=self._ANTHROPIC_MODEL,
            max_tokens=max_tokens,
            thinking={"type": "adaptive"},
            messages=[{"role": "user", "content": prompt}],
        )
        text_blocks = [b.text for b in response.content if b.type == "text"]
        return "\n".join(text_blocks) if text_blocks else None

    def _generate_openai(
        self, prompt: str, max_tokens: int, temperature: float
    ) -> Optional[str]:
        if self._openai_client is None:
            return None
        response = self._openai_client.chat.completions.create(  # type: ignore[attr-defined]
            model=self._OPENAI_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            temperature=temperature,
        )
        return response.choices[0].message.content or None

    def _generate_grok(
        self, prompt: str, max_tokens: int, temperature: float
    ) -> Optional[str]:
        if self._grok_client is None:
            return None
        response = self._grok_client.chat.completions.create(  # type: ignore[attr-defined]
            model=self._GROK_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            temperature=temperature,
        )
        return response.choices[0].message.content or None

    def _generate_perplexity(
        self, prompt: str, max_tokens: int, temperature: float
    ) -> Optional[str]:
        if self._perplexity_client is None:
            return None
        response = self._perplexity_client.chat.completions.create(  # type: ignore[attr-defined]
            model=self._PERPLEXITY_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            temperature=temperature,
        )
        return response.choices[0].message.content or None

    def close(self) -> None:
        """Explicit close for all initialized provider clients (best-effort hygiene for unclosed sessions)."""
        for attr in (
            "_gemini_client",
            "_anthropic_client",
            "_openai_client",
            "_grok_client",
            "_perplexity_client",
        ):
            client = getattr(self, attr, None)
            if not client:
                continue
            for m in ("close", "aclose"):
                fn = getattr(client, m, None)
                if callable(fn):
                    try:
                        fn()
                        break
                    except Exception:
                        pass
