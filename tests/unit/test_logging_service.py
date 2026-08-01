"""Unit tests for LogLevel, StructuredLogEntry, and ErrorAggregator."""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from youtube_extension.backend.services.logging_service import (
    ErrorAggregator,
    LogLevel,
    StructuredLogEntry,
)

MODULE_PATH = "youtube_extension.backend.services.logging_service"

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


# ===========================================================================
# LoggingService — needs async context for asyncio.create_task in __init__
# ===========================================================================

from youtube_extension.backend.services.logging_service import LoggingService


class TestLoggingServiceInit:
    @pytest.fixture
    async def service(self, tmp_path):
        return LoggingService(config={"log_directory": tmp_path / "logs", "enable_remote_logging": False})

    async def test_buffer_starts_empty(self, service):
        assert service.log_buffer == []

    async def test_config_loaded(self, service):
        assert "buffer_size" in service.config

    async def test_error_aggregator_is_instance(self, service):
        assert isinstance(service.error_aggregator, ErrorAggregator)

    async def test_start_time_set(self, service):
        assert service.start_time > 0

    async def test_metrics_cache_empty(self, service):
        assert service.metrics_cache == {}


class TestLoggingServiceLogStructured:
    @pytest.fixture
    async def service(self, tmp_path):
        return LoggingService(config={"log_directory": tmp_path / "logs", "enable_remote_logging": False})

    async def test_log_structured_adds_to_buffer(self, service):
        await service.log_structured("INFO", "Test message")
        assert len(service.log_buffer) == 1

    async def test_log_structured_entry_has_message(self, service):
        await service.log_structured("INFO", "Hello world")
        entry = service.log_buffer[-1]
        assert entry.message == "Hello world"

    async def test_log_structured_level_uppercased(self, service):
        await service.log_structured("warning", "Low disk space")
        entry = service.log_buffer[-1]
        assert entry.level == "WARNING"

    async def test_log_structured_numeric_level(self, service):
        import logging
        await service.log_structured(logging.ERROR, "Error occurred")
        entry = service.log_buffer[-1]
        assert entry.level == "ERROR"

    async def test_log_structured_kwargs_stored(self, service):
        await service.log_structured("INFO", "Request", endpoint="/api/v1/test", status_code=200)
        entry = service.log_buffer[-1]
        assert entry.endpoint == "/api/v1/test"
        assert entry.status_code == 200

    async def test_multiple_logs_accumulate(self, service):
        for i in range(5):
            await service.log_structured("INFO", f"Message {i}")
        assert len(service.log_buffer) == 5


class TestLoggingServiceLogError:
    @pytest.fixture
    async def service(self, tmp_path):
        return LoggingService(config={"log_directory": tmp_path / "logs", "enable_remote_logging": False, "enable_error_aggregation": True})

    async def test_log_error_returns_error_id(self, service):
        error_id = await service.log_error(ValueError("test error"))
        assert error_id.startswith("ERR_")

    async def test_log_error_adds_to_buffer(self, service):
        await service.log_error(RuntimeError("runtime error"))
        assert len(service.log_buffer) >= 1

    async def test_log_error_with_context(self, service):
        error_id = await service.log_error(KeyError("missing key"), context={"key": "test"})
        assert error_id is not None

    async def test_log_error_adds_to_aggregator(self, service):
        await service.log_error(ValueError("agg test"))
        # Error should be in aggregator
        summary = service.error_aggregator.get_error_summary()
        assert summary["total_errors"] >= 1


class TestLoggingServiceLogApiRequest:
    @pytest.fixture
    async def service(self, tmp_path):
        return LoggingService(config={"log_directory": tmp_path / "logs", "enable_remote_logging": False})

    async def test_2xx_uses_info_level(self, service):
        await service.log_api_request("GET", "/api/health", 200, 50.0)
        entry = service.log_buffer[-1]
        assert entry.level == "INFO"

    async def test_4xx_uses_warning_level(self, service):
        await service.log_api_request("GET", "/api/missing", 404, 10.0)
        entry = service.log_buffer[-1]
        assert entry.level == "WARNING"

    async def test_5xx_uses_error_level(self, service):
        await service.log_api_request("POST", "/api/process", 500, 1000.0)
        entry = service.log_buffer[-1]
        assert entry.level == "ERROR"

    async def test_stores_method_and_endpoint(self, service):
        await service.log_api_request("DELETE", "/api/resource", 204, 5.0)
        entry = service.log_buffer[-1]
        assert entry.method == "DELETE"
        assert entry.endpoint == "/api/resource"

    async def test_stores_duration_ms(self, service):
        await service.log_api_request("GET", "/api/test", 200, 123.45)
        entry = service.log_buffer[-1]
        assert entry.duration_ms == 123.45


class TestLoggingServiceLogPerformanceMetric:
    @pytest.fixture
    async def service(self, tmp_path):
        return LoggingService(config={"log_directory": tmp_path / "logs", "enable_remote_logging": False})

    async def test_logs_performance_metric(self, service):
        await service.log_performance_metric("video_processing", 1500.0)
        assert len(service.log_buffer) >= 1

    async def test_entry_has_duration(self, service):
        await service.log_performance_metric("db_query", 25.0)
        entry = service.log_buffer[-1]
        assert entry.duration_ms == 25.0

    async def test_entry_tags_include_performance(self, service):
        await service.log_performance_metric("cache_hit", 1.0)
        entry = service.log_buffer[-1]
        assert "performance" in entry.tags


class TestLoggingServiceFlushLogs:
    @pytest.fixture
    async def service(self, tmp_path):
        return LoggingService(config={"log_directory": tmp_path / "logs", "enable_remote_logging": False})

    async def test_flush_empty_buffer_no_error(self, service):
        await service.flush_logs()

    async def test_flush_clears_buffer(self, service, tmp_path):
        await service.log_structured("INFO", "msg1")
        await service.log_structured("INFO", "msg2")
        assert len(service.log_buffer) == 2
        await service.flush_logs()
        assert len(service.log_buffer) == 0


class TestLoggingServiceGetHealthStatus:
    @pytest.fixture
    async def service(self, tmp_path):
        return LoggingService(config={"log_directory": tmp_path / "logs", "enable_remote_logging": False})

    async def test_returns_dict(self, service):
        status = service.get_health_status()
        assert isinstance(status, dict)

    async def test_has_status_healthy(self, service):
        status = service.get_health_status()
        assert status["status"] == "healthy"

    async def test_has_buffer_size(self, service):
        status = service.get_health_status()
        assert "buffer_size" in status

    async def test_has_uptime(self, service):
        status = service.get_health_status()
        assert "uptime_seconds" in status
        assert status["uptime_seconds"] >= 0


# ===========================================================================
# LoggingService._write_to_files — batching
# ===========================================================================


class TestLoggingServiceWriteToFiles:
    """Tests for _write_to_files().

    aiofiles delegates every ``write()`` to the thread-pool executor, so the
    number of ``write()`` calls -- not the number of bytes -- is what costs.
    These tests pin the batch to a single write per file.
    """

    @pytest.fixture
    async def service(self, tmp_path):
        return LoggingService(
            config={"log_directory": tmp_path / "logs", "enable_remote_logging": False}
        )

    @staticmethod
    def _entries(n: int, level: str = "INFO") -> list[StructuredLogEntry]:
        return [
            StructuredLogEntry(
                timestamp=f"2026-01-01T00:00:{i:02d}Z",
                level=level,
                logger_name="test",
                message=f"msg-{i}",
            )
            for i in range(n)
        ]

    async def test_batches_structured_logs_into_one_write(self, service, tmp_path):
        writes: list[str] = []

        class _FakeFile:
            async def write(self, data):
                writes.append(data)

            async def __aenter__(self):
                return self

            async def __aexit__(self, *exc):
                return False

        with patch(f"{MODULE_PATH}.aiofiles.open", return_value=_FakeFile()):
            await service._write_to_files(self._entries(25))

        assert len(writes) == 1, (
            f"_write_to_files issued {len(writes)} write() calls for 25 log entries; "
            "each aiofiles write is a separate thread-pool round-trip, so the batch "
            "must be serialised into a single write"
        )
        assert writes[0].count("\n") == 25

    async def test_batches_error_logs_into_one_write(self, service, tmp_path):
        writes: list[str] = []

        class _FakeFile:
            async def write(self, data):
                writes.append(data)

            async def __aenter__(self):
                return self

            async def __aexit__(self, *exc):
                return False

        with patch(f"{MODULE_PATH}.aiofiles.open", return_value=_FakeFile()):
            await service._write_to_files(self._entries(12, level="ERROR"))

        # One write for structured_logs.jsonl, one for error_logs.jsonl.
        assert len(writes) == 2, (
            f"_write_to_files issued {len(writes)} write() calls for 12 ERROR entries; "
            "expected exactly one batched write per file"
        )
        assert all(payload.count("\n") == 12 for payload in writes)

    async def test_writes_every_entry_exactly_once(self, service, tmp_path):
        await service._write_to_files(self._entries(5))

        path = tmp_path / "logs" / "structured_logs.jsonl"
        lines = [ln for ln in path.read_text().splitlines() if ln.strip()]
        assert len(lines) == 5
        assert [json.loads(ln)["message"] for ln in lines] == [f"msg-{i}" for i in range(5)]

    async def test_appends_rather_than_truncating(self, service, tmp_path):
        await service._write_to_files(self._entries(3))
        await service._write_to_files(self._entries(2))

        path = tmp_path / "logs" / "structured_logs.jsonl"
        lines = [ln for ln in path.read_text().splitlines() if ln.strip()]
        assert len(lines) == 5

    async def test_error_logs_routed_to_separate_file(self, service, tmp_path):
        mixed = self._entries(2, level="INFO") + self._entries(3, level="CRITICAL")
        await service._write_to_files(mixed)

        structured = tmp_path / "logs" / "structured_logs.jsonl"
        errors = tmp_path / "logs" / "error_logs.jsonl"
        assert len([ln for ln in structured.read_text().splitlines() if ln.strip()]) == 5
        assert len([ln for ln in errors.read_text().splitlines() if ln.strip()]) == 3

    async def test_no_error_content_written_when_no_error_logs(self, service, tmp_path):
        await service._write_to_files(self._entries(4, level="INFO"))
        errors = tmp_path / "logs" / "error_logs.jsonl"
        # The service pre-creates its log files at init, so assert on content.
        existing = errors.read_text() if errors.exists() else ""
        assert [ln for ln in existing.splitlines() if ln.strip()] == []

    async def test_empty_batch_does_not_raise(self, service):
        await service._write_to_files([])
