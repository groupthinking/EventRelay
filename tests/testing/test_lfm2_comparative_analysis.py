#!/usr/bin/env python3
"""
Tests for the LFM2-VL Comparative Analysis Service

These tests validate the comparative analysis framework that benchmarks
LiquidAI's LFM2-VL model against existing EventRelay providers.
All network I/O is mocked so the suite runs without live API keys.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# pytest.ini already sets pythonpath=src; this fallback handles direct execution.
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from youtube_extension.backend.services.comparative_analysis import (
    AnalysisTask,
    ComparativeAnalysisService,
    ComparativeReport,
    LFM2MCPClient,
    ProviderResult,
    get_comparative_analysis_service,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SAMPLE_TRANSCRIPT = (
    "In this video we explore how LiquidAI's LFM2-VL model compares to "
    "existing vision-language models on video understanding tasks. "
    "The model demonstrates strong performance on both temporal reasoning "
    "and fine-grained visual description benchmarks."
)


def _make_provider_result(provider: str, response: str = "ok", latency: int = 100) -> ProviderResult:
    return ProviderResult(
        provider=provider,
        model_name=provider,
        response=response,
        latency_ms=latency,
    )


# ---------------------------------------------------------------------------
# ProviderResult & ComparativeReport dataclasses
# ---------------------------------------------------------------------------


class TestProviderResult:
    def test_successful_result_has_no_error(self) -> None:
        r = _make_provider_result("lfm2", response="Hello from LFM2")
        assert r.error is None
        assert r.provider == "lfm2"
        assert r.model_name == "lfm2"

    def test_error_result_carries_message(self) -> None:
        r = ProviderResult(
            provider="gemini",
            model_name="gemini-2.0-flash",
            response="",
            latency_ms=50,
            error="API quota exceeded",
        )
        assert r.error == "API quota exceeded"
        assert r.response == ""


class TestComparativeReport:
    def test_fastest_provider_selected_correctly(self) -> None:
        results = [
            _make_provider_result("lfm2", latency=200),
            _make_provider_result("gemini", latency=150),
            _make_provider_result("claude", latency=300),
        ]
        report = ComparativeReport(
            task=AnalysisTask.TRANSCRIPT_SUMMARY,
            prompt="summarise",
            results=results,
        )
        assert report.fastest_provider == "gemini"

    def test_most_verbose_provider_selected_correctly(self) -> None:
        results = [
            _make_provider_result("lfm2", response="short"),
            _make_provider_result("claude", response="a much longer response here"),
        ]
        report = ComparativeReport(
            task=AnalysisTask.EVENT_EXTRACTION,
            prompt="extract",
            results=results,
        )
        assert report.most_verbose_provider == "claude"

    def test_summary_mentions_both_providers(self) -> None:
        results = [
            _make_provider_result("lfm2", latency=100),
            _make_provider_result("gemini", latency=200, response="longer text here"),
        ]
        report = ComparativeReport(
            task=AnalysisTask.REASONING,
            prompt="reason",
            results=results,
        )
        assert report.fastest_provider in report.summary
        assert report.most_verbose_provider in report.summary

    def test_empty_results_yields_empty_fields(self) -> None:
        report = ComparativeReport(
            task=AnalysisTask.TRANSCRIPT_SUMMARY,
            prompt="test",
            results=[],
        )
        assert report.fastest_provider == ""
        assert report.summary == ""

    def test_errored_results_are_excluded_from_ranking(self) -> None:
        results = [
            ProviderResult("lfm2", "lfm2", "", 50, error="timeout"),
            _make_provider_result("gemini", response="good answer", latency=200),
        ]
        report = ComparativeReport(
            task=AnalysisTask.TRANSCRIPT_SUMMARY,
            prompt="test",
            results=results,
        )
        # Only 'gemini' is successful so it should be both fastest and most verbose
        assert report.fastest_provider == "gemini"
        assert report.most_verbose_provider == "gemini"


# ---------------------------------------------------------------------------
# LFM2MCPClient
# ---------------------------------------------------------------------------


class TestLFM2MCPClient:
    @pytest.mark.asyncio
    async def test_generate_text_parses_mcp_content_list(self) -> None:
        """Client should unwrap the MCP content list and return the text."""
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {
                "content": [{"type": "text", "text": "LFM2 says hello"}]
            },
        }

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_cls.return_value = mock_client

            async with LFM2MCPClient(base_url="http://fake-lfm2") as client:
                # Manually set the internal client to the mock
                client._client = mock_client
                text = await client.generate_text("hello")

        assert text == "LFM2 says hello"

    @pytest.mark.asyncio
    async def test_generate_text_raises_on_mcp_error(self) -> None:
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "jsonrpc": "2.0",
            "id": 1,
            "error": {"code": -32603, "message": "Internal error"},
        }

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_cls.return_value = mock_client

            async with LFM2MCPClient(base_url="http://fake-lfm2") as client:
                client._client = mock_client
                with pytest.raises(RuntimeError, match="LFM2 MCP error"):
                    await client.generate_text("hello")


# ---------------------------------------------------------------------------
# ComparativeAnalysisService
# ---------------------------------------------------------------------------


class TestComparativeAnalysisService:
    def _service_no_keys(self) -> ComparativeAnalysisService:
        """Return a service with no env-based API keys configured."""
        with patch.dict(
            "os.environ",
            {
                "GEMINI_API_KEY": "",
                "ANTHROPIC_API_KEY": "",
                "GROK_API_KEY": "",
                "OPENAI_API_KEY": "",
                "LIQUIDAI_API_KEY": "",
            },
            clear=False,
        ):
            return ComparativeAnalysisService()

    def test_available_providers_always_includes_lfm2(self) -> None:
        svc = self._service_no_keys()
        providers = svc._available_providers()
        assert "lfm2" in providers

    def test_available_providers_excludes_gemini_without_key(self) -> None:
        svc = self._service_no_keys()
        providers = svc._available_providers()
        assert "gemini" not in providers

    @pytest.mark.asyncio
    async def test_run_comparison_returns_report_with_lfm2_result(self) -> None:
        svc = self._service_no_keys()

        async def _fake_query(provider: str, prompt: str, max_tokens: int) -> ProviderResult:
            return _make_provider_result(provider, response=f"{provider} response")

        svc._query_provider = _fake_query  # type: ignore[method-assign]

        report = await svc.run_comparison(
            prompt="summarise this transcript",
            task=AnalysisTask.TRANSCRIPT_SUMMARY,
        )

        assert isinstance(report, ComparativeReport)
        assert report.task == AnalysisTask.TRANSCRIPT_SUMMARY
        assert len(report.results) >= 1
        providers = {r.provider for r in report.results}
        assert "lfm2" in providers

    @pytest.mark.asyncio
    async def test_run_comparison_subset_of_providers(self) -> None:
        """Specifying providers= should restrict which models are queried."""
        svc = self._service_no_keys()

        queried: list[str] = []

        async def _fake_query(provider: str, prompt: str, max_tokens: int) -> ProviderResult:
            queried.append(provider)
            return _make_provider_result(provider)

        svc._query_provider = _fake_query  # type: ignore[method-assign]

        await svc.run_comparison(
            prompt="test",
            providers=["lfm2"],
        )

        assert queried == ["lfm2"]

    @pytest.mark.asyncio
    async def test_run_comparison_handles_provider_exception(self) -> None:
        """Provider errors should surface as ProviderResult with error field set."""
        svc = self._service_no_keys()

        async def _fake_query(provider: str, prompt: str, max_tokens: int) -> ProviderResult:
            # The real _query_provider catches exceptions internally and returns
            # a ProviderResult with the error field set rather than raising.
            if provider == "lfm2":
                return ProviderResult(
                    provider="lfm2",
                    model_name="LFM2-VL",
                    response="",
                    latency_ms=50,
                    error="network unreachable",
                )
            return _make_provider_result(provider)

        svc._query_provider = _fake_query  # type: ignore[method-assign]

        report = await svc.run_comparison(prompt="test")
        lfm2_results = [r for r in report.results if r.provider == "lfm2"]
        assert len(lfm2_results) == 1
        assert lfm2_results[0].error == "network unreachable"

    @pytest.mark.asyncio
    async def test_run_full_suite_covers_all_tasks(self) -> None:
        svc = self._service_no_keys()

        async def _fake_query(provider: str, prompt: str, max_tokens: int) -> ProviderResult:
            return _make_provider_result(provider)

        svc._query_provider = _fake_query  # type: ignore[method-assign]

        reports = await svc.run_full_suite(video_transcript=SAMPLE_TRANSCRIPT)

        expected_tasks = {
            AnalysisTask.TRANSCRIPT_SUMMARY.value,
            AnalysisTask.EVENT_EXTRACTION.value,
            AnalysisTask.REASONING.value,
        }
        assert set(reports.keys()) == expected_tasks

    def test_singleton_returns_same_instance(self) -> None:
        import youtube_extension.backend.services.comparative_analysis as mod

        # Reset the singleton
        mod._service = None

        svc1 = get_comparative_analysis_service()
        svc2 = get_comparative_analysis_service()
        assert svc1 is svc2

        # Cleanup
        mod._service = None


# ---------------------------------------------------------------------------
# Analysis task enum
# ---------------------------------------------------------------------------


class TestAnalysisTask:
    def test_all_task_values_are_strings(self) -> None:
        for task in AnalysisTask:
            assert isinstance(task.value, str)

    def test_task_has_vision_description(self) -> None:
        assert AnalysisTask.VISION_DESCRIPTION.value == "vision_description"


# ---------------------------------------------------------------------------
# Entry point (run directly)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import subprocess

    subprocess.run(
        [sys.executable, "-m", "pytest", __file__, "-v"],
        check=False,
    )
