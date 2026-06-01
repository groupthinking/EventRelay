"""Unit tests for backend/ai_insights_processor.py."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_SRC = Path(__file__).resolve().parents[2] / "src"
sys.path.insert(0, str(_SRC))

sys.modules.pop("youtube_extension.backend.ai_insights_processor", None)

from youtube_extension.backend.ai_insights_processor import (
    AIInsightsProcessor,
    get_ai_insights,
)


# ===========================================================================
# AIInsightsProcessor.__init__ / _check_available_services
# ===========================================================================


class TestAIInsightsProcessorInit:
    def test_available_services_starts_empty_without_env(self, monkeypatch):
        monkeypatch.delenv("GOOGLE_AI_API_KEY", raising=False)
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        p = AIInsightsProcessor()
        assert p.available_services == []

    def test_gemini_added_via_google_ai_key(self, monkeypatch):
        monkeypatch.setenv("GOOGLE_AI_API_KEY", "key123")
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        p = AIInsightsProcessor()
        assert "gemini" in p.available_services

    def test_gemini_added_via_gemini_key(self, monkeypatch):
        monkeypatch.delenv("GOOGLE_AI_API_KEY", raising=False)
        monkeypatch.setenv("GEMINI_API_KEY", "key123")
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        p = AIInsightsProcessor()
        assert "gemini" in p.available_services

    def test_openai_added_when_key_present(self, monkeypatch):
        monkeypatch.delenv("GOOGLE_AI_API_KEY", raising=False)
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        monkeypatch.setenv("OPENAI_API_KEY", "sk-xxx")
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        p = AIInsightsProcessor()
        assert "openai" in p.available_services

    def test_anthropic_added_when_key_present(self, monkeypatch):
        monkeypatch.delenv("GOOGLE_AI_API_KEY", raising=False)
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-xxx")
        p = AIInsightsProcessor()
        assert "anthropic" in p.available_services

    def test_all_three_services_detected(self, monkeypatch):
        monkeypatch.setenv("GOOGLE_AI_API_KEY", "g-key")
        monkeypatch.setenv("OPENAI_API_KEY", "o-key")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "a-key")
        p = AIInsightsProcessor()
        assert len(p.available_services) == 3


# ===========================================================================
# AIInsightsProcessor._generate_fallback_insights
# ===========================================================================


class TestAIInsightsProcessorFallback:
    def test_returns_dict(self):
        p = AIInsightsProcessor()
        result = p._generate_fallback_insights("http://example.com/v")
        assert isinstance(result, dict)

    def test_has_summary(self):
        p = AIInsightsProcessor()
        result = p._generate_fallback_insights("http://example.com/v")
        assert "summary" in result

    def test_has_key_moments(self):
        p = AIInsightsProcessor()
        result = p._generate_fallback_insights("http://example.com/v")
        assert isinstance(result.get("key_moments"), list)
        assert len(result["key_moments"]) > 0

    def test_has_technologies_detected(self):
        p = AIInsightsProcessor()
        result = p._generate_fallback_insights("http://example.com/v")
        assert "technologies_detected" in result

    def test_has_difficulty_level(self):
        p = AIInsightsProcessor()
        result = p._generate_fallback_insights("http://example.com/v")
        assert "difficulty_level" in result

    def test_service_used_is_fallback(self):
        p = AIInsightsProcessor()
        result = p._generate_fallback_insights("http://example.com/v")
        assert result.get("service_used") == "fallback"

    def test_note_present(self):
        p = AIInsightsProcessor()
        result = p._generate_fallback_insights("http://example.com/v")
        assert "note" in result


# ===========================================================================
# AIInsightsProcessor._get_insights_from_service routing
# ===========================================================================


class TestAIInsightsProcessorServiceRouting:
    async def test_unknown_service_returns_none(self):
        p = AIInsightsProcessor()
        result = await p._get_insights_from_service("http://example.com/v", "unknown_service")
        assert result is None


# ===========================================================================
# AIInsightsProcessor.get_insights
# ===========================================================================


class TestAIInsightsProcessorGetInsights:
    async def test_returns_fallback_when_no_services(self, monkeypatch):
        monkeypatch.delenv("GOOGLE_AI_API_KEY", raising=False)
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        p = AIInsightsProcessor()
        result = await p.get_insights("http://example.com/v")
        assert result is not None
        assert result.get("service_used") == "fallback"

    async def test_returns_dict(self, monkeypatch):
        monkeypatch.delenv("GOOGLE_AI_API_KEY", raising=False)
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        p = AIInsightsProcessor()
        result = await p.get_insights("http://example.com/v")
        assert isinstance(result, dict)


# ===========================================================================
# get_ai_insights global function
# ===========================================================================


class TestGetAIInsights:
    async def test_returns_dict(self, monkeypatch):
        monkeypatch.delenv("GOOGLE_AI_API_KEY", raising=False)
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        # Reset global instance
        import youtube_extension.backend.ai_insights_processor as _mod
        _mod._ai_insights_processor = None
        result = await get_ai_insights("http://example.com/v")
        assert isinstance(result, dict)

    async def test_reuses_global_instance(self, monkeypatch):
        monkeypatch.delenv("GOOGLE_AI_API_KEY", raising=False)
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        import youtube_extension.backend.ai_insights_processor as _mod
        _mod._ai_insights_processor = None
        await get_ai_insights("http://example.com/v1")
        instance_after_first = _mod._ai_insights_processor
        await get_ai_insights("http://example.com/v2")
        assert _mod._ai_insights_processor is instance_after_first
