"""Unit tests for AnalysisTask, ProviderResult, ComparativeReport dataclasses."""

from __future__ import annotations

import sys
import types
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

# Stub out optional heavy dependencies before importing the module
_google_stub = types.ModuleType("google")
sys.modules.setdefault("google", _google_stub)
_google_genai_stub = types.ModuleType("google.genai")
_google_genai_stub.Client = MagicMock()
sys.modules.setdefault("google.genai", _google_genai_stub)
_genai_types = types.ModuleType("google.genai.types")
_genai_types.GenerateContentConfig = MagicMock()
sys.modules.setdefault("google.genai.types", _genai_types)
# Make `from google import genai` work
_google_stub.genai = _google_genai_stub

_anthropic_stub = types.ModuleType("anthropic")
_anthropic_stub.Anthropic = MagicMock()
sys.modules.setdefault("anthropic", _anthropic_stub)

# httpx is a real installed dependency — import it so sys.modules contains the real module
# before any test file with a heavier httpx stub is loaded
import httpx as _httpx_real  # noqa: F401

from youtube_extension.backend.services.comparative_analysis import (  # noqa: E402
    AnalysisTask,
    ComparativeAnalysisService,
    ComparativeReport,
    LFM2MCPClient,
    LFM2_MCP_BASE_URL,
    ProviderResult,
    get_comparative_analysis_service,
)


# ===========================================================================
# AnalysisTask enum
# ===========================================================================


class TestAnalysisTask:
    def test_all_values_present(self):
        values = {t.value for t in AnalysisTask}
        assert values == {
            "transcript_summary",
            "event_extraction",
            "vision_description",
            "reasoning",
        }

    def test_str_comparison(self):
        assert AnalysisTask.TRANSCRIPT_SUMMARY == "transcript_summary"
        assert AnalysisTask.REASONING == "reasoning"

    def test_round_trip(self):
        assert AnalysisTask("event_extraction") is AnalysisTask.EVENT_EXTRACTION


# ===========================================================================
# ProviderResult dataclass
# ===========================================================================


class TestProviderResult:
    def test_required_fields(self):
        r = ProviderResult(
            provider="openai",
            model_name="gpt-4o",
            response="Hello",
            latency_ms=200,
        )
        assert r.provider == "openai"
        assert r.model_name == "gpt-4o"
        assert r.response == "Hello"
        assert r.latency_ms == 200

    def test_token_estimate_defaults_zero(self):
        r = ProviderResult(provider="a", model_name="m", response="r", latency_ms=0)
        assert r.token_estimate == 0

    def test_error_defaults_none(self):
        r = ProviderResult(provider="a", model_name="m", response="r", latency_ms=0)
        assert r.error is None

    def test_with_error(self):
        r = ProviderResult(
            provider="anthropic",
            model_name="claude-opus-4-8",
            response="",
            latency_ms=0,
            error="rate limited",
        )
        assert r.error == "rate limited"


# ===========================================================================
# ComparativeReport dataclass + __post_init__
# ===========================================================================


def _result(provider: str, latency: int, response: str, error: str | None = None) -> ProviderResult:
    return ProviderResult(
        provider=provider,
        model_name=f"{provider}-model",
        response=response,
        latency_ms=latency,
        error=error,
    )


class TestComparativeReportEmpty:
    def test_empty_results_no_post_init_crash(self):
        report = ComparativeReport(
            task=AnalysisTask.REASONING,
            prompt="test",
            results=[],
        )
        assert report.fastest_provider == ""
        assert report.most_verbose_provider == ""
        assert report.summary == ""

    def test_all_errored_results_treated_as_empty(self):
        report = ComparativeReport(
            task=AnalysisTask.REASONING,
            prompt="test",
            results=[_result("openai", 100, "", error="failed")],
        )
        assert report.fastest_provider == ""


class TestComparativeReportPopulated:
    def _make_report(self) -> ComparativeReport:
        return ComparativeReport(
            task=AnalysisTask.TRANSCRIPT_SUMMARY,
            prompt="Summarise this transcript.",
            results=[
                _result("openai", 150, "Short summary."),
                _result("anthropic", 300, "A much longer and more detailed summary."),
                _result("google", 200, "Medium length summary here."),
            ],
        )

    def test_fastest_provider_is_lowest_latency(self):
        report = self._make_report()
        assert report.fastest_provider == "openai"

    def test_most_verbose_is_longest_response(self):
        report = self._make_report()
        assert report.most_verbose_provider == "anthropic"

    def test_summary_contains_task_value(self):
        report = self._make_report()
        assert "transcript_summary" in report.summary

    def test_summary_contains_fastest_provider(self):
        report = self._make_report()
        assert "openai" in report.summary

    def test_summary_contains_most_verbose_provider(self):
        report = self._make_report()
        assert "anthropic" in report.summary

    def test_summary_mentions_provider_count(self):
        report = self._make_report()
        assert "3" in report.summary

    def test_errored_results_excluded_from_ranking(self):
        report = ComparativeReport(
            task=AnalysisTask.EVENT_EXTRACTION,
            prompt="Extract events.",
            results=[
                _result("openai", 50, "Fast but errored", error="timeout"),
                _result("anthropic", 300, "Succeeded"),
            ],
        )
        assert report.fastest_provider == "anthropic"

    def test_single_successful_result(self):
        report = ComparativeReport(
            task=AnalysisTask.VISION_DESCRIPTION,
            prompt="Describe the image.",
            results=[_result("google", 100, "A mountain.")],
        )
        assert report.fastest_provider == "google"
        assert report.most_verbose_provider == "google"

    def test_metadata_defaults_empty(self):
        report = self._make_report()
        assert report.metadata == {}

    def test_custom_metadata_preserved(self):
        report = ComparativeReport(
            task=AnalysisTask.REASONING,
            prompt="Why?",
            results=[_result("openai", 100, "Because.")],
            metadata={"run_id": "abc"},
        )
        assert report.metadata["run_id"] == "abc"


# ===========================================================================
# LFM2MCPClient
# ===========================================================================


class TestLFM2MCPClientInit:
    def test_default_base_url(self):
        import httpx as _httpx  # noqa: F401  (may be stub)
        # Just verify the constructor runs without error and stores attributes
        # We patch httpx.AsyncClient so we don't need a real HTTP client
        with patch(
            "youtube_extension.backend.services.comparative_analysis.httpx.AsyncClient",
            return_value=MagicMock(),
        ):
            client = LFM2MCPClient()
            assert client.base_url == LFM2_MCP_BASE_URL.rstrip("/")
            assert client.timeout == 60
            assert client._request_id == 0

    def test_custom_base_url_trailing_slash_stripped(self):
        with patch(
            "youtube_extension.backend.services.comparative_analysis.httpx.AsyncClient",
            return_value=MagicMock(),
        ):
            client = LFM2MCPClient(base_url="https://example.com/")
            assert client.base_url == "https://example.com"

    def test_api_key_sets_authorization_header(self):
        captured_headers = {}

        def fake_async_client(base_url, headers, timeout):
            captured_headers.update(headers)
            return MagicMock()

        with patch(
            "youtube_extension.backend.services.comparative_analysis.httpx.AsyncClient",
            side_effect=fake_async_client,
        ):
            LFM2MCPClient(api_key="test-key-123")
        assert captured_headers.get("Authorization") == "Bearer test-key-123"

    def test_no_api_key_no_authorization_header(self):
        captured_headers = {}

        def fake_async_client(base_url, headers, timeout):
            captured_headers.update(headers)
            return MagicMock()

        with patch(
            "youtube_extension.backend.services.comparative_analysis.httpx.AsyncClient",
            side_effect=fake_async_client,
        ):
            LFM2MCPClient(api_key=None)
        assert "Authorization" not in captured_headers


@pytest.mark.asyncio
class TestLFM2MCPClientGenerateText:
    def _make_client(self, mock_http_client):
        with patch(
            "youtube_extension.backend.services.comparative_analysis.httpx.AsyncClient",
            return_value=mock_http_client,
        ):
            return LFM2MCPClient()

    async def test_generate_text_success_text_in_content(self):
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {"content": [{"type": "text", "text": "Hello from LFM2"}]},
        }
        mock_http = AsyncMock()
        mock_http.post = AsyncMock(return_value=mock_response)

        with patch(
            "youtube_extension.backend.services.comparative_analysis.httpx.AsyncClient",
            return_value=mock_http,
        ):
            client = LFM2MCPClient()
        text = await client.generate_text("say hello")
        assert text == "Hello from LFM2"

    async def test_generate_text_increments_request_id(self):
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {"content": [{"type": "text", "text": "ok"}]},
        }
        mock_http = AsyncMock()
        mock_http.post = AsyncMock(return_value=mock_response)

        with patch(
            "youtube_extension.backend.services.comparative_analysis.httpx.AsyncClient",
            return_value=mock_http,
        ):
            client = LFM2MCPClient()

        assert client._request_id == 0
        await client.generate_text("first")
        assert client._request_id == 1
        await client.generate_text("second")
        assert client._request_id == 2

    async def test_generate_text_error_in_response_raises(self):
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "jsonrpc": "2.0",
            "id": 1,
            "error": {"code": -32000, "message": "model overloaded"},
        }
        mock_http = AsyncMock()
        mock_http.post = AsyncMock(return_value=mock_response)

        with patch(
            "youtube_extension.backend.services.comparative_analysis.httpx.AsyncClient",
            return_value=mock_http,
        ):
            client = LFM2MCPClient()

        with pytest.raises(RuntimeError, match="model overloaded"):
            await client.generate_text("prompt")

    async def test_generate_text_result_is_plain_string(self):
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "jsonrpc": "2.0",
            "id": 1,
            "result": "plain text result",
        }
        mock_http = AsyncMock()
        mock_http.post = AsyncMock(return_value=mock_response)

        with patch(
            "youtube_extension.backend.services.comparative_analysis.httpx.AsyncClient",
            return_value=mock_http,
        ):
            client = LFM2MCPClient()

        text = await client.generate_text("prompt")
        assert text == "plain text result"

    async def test_generate_text_result_dict_with_text_key(self):
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {"text": "direct text key"},
        }
        mock_http = AsyncMock()
        mock_http.post = AsyncMock(return_value=mock_response)

        with patch(
            "youtube_extension.backend.services.comparative_analysis.httpx.AsyncClient",
            return_value=mock_http,
        ):
            client = LFM2MCPClient()

        text = await client.generate_text("prompt")
        assert text == "direct text key"

    async def test_generate_text_with_system_prompt(self):
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {"content": [{"type": "text", "text": "response"}]},
        }
        mock_http = AsyncMock()
        mock_http.post = AsyncMock(return_value=mock_response)

        with patch(
            "youtube_extension.backend.services.comparative_analysis.httpx.AsyncClient",
            return_value=mock_http,
        ):
            client = LFM2MCPClient()

        await client.generate_text("prompt", system="You are a helpful assistant")
        call_args = mock_http.post.call_args
        payload = call_args[1]["json"]
        assert payload["params"]["arguments"]["system"] == "You are a helpful assistant"

    async def test_context_manager_closes_client(self):
        mock_http = AsyncMock()
        mock_http.aclose = AsyncMock()

        with patch(
            "youtube_extension.backend.services.comparative_analysis.httpx.AsyncClient",
            return_value=mock_http,
        ):
            async with LFM2MCPClient() as client:
                assert client is not None
        mock_http.aclose.assert_called_once()


# ===========================================================================
# ComparativeAnalysisService
# ===========================================================================


class TestComparativeAnalysisServiceInit:
    def test_reads_api_keys_from_env(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "g-key")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "a-key")
        monkeypatch.setenv("GROK_API_KEY", "gr-key")
        monkeypatch.setenv("OPENAI_API_KEY", "o-key")
        monkeypatch.setenv("LIQUIDAI_API_KEY", "l-key")
        svc = ComparativeAnalysisService()
        assert svc.grok_api_key == "gr-key"
        assert svc.openai_api_key == "o-key"
        assert svc.lfm2_api_key == "l-key"

    def test_missing_api_keys_are_none(self, monkeypatch):
        for key in ("GEMINI_API_KEY", "ANTHROPIC_API_KEY", "GROK_API_KEY",
                    "OPENAI_API_KEY", "LIQUIDAI_API_KEY"):
            monkeypatch.delenv(key, raising=False)
        svc = ComparativeAnalysisService()
        assert svc.grok_api_key is None
        assert svc.openai_api_key is None


class TestAvailableProviders:
    def test_lfm2_always_included(self, monkeypatch):
        for key in ("GEMINI_API_KEY", "ANTHROPIC_API_KEY", "GROK_API_KEY",
                    "OPENAI_API_KEY", "LIQUIDAI_API_KEY"):
            monkeypatch.delenv(key, raising=False)
        svc = ComparativeAnalysisService()
        providers = svc._available_providers()
        assert "lfm2" in providers

    def test_grok_included_when_key_set(self, monkeypatch):
        monkeypatch.setenv("GROK_API_KEY", "gr-key")
        svc = ComparativeAnalysisService()
        assert "grok" in svc._available_providers()

    def test_openai_included_when_key_set(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "o-key")
        svc = ComparativeAnalysisService()
        assert "openai" in svc._available_providers()

    def test_grok_not_included_without_key(self, monkeypatch):
        monkeypatch.delenv("GROK_API_KEY", raising=False)
        svc = ComparativeAnalysisService()
        assert "grok" not in svc._available_providers()

    def test_openai_not_included_without_key(self, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        svc = ComparativeAnalysisService()
        assert "openai" not in svc._available_providers()


@pytest.mark.asyncio
class TestRunComparison:
    async def test_filters_to_requested_providers(self, monkeypatch):
        monkeypatch.setenv("GROK_API_KEY", "gr-key")
        monkeypatch.setenv("OPENAI_API_KEY", "o-key")
        svc = ComparativeAnalysisService()

        async def fake_query(provider, prompt, max_tokens):
            return ProviderResult(
                provider=provider,
                model_name=provider,
                response=f"response from {provider}",
                latency_ms=100,
            )

        svc._query_provider = fake_query
        report = await svc.run_comparison(
            prompt="test",
            task=AnalysisTask.REASONING,
            providers=["lfm2"],
        )
        assert all(r.provider == "lfm2" for r in report.results)

    async def test_exceptions_in_gather_are_skipped(self, monkeypatch):
        for key in ("GEMINI_API_KEY", "ANTHROPIC_API_KEY", "GROK_API_KEY",
                    "OPENAI_API_KEY", "LIQUIDAI_API_KEY"):
            monkeypatch.delenv(key, raising=False)
        svc = ComparativeAnalysisService()

        async def raise_exc(provider, prompt, max_tokens):
            raise RuntimeError("network down")

        svc._query_provider = raise_exc
        report = await svc.run_comparison(prompt="test")
        assert report.results == []

    async def test_returns_comparative_report(self, monkeypatch):
        for key in ("GEMINI_API_KEY", "ANTHROPIC_API_KEY", "GROK_API_KEY",
                    "OPENAI_API_KEY", "LIQUIDAI_API_KEY"):
            monkeypatch.delenv(key, raising=False)
        svc = ComparativeAnalysisService()

        async def fake_query(provider, prompt, max_tokens):
            return ProviderResult(
                provider=provider,
                model_name=provider,
                response="hello",
                latency_ms=50,
            )

        svc._query_provider = fake_query
        report = await svc.run_comparison(prompt="hello", task=AnalysisTask.REASONING)
        assert isinstance(report, ComparativeReport)
        assert report.task == AnalysisTask.REASONING


@pytest.mark.asyncio
class TestRunFullSuite:
    async def test_returns_dict_with_all_task_keys(self, monkeypatch):
        for key in ("GEMINI_API_KEY", "ANTHROPIC_API_KEY", "GROK_API_KEY",
                    "OPENAI_API_KEY", "LIQUIDAI_API_KEY"):
            monkeypatch.delenv(key, raising=False)
        svc = ComparativeAnalysisService()

        async def fake_query(provider, prompt, max_tokens):
            return ProviderResult(
                provider=provider, model_name=provider, response="ok", latency_ms=10
            )

        svc._query_provider = fake_query
        reports = await svc.run_full_suite("some transcript")
        assert set(reports.keys()) >= {
            AnalysisTask.TRANSCRIPT_SUMMARY.value,
            AnalysisTask.EVENT_EXTRACTION.value,
            AnalysisTask.REASONING.value,
        }

    async def test_each_value_is_comparative_report(self, monkeypatch):
        for key in ("GEMINI_API_KEY", "ANTHROPIC_API_KEY", "GROK_API_KEY",
                    "OPENAI_API_KEY", "LIQUIDAI_API_KEY"):
            monkeypatch.delenv(key, raising=False)
        svc = ComparativeAnalysisService()

        async def fake_query(provider, prompt, max_tokens):
            return ProviderResult(
                provider=provider, model_name=provider, response="ok", latency_ms=10
            )

        svc._query_provider = fake_query
        reports = await svc.run_full_suite("some transcript", max_tokens=256)
        for v in reports.values():
            assert isinstance(v, ComparativeReport)


@pytest.mark.asyncio
class TestQueryProvider:
    async def _svc(self, monkeypatch):
        for key in ("GEMINI_API_KEY", "ANTHROPIC_API_KEY", "GROK_API_KEY",
                    "OPENAI_API_KEY", "LIQUIDAI_API_KEY"):
            monkeypatch.delenv(key, raising=False)
        return ComparativeAnalysisService()

    async def test_unknown_provider_returns_error_result(self, monkeypatch):
        svc = await self._svc(monkeypatch)
        result = await svc._query_provider("unknown_provider", "prompt", 512)
        assert result.error is not None
        assert "Unknown provider" in result.error

    async def test_grok_missing_key_returns_error_result(self, monkeypatch):
        monkeypatch.delenv("GROK_API_KEY", raising=False)
        svc = await self._svc(monkeypatch)
        svc.grok_api_key = None
        result = await svc._query_provider("grok", "prompt", 512)
        assert result.error is not None
        assert "GROK_API_KEY" in result.error

    async def test_openai_missing_key_returns_error_result(self, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        svc = await self._svc(monkeypatch)
        svc.openai_api_key = None
        result = await svc._query_provider("openai", "prompt", 512)
        assert result.error is not None
        assert "OPENAI_API_KEY" in result.error

    async def test_latency_is_non_negative_on_error(self, monkeypatch):
        svc = await self._svc(monkeypatch)
        result = await svc._query_provider("unknown_provider", "prompt", 512)
        assert result.latency_ms >= 0


@pytest.mark.asyncio
class TestQueryGrok:
    async def test_grok_valid_response_returns_provider_result(self, monkeypatch):
        monkeypatch.setenv("GROK_API_KEY", "gr-key")
        svc = ComparativeAnalysisService()
        svc.grok_api_key = "gr-key"

        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": "grok says hello"}}]
        }

        import httpx as real_httpx
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_resp)

        with patch(
            "youtube_extension.backend.services.comparative_analysis.httpx.AsyncClient",
            return_value=mock_client,
        ):
            import time
            result = await svc._query_grok("test prompt", 512, time.monotonic())
        assert result.provider == "grok"
        assert result.response == "grok says hello"
        assert result.error is None

    async def test_grok_missing_choices_raises(self, monkeypatch):
        monkeypatch.setenv("GROK_API_KEY", "gr-key")
        svc = ComparativeAnalysisService()
        svc.grok_api_key = "gr-key"

        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {"choices": []}

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_resp)

        with patch(
            "youtube_extension.backend.services.comparative_analysis.httpx.AsyncClient",
            return_value=mock_client,
        ):
            import time
            with pytest.raises(ValueError, match="choices"):
                await svc._query_grok("prompt", 512, time.monotonic())

    async def test_grok_missing_message_content_raises(self, monkeypatch):
        monkeypatch.setenv("GROK_API_KEY", "gr-key")
        svc = ComparativeAnalysisService()
        svc.grok_api_key = "gr-key"

        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {"choices": [{"other": "field"}]}

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_resp)

        with patch(
            "youtube_extension.backend.services.comparative_analysis.httpx.AsyncClient",
            return_value=mock_client,
        ):
            import time
            with pytest.raises(ValueError, match="message.content"):
                await svc._query_grok("prompt", 512, time.monotonic())

    async def test_grok_non_string_content_raises(self, monkeypatch):
        monkeypatch.setenv("GROK_API_KEY", "gr-key")
        svc = ComparativeAnalysisService()
        svc.grok_api_key = "gr-key"

        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": 42}}]
        }

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_resp)

        with patch(
            "youtube_extension.backend.services.comparative_analysis.httpx.AsyncClient",
            return_value=mock_client,
        ):
            import time
            with pytest.raises(ValueError, match="not a string"):
                await svc._query_grok("prompt", 512, time.monotonic())


@pytest.mark.asyncio
class TestQueryOpenAI:
    async def test_openai_valid_response_returns_provider_result(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "o-key")
        svc = ComparativeAnalysisService()
        svc.openai_api_key = "o-key"

        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": "openai says hello"}}]
        }
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_resp)

        with patch(
            "youtube_extension.backend.services.comparative_analysis.httpx.AsyncClient",
            return_value=mock_client,
        ):
            import time
            result = await svc._query_openai("test prompt", 512, time.monotonic())
        assert result.provider == "openai"
        assert result.response == "openai says hello"
        assert result.error is None

    async def test_openai_empty_choices_raises(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "o-key")
        svc = ComparativeAnalysisService()
        svc.openai_api_key = "o-key"

        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {"choices": []}
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_resp)

        with patch(
            "youtube_extension.backend.services.comparative_analysis.httpx.AsyncClient",
            return_value=mock_client,
        ):
            import time
            with pytest.raises(ValueError, match="choices"):
                await svc._query_openai("prompt", 512, time.monotonic())

    async def test_openai_non_string_content_raises(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "o-key")
        svc = ComparativeAnalysisService()
        svc.openai_api_key = "o-key"

        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": {"nested": "obj"}}}]
        }
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_resp)

        with patch(
            "youtube_extension.backend.services.comparative_analysis.httpx.AsyncClient",
            return_value=mock_client,
        ):
            import time
            with pytest.raises(ValueError, match="not a string"):
                await svc._query_openai("prompt", 512, time.monotonic())


@pytest.mark.asyncio
class TestQueryLFM2:
    async def test_lfm2_query_returns_provider_result(self, monkeypatch):
        for key in ("GEMINI_API_KEY", "ANTHROPIC_API_KEY", "GROK_API_KEY",
                    "OPENAI_API_KEY", "LIQUIDAI_API_KEY"):
            monkeypatch.delenv(key, raising=False)
        svc = ComparativeAnalysisService()

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {"content": [{"type": "text", "text": "LFM2 response"}]},
        }
        mock_http = AsyncMock()
        mock_http.post = AsyncMock(return_value=mock_response)
        mock_http.aclose = AsyncMock()

        with patch(
            "youtube_extension.backend.services.comparative_analysis.httpx.AsyncClient",
            return_value=mock_http,
        ):
            import time
            result = await svc._query_lfm2("prompt", 512, time.monotonic())

        assert result.provider == "lfm2"
        assert result.response == "LFM2 response"
        assert result.model_name == "LFM2-VL"
        assert result.token_estimate > 0
        assert result.error is None


# ===========================================================================
# Module-level singleton
# ===========================================================================


class TestGetComparativeAnalysisService:
    def test_returns_service_instance(self):
        svc = get_comparative_analysis_service()
        assert isinstance(svc, ComparativeAnalysisService)

    def test_returns_same_instance_on_repeated_calls(self):
        svc1 = get_comparative_analysis_service()
        svc2 = get_comparative_analysis_service()
        assert svc1 is svc2
