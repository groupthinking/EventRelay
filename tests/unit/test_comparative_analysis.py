"""Unit tests for AnalysisTask, ProviderResult, ComparativeReport dataclasses."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from youtube_extension.backend.services.comparative_analysis import (
    AnalysisTask,
    ComparativeReport,
    ProviderResult,
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
