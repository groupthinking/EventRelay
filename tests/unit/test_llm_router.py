"""Unit tests for backend/llm_router.py — LLMRouter multi-provider fallback."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

_SRC = Path(__file__).resolve().parents[2] / "src"
sys.path.insert(0, str(_SRC))

import youtube_extension.backend.llm_router as _mod
from youtube_extension.backend.llm_router import LLMRouter

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_router_no_keys(monkeypatch) -> LLMRouter:
    """Return a router with all API key env vars cleared."""
    for k in ("GEMINI_API_KEY", "ANTHROPIC_API_KEY", "OPENAI_API_KEY",
              "XAI_API_KEY", "XAI_GROK4_API", "XAI_GROK4_OR_3_API", "PERPLEXITY_API_KEY"):
        monkeypatch.delenv(k, raising=False)
    return LLMRouter()


# ---------------------------------------------------------------------------
# LLMRouter.__init__ / has_provider
# ---------------------------------------------------------------------------


class TestLLMRouterInit:
    def test_no_providers_when_no_keys(self, monkeypatch):
        r = _make_router_no_keys(monkeypatch)
        assert r.has_provider() is False

    def test_all_clients_none_when_no_keys(self, monkeypatch):
        r = _make_router_no_keys(monkeypatch)
        assert r._gemini_client is None
        assert r._anthropic_client is None
        assert r._openai_client is None
        assert r._grok_client is None
        assert r._perplexity_client is None

    def test_has_provider_true_when_mock_client_set(self, monkeypatch):
        r = _make_router_no_keys(monkeypatch)
        r._anthropic_client = MagicMock()
        assert r.has_provider() is True

    def test_available_providers_empty_when_no_clients(self, monkeypatch):
        r = _make_router_no_keys(monkeypatch)
        assert r._available_providers() == []

    def test_available_providers_lists_anthropic(self, monkeypatch):
        r = _make_router_no_keys(monkeypatch)
        r._anthropic_client = MagicMock()
        assert "Anthropic" in r._available_providers()

    def test_available_providers_lists_openai(self, monkeypatch):
        r = _make_router_no_keys(monkeypatch)
        r._openai_client = MagicMock()
        assert "OpenAI" in r._available_providers()

    def test_available_providers_lists_gemini(self, monkeypatch):
        r = _make_router_no_keys(monkeypatch)
        r._gemini_client = MagicMock()
        assert "Gemini" in r._available_providers()

    def test_available_providers_lists_grok(self, monkeypatch):
        r = _make_router_no_keys(monkeypatch)
        r._grok_client = MagicMock()
        assert "Grok" in r._available_providers()

    def test_available_providers_lists_perplexity(self, monkeypatch):
        r = _make_router_no_keys(monkeypatch)
        r._perplexity_client = MagicMock()
        assert "Perplexity" in r._available_providers()


# ---------------------------------------------------------------------------
# LLMRouter.generate — routing logic
# ---------------------------------------------------------------------------


class TestLLMRouterGenerate:
    async def test_returns_none_when_no_providers(self, monkeypatch):
        r = _make_router_no_keys(monkeypatch)
        result = await r.generate("hello")
        assert result is None

    async def test_returns_gemini_response_when_available(self, monkeypatch):
        r = _make_router_no_keys(monkeypatch)
        r._gemini_client = MagicMock()
        with patch.object(r, "_generate_gemini", return_value="gemini result"):
            result = await r.generate("prompt")
        assert result == "gemini result"

    async def test_skips_to_anthropic_when_gemini_fails(self, monkeypatch):
        r = _make_router_no_keys(monkeypatch)
        r._gemini_client = MagicMock()
        r._anthropic_client = MagicMock()
        with patch.object(r, "_generate_gemini", side_effect=RuntimeError("boom")), \
             patch.object(r, "_generate_anthropic", return_value="claude result"):
            result = await r.generate("prompt")
        assert result == "claude result"

    async def test_skips_to_openai_when_anthropic_fails(self, monkeypatch):
        r = _make_router_no_keys(monkeypatch)
        r._anthropic_client = MagicMock()
        r._openai_client = MagicMock()
        with patch.object(r, "_generate_gemini", return_value=None), \
             patch.object(r, "_generate_anthropic", side_effect=RuntimeError("no")), \
             patch.object(r, "_generate_openai", return_value="openai result"):
            result = await r.generate("prompt")
        assert result == "openai result"

    async def test_returns_none_when_all_providers_fail(self, monkeypatch):
        r = _make_router_no_keys(monkeypatch)
        r._gemini_client = MagicMock()
        r._anthropic_client = MagicMock()
        with patch.object(r, "_generate_gemini", side_effect=RuntimeError("g")), \
             patch.object(r, "_generate_anthropic", side_effect=RuntimeError("a")), \
             patch.object(r, "_generate_openai", side_effect=RuntimeError("o")), \
             patch.object(r, "_generate_grok", side_effect=RuntimeError("gr")), \
             patch.object(r, "_generate_perplexity", side_effect=RuntimeError("p")):
            result = await r.generate("prompt")
        assert result is None

    async def test_skips_provider_returning_none(self, monkeypatch):
        r = _make_router_no_keys(monkeypatch)
        r._gemini_client = MagicMock()
        r._openai_client = MagicMock()
        with patch.object(r, "_generate_gemini", return_value=None), \
             patch.object(r, "_generate_anthropic", return_value=None), \
             patch.object(r, "_generate_openai", return_value="openai wins"):
            result = await r.generate("prompt")
        assert result == "openai wins"

    async def test_passes_max_tokens_to_provider(self, monkeypatch):
        r = _make_router_no_keys(monkeypatch)
        r._anthropic_client = MagicMock()
        calls = []
        def capture(*args, **kwargs):
            calls.append(kwargs.get("max_tokens") or args[1])
            return "ok"
        with patch.object(r, "_generate_gemini", return_value=None), \
             patch.object(r, "_generate_anthropic", side_effect=capture):
            await r.generate("prompt", max_tokens=4096)
        assert 4096 in calls

    async def test_uses_grok_as_fallback(self, monkeypatch):
        r = _make_router_no_keys(monkeypatch)
        r._grok_client = MagicMock()
        with patch.object(r, "_generate_gemini", return_value=None), \
             patch.object(r, "_generate_anthropic", return_value=None), \
             patch.object(r, "_generate_openai", return_value=None), \
             patch.object(r, "_generate_grok", return_value="grok response"):
            result = await r.generate("prompt")
        assert result == "grok response"

    async def test_uses_perplexity_as_last_fallback(self, monkeypatch):
        r = _make_router_no_keys(monkeypatch)
        r._perplexity_client = MagicMock()
        with patch.object(r, "_generate_gemini", return_value=None), \
             patch.object(r, "_generate_anthropic", return_value=None), \
             patch.object(r, "_generate_openai", return_value=None), \
             patch.object(r, "_generate_grok", return_value=None), \
             patch.object(r, "_generate_perplexity", return_value="perplexity answer"):
            result = await r.generate("prompt")
        assert result == "perplexity answer"


# ---------------------------------------------------------------------------
# Per-provider _generate_* methods — None client short-circuits
# ---------------------------------------------------------------------------


class TestGenerateMethodsWithNoneClient:
    def test_gemini_returns_none_when_no_client(self, monkeypatch):
        r = _make_router_no_keys(monkeypatch)
        assert r._generate_gemini("p", 100, 1.0) is None

    def test_anthropic_returns_none_when_no_client(self, monkeypatch):
        r = _make_router_no_keys(monkeypatch)
        assert r._generate_anthropic("p", 100, 1.0) is None

    def test_openai_returns_none_when_no_client(self, monkeypatch):
        r = _make_router_no_keys(monkeypatch)
        assert r._generate_openai("p", 100, 1.0) is None

    def test_grok_returns_none_when_no_client(self, monkeypatch):
        r = _make_router_no_keys(monkeypatch)
        assert r._generate_grok("p", 100, 1.0) is None

    def test_perplexity_returns_none_when_no_client(self, monkeypatch):
        r = _make_router_no_keys(monkeypatch)
        assert r._generate_perplexity("p", 100, 1.0) is None


# ---------------------------------------------------------------------------
# Per-provider _generate_* methods — with mock clients
# ---------------------------------------------------------------------------


class TestGenerateGemini:
    def test_returns_text_from_response(self, monkeypatch):
        r = _make_router_no_keys(monkeypatch)
        mock_client = MagicMock()
        resp = MagicMock()
        resp.text = "gemini output"
        mock_client.models.generate_content.return_value = resp
        r._gemini_client = mock_client
        result = r._generate_gemini("prompt", 1024, 1.0)
        assert result == "gemini output"

    def test_falls_back_to_parts_when_text_is_none(self, monkeypatch):
        r = _make_router_no_keys(monkeypatch)
        mock_client = MagicMock()
        resp = MagicMock()
        resp.text = None
        part = MagicMock()
        part.text = "part content"
        resp.candidates = [MagicMock()]
        resp.candidates[0].content.parts = [part]
        mock_client.models.generate_content.return_value = resp
        r._gemini_client = mock_client
        result = r._generate_gemini("prompt", 1024, 1.0)
        assert result == "part content"

    def test_returns_none_when_text_and_parts_both_empty(self, monkeypatch):
        r = _make_router_no_keys(monkeypatch)
        mock_client = MagicMock()
        resp = MagicMock()
        resp.text = None
        resp.candidates = []
        mock_client.models.generate_content.return_value = resp
        r._gemini_client = mock_client
        result = r._generate_gemini("prompt", 1024, 1.0)
        assert result is None


class TestGenerateAnthropic:
    def test_returns_text_block_content(self, monkeypatch):
        r = _make_router_no_keys(monkeypatch)
        mock_client = MagicMock()
        text_block = MagicMock()
        text_block.type = "text"
        text_block.text = "claude says hello"
        mock_client.messages.create.return_value = MagicMock(content=[text_block])
        r._anthropic_client = mock_client
        result = r._generate_anthropic("prompt", 1024, 1.0)
        assert result == "claude says hello"

    def test_returns_none_when_no_text_blocks(self, monkeypatch):
        r = _make_router_no_keys(monkeypatch)
        mock_client = MagicMock()
        thinking_block = MagicMock()
        thinking_block.type = "thinking"
        mock_client.messages.create.return_value = MagicMock(content=[thinking_block])
        r._anthropic_client = mock_client
        result = r._generate_anthropic("prompt", 1024, 1.0)
        assert result is None

    def test_joins_multiple_text_blocks(self, monkeypatch):
        r = _make_router_no_keys(monkeypatch)
        mock_client = MagicMock()
        b1 = MagicMock()
        b1.type = "text"
        b1.text = "part1"
        b2 = MagicMock()
        b2.type = "text"
        b2.text = "part2"
        mock_client.messages.create.return_value = MagicMock(content=[b1, b2])
        r._anthropic_client = mock_client
        result = r._generate_anthropic("prompt", 1024, 1.0)
        assert "part1" in result and "part2" in result


class TestGenerateOpenAI:
    def test_returns_message_content(self, monkeypatch):
        r = _make_router_no_keys(monkeypatch)
        mock_client = MagicMock()
        choice = MagicMock()
        choice.message.content = "openai response"
        mock_client.chat.completions.create.return_value = MagicMock(choices=[choice])
        r._openai_client = mock_client
        result = r._generate_openai("prompt", 1024, 0.7)
        assert result == "openai response"

    def test_returns_none_when_content_is_empty(self, monkeypatch):
        r = _make_router_no_keys(monkeypatch)
        mock_client = MagicMock()
        choice = MagicMock()
        choice.message.content = ""
        mock_client.chat.completions.create.return_value = MagicMock(choices=[choice])
        r._openai_client = mock_client
        result = r._generate_openai("prompt", 1024, 0.7)
        assert result is None


class TestGenerateGrok:
    def test_returns_message_content(self, monkeypatch):
        r = _make_router_no_keys(monkeypatch)
        mock_client = MagicMock()
        choice = MagicMock()
        choice.message.content = "grok response"
        mock_client.chat.completions.create.return_value = MagicMock(choices=[choice])
        r._grok_client = mock_client
        result = r._generate_grok("prompt", 1024, 0.7)
        assert result == "grok response"


class TestGeneratePerplexity:
    def test_returns_message_content(self, monkeypatch):
        r = _make_router_no_keys(monkeypatch)
        mock_client = MagicMock()
        choice = MagicMock()
        choice.message.content = "perplexity response"
        mock_client.chat.completions.create.return_value = MagicMock(choices=[choice])
        r._perplexity_client = mock_client
        result = r._generate_perplexity("prompt", 1024, 0.7)
        assert result == "perplexity response"


# ---------------------------------------------------------------------------
# _init_clients — SDK unavailable paths
# ---------------------------------------------------------------------------


class TestInitClientsSDKUnavailable:
    def test_no_gemini_client_when_sdk_unavailable(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
        with patch.object(_mod, "_GENAI_AVAILABLE", False):
            r = LLMRouter()
        assert r._gemini_client is None

    def test_no_anthropic_client_when_sdk_unavailable(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key")
        with patch.object(_mod, "_ANTHROPIC_AVAILABLE", False):
            r = LLMRouter()
        assert r._anthropic_client is None

    def test_no_openai_client_when_sdk_unavailable(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "fake-key")
        with patch.object(_mod, "_OPENAI_AVAILABLE", False):
            r = LLMRouter()
        assert r._openai_client is None

    def test_no_grok_client_when_sdk_unavailable(self, monkeypatch):
        monkeypatch.setenv("XAI_API_KEY", "fake-grok-key")
        with patch.object(_mod, "_OPENAI_AVAILABLE", False):
            r = LLMRouter()
        assert r._grok_client is None

    def test_no_perplexity_client_when_sdk_unavailable(self, monkeypatch):
        monkeypatch.setenv("PERPLEXITY_API_KEY", "fake-key")
        with patch.object(_mod, "_OPENAI_AVAILABLE", False):
            r = LLMRouter()
        assert r._perplexity_client is None

    def test_init_failure_in_gemini_sets_none(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
        mock_genai = MagicMock(Client=MagicMock(side_effect=RuntimeError("init err")))
        with patch.object(_mod, "_GENAI_AVAILABLE", True), \
             patch.dict("sys.modules", {"google.genai": mock_genai}):
            # Temporarily replace the module-level _genai reference
            original = getattr(_mod, "_genai", None)
            _mod._genai = mock_genai  # type: ignore[attr-defined]
            try:
                r = LLMRouter()
            finally:
                if original is None:
                    try:
                        delattr(_mod, "_genai")
                    except AttributeError:
                        pass
                else:
                    _mod._genai = original  # type: ignore[attr-defined]
        assert r._gemini_client is None

    def test_xai_grok_alternative_key_name(self, monkeypatch):
        for k in ("XAI_API_KEY", "PERPLEXITY_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GEMINI_API_KEY"):
            monkeypatch.delenv(k, raising=False)
        monkeypatch.setenv("XAI_GROK4_API", "grok-via-alt-key")
        r = LLMRouter()
        assert r._grok_key == "grok-via-alt-key"
