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
    def test_debug_is_10(self):
        assert LogLevel.DEBUG == 10

    def test_info_is_20(self):
        assert LogLevel.INFO == 20

    def test_warning_is_30(self):
        assert LogLevel.WARNING == 30

    def test_error_is_40(self):
        assert LogLevel.ERROR == 40

    def test_critical_is_50(self):
        assert LogLevel.CRITICAL == 50

    def test_ordered_correctly(self):
        assert LogLevel.DEBUG < LogLevel.INFO < LogLevel.WARNING < LogLevel.ERROR < LogLevel.CRITICAL


# ===========================================================================
# StructuredLogEntry
# ===========================================================================


class TestStructuredLogEntry:
    @pytest.fixture
    def entry(self):
        return StructuredLogEntry(
            timestamp="2024-01-01T12:00:00Z",
            level="INFO",
            logger_name="test.logger",
            message="Test message",
        )

    def test_required_fields_stored(self, entry):
        assert entry.timestamp == "2024-01-01T12:00:00Z"
        assert entry.level == "INFO"
        assert entry.logger_name == "test.logger"
        assert entry.message == "Test message"

    def test_service_name_default(self, entry):
        assert entry.service_name == "youtube-extension-api"

    def test_version_default(self, entry):
        assert entry.version == "2.0.0"

    def test_environment_default(self, entry):
        assert entry.environment == "production"

    def test_request_id_default_none(self, entry):
        assert entry.request_id is None

    def test_user_id_default_none(self, entry):
        assert entry.user_id is None

    def test_session_id_default_none(self, entry):
        assert entry.session_id is None

    def test_correlation_id_default_none(self, entry):
        assert entry.correlation_id is None

    def test_duration_ms_default_none(self, entry):
        assert entry.duration_ms is None

    def test_error_type_default_none(self, entry):
        assert entry.error_type is None

    def test_error_message_default_none(self, entry):
        assert entry.error_message is None

    def test_stack_trace_default_none(self, entry):
        assert entry.stack_trace is None

    def test_endpoint_default_none(self, entry):
        assert entry.endpoint is None

    def test_tags_default_empty(self, entry):
        assert entry.tags == []

    def test_metadata_default_empty(self, entry):
        assert entry.metadata == {}

    def test_custom_fields(self):
        e = StructuredLogEntry(
            timestamp="2024-01-01T00:00:00Z",
            level="ERROR",
            logger_name="api",
            message="Error occurred",
            request_id="req-123",
            error_type="ValueError",
            duration_ms=150.0,
            tags=["critical"],
            metadata={"key": "val"},
        )
        assert e.request_id == "req-123"
        assert e.error_type == "ValueError"
        assert e.duration_ms == 150.0
        assert e.tags == ["critical"]
        assert e.metadata["key"] == "val"


# ===========================================================================
# ErrorAggregator
# ===========================================================================


class TestErrorAggregatorInit:
    def test_window_size_default(self):
        ea = ErrorAggregator()
        assert ea.window_size == 3600

    def test_custom_window_size(self):
        ea = ErrorAggregator(window_size=60)
        assert ea.window_size == 60

    def test_error_buckets_empty(self):
        ea = ErrorAggregator()
        assert ea.error_buckets == {}

    def test_last_cleanup_recent(self):
        before = time.time()
        ea = ErrorAggregator()
        assert ea.last_cleanup >= before


class TestErrorAggregatorAddError:
    def test_adds_error_to_bucket(self):
        ea = ErrorAggregator()
        ea.add_error("ValueError", {"msg": "test"})
        assert "ValueError" in ea.error_buckets

    def test_error_count_increments(self):
        ea = ErrorAggregator()
        ea.add_error("TypeError", {"msg": "a"})
        ea.add_error("TypeError", {"msg": "b"})
        assert len(ea.error_buckets["TypeError"]) == 2

    def test_different_signatures_separate(self):
        ea = ErrorAggregator()
        ea.add_error("ValueError", {"msg": "a"})
        ea.add_error("TypeError", {"msg": "b"})
        assert len(ea.error_buckets) == 2

    def test_error_entry_has_timestamp(self):
        before = time.time()
        ea = ErrorAggregator()
        ea.add_error("Err", {"x": 1})
        assert ea.error_buckets["Err"][0]["timestamp"] >= before

    def test_error_entry_has_data(self):
        ea = ErrorAggregator()
        ea.add_error("Err", {"code": 500})
        assert ea.error_buckets["Err"][0]["data"] == {"code": 500}


class TestErrorAggregatorGetSummary:
    def test_empty_summary(self):
        ea = ErrorAggregator()
        summary = ea.get_error_summary()
        assert summary["total_errors"] == 0
        assert summary["error_rate_per_minute"] == 0

    def test_summary_has_required_keys(self):
        ea = ErrorAggregator()
        summary = ea.get_error_summary()
        for key in ["total_errors", "error_rate_per_minute", "top_errors", "error_trends"]:
            assert key in summary

    def test_total_errors_counted(self):
        ea = ErrorAggregator()
        ea.add_error("ValueError", {"m": "1"})
        ea.add_error("ValueError", {"m": "2"})
        ea.add_error("TypeError", {"m": "3"})
        summary = ea.get_error_summary()
        assert summary["total_errors"] == 3

    def test_error_trends_populated(self):
        ea = ErrorAggregator()
        ea.add_error("ValueError", {"m": "1"})
        ea.add_error("ValueError", {"m": "2"})
        summary = ea.get_error_summary()
        assert summary["error_trends"]["ValueError"] == 2

    def test_error_rate_positive_when_errors_present(self):
        ea = ErrorAggregator()
        ea.add_error("Err", {})
        summary = ea.get_error_summary()
        assert summary["error_rate_per_minute"] > 0
