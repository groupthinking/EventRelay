"""Unit tests for LogLevel, StructuredLogEntry, and ErrorAggregator."""

from __future__ import annotations

import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from youtube_extension.backend.services.logging_service import (
    ErrorAggregator,
    LogLevel,
    StructuredLogEntry,
)


# ===========================================================================
# LogLevel constants
# ===========================================================================


class TestLogLevel:
    def test_debug_is_lowest(self):
        assert LogLevel.DEBUG == 10

    def test_ascending_order(self):
        assert LogLevel.DEBUG < LogLevel.INFO < LogLevel.WARNING < LogLevel.ERROR < LogLevel.CRITICAL

    def test_critical_is_50(self):
        assert LogLevel.CRITICAL == 50


# ===========================================================================
# StructuredLogEntry (Pydantic model)
# ===========================================================================


class TestStructuredLogEntry:
    def _make(self, **kw) -> StructuredLogEntry:
        defaults = dict(timestamp="2024-01-01T00:00:00Z", level="INFO", logger_name="test", message="hello")
        return StructuredLogEntry(**{**defaults, **kw})

    def test_required_fields_accepted(self):
        entry = self._make()
        assert entry.level == "INFO"
        assert entry.message == "hello"

    def test_service_name_default(self):
        assert self._make().service_name == "youtube-extension-api"

    def test_version_default(self):
        assert self._make().version == "2.0.0"

    def test_environment_default(self):
        assert self._make().environment == "production"

    def test_optional_fields_default_none(self):
        entry = self._make()
        assert entry.request_id is None
        assert entry.user_id is None
        assert entry.duration_ms is None
        assert entry.error_type is None
        assert entry.endpoint is None

    def test_tags_default_empty(self):
        assert self._make().tags == []

    def test_metadata_default_empty(self):
        assert self._make().metadata == {}

    def test_custom_fields_set(self):
        entry = self._make(
            request_id="req-123",
            duration_ms=42.5,
            status_code=200,
            endpoint="/api/v1/health",
        )
        assert entry.request_id == "req-123"
        assert entry.duration_ms == 42.5
        assert entry.status_code == 200
        assert entry.endpoint == "/api/v1/health"

    def test_error_fields(self):
        entry = self._make(
            error_type="ValueError",
            error_message="bad input",
            error_code="E001",
        )
        assert entry.error_type == "ValueError"
        assert entry.error_message == "bad input"


# ===========================================================================
# ErrorAggregator
# ===========================================================================


class TestErrorAggregatorInit:
    def test_default_window_size(self):
        agg = ErrorAggregator()
        assert agg.window_size == 3600

    def test_custom_window_size(self):
        agg = ErrorAggregator(window_size=600)
        assert agg.window_size == 600

    def test_starts_empty(self):
        agg = ErrorAggregator()
        assert agg.error_buckets == {}


class TestErrorAggregatorAddError:
    def test_adds_first_error(self):
        agg = ErrorAggregator()
        agg.add_error("ValueError", {"msg": "bad"})
        assert "ValueError" in agg.error_buckets
        assert len(agg.error_buckets["ValueError"]) == 1

    def test_adds_multiple_same_signature(self):
        agg = ErrorAggregator()
        agg.add_error("TypeError", {"msg": "a"})
        agg.add_error("TypeError", {"msg": "b"})
        assert len(agg.error_buckets["TypeError"]) == 2

    def test_different_signatures_separate_buckets(self):
        agg = ErrorAggregator()
        agg.add_error("TypeError", {"msg": "a"})
        agg.add_error("ValueError", {"msg": "b"})
        assert len(agg.error_buckets) == 2

    def test_error_entry_has_timestamp(self):
        agg = ErrorAggregator()
        before = time.time()
        agg.add_error("SomeError", {"detail": "x"})
        after = time.time()
        ts = agg.error_buckets["SomeError"][0]["timestamp"]
        assert before <= ts <= after

    def test_error_entry_stores_data(self):
        agg = ErrorAggregator()
        agg.add_error("KeyError", {"key": "missing_field"})
        assert agg.error_buckets["KeyError"][0]["data"] == {"key": "missing_field"}


class TestErrorAggregatorGetSummary:
    def test_empty_summary(self):
        agg = ErrorAggregator()
        summary = agg.get_error_summary()
        assert summary["total_errors"] == 0
        assert summary["error_rate_per_minute"] == 0
        assert summary["top_errors"] == []

    def test_total_errors_counted(self):
        agg = ErrorAggregator()
        agg.add_error("E1", {})
        agg.add_error("E1", {})
        agg.add_error("E2", {})
        summary = agg.get_error_summary()
        assert summary["total_errors"] == 3

    def test_error_trends_per_signature(self):
        agg = ErrorAggregator()
        for _ in range(3):
            agg.add_error("SigA", {})
        agg.add_error("SigB", {})
        summary = agg.get_error_summary()
        assert summary["error_trends"]["SigA"] == 3
        assert summary["error_trends"]["SigB"] == 1

    def test_top_errors_sorted_by_count(self):
        agg = ErrorAggregator()
        for _ in range(5):
            agg.add_error("FreqError", {})
        agg.add_error("RareError", {})
        summary = agg.get_error_summary()
        top = summary["top_errors"]
        assert top[0][0] == "FreqError"
        assert top[0][1] == 5

    def test_error_rate_positive_when_errors_present(self):
        agg = ErrorAggregator()
        agg.add_error("E", {})
        summary = agg.get_error_summary()
        assert summary["error_rate_per_minute"] > 0


class TestErrorAggregatorCleanup:
    def test_cleanup_removes_old_errors(self):
        agg = ErrorAggregator(window_size=60)
        old_time = time.time() - 120  # 2 minutes ago, outside 60s window
        agg.error_buckets["OldError"] = [{"timestamp": old_time, "data": {}}]
        agg._cleanup_old_errors()
        assert "OldError" not in agg.error_buckets

    def test_cleanup_keeps_recent_errors(self):
        agg = ErrorAggregator(window_size=3600)
        agg.add_error("RecentError", {})
        agg._cleanup_old_errors()
        assert "RecentError" in agg.error_buckets

    def test_cleanup_removes_empty_buckets(self):
        agg = ErrorAggregator(window_size=60)
        old_time = time.time() - 120
        agg.error_buckets["DeadBucket"] = [{"timestamp": old_time, "data": {}}]
        agg._cleanup_old_errors()
        assert "DeadBucket" not in agg.error_buckets
