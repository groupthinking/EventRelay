"""Unit tests for PerformanceMetric dataclass and PerformanceMonitor pure logic."""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from youtube_extension.backend.services.performance_monitor import (
    PerformanceAlert,
    PerformanceMetric,
    PerformanceMonitor,
)


# ===========================================================================
# PerformanceMetric dataclass
# ===========================================================================


class TestPerformanceMetric:
    def _make(self, **kw) -> PerformanceMetric:
        defaults = dict(
            component="api",
            metric_name="response_time",
            value=150.0,
            timestamp=datetime.now(timezone.utc),
        )
        return PerformanceMetric(**{**defaults, **kw})

    def test_required_fields_stored(self):
        m = self._make(component="db", metric_name="query_time", value=42.5)
        assert m.component == "db"
        assert m.metric_name == "query_time"
        assert m.value == 42.5

    def test_unit_default_is_ms(self):
        assert self._make().unit == "ms"

    def test_custom_unit_stored(self):
        m = self._make(unit="%")
        assert m.unit == "%"

    def test_tags_default_empty_dict(self):
        m = self._make()
        assert m.tags == {}

    def test_tags_none_replaced_with_empty_dict(self):
        m = self._make(tags=None)
        assert m.tags == {}

    def test_custom_tags_stored(self):
        m = self._make(tags={"endpoint": "/api/health"})
        assert m.tags["endpoint"] == "/api/health"

    def test_timestamp_stored(self):
        ts = datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
        m = self._make(timestamp=ts)
        assert m.timestamp == ts

    def test_integer_value_accepted(self):
        m = self._make(value=100)
        assert m.value == 100


# ===========================================================================
# PerformanceAlert dataclass
# ===========================================================================


class TestPerformanceAlert:
    def _make(self, **kw) -> PerformanceAlert:
        defaults = dict(
            alert_id="test-alert-1",
            component="api",
            metric_name="response_time",
            threshold=2000.0,
            current_value=3500.0,
            severity="warning",
            message="Response time exceeded threshold",
            timestamp=datetime.now(timezone.utc),
        )
        return PerformanceAlert(**{**defaults, **kw})

    def test_required_fields_stored(self):
        a = self._make()
        assert a.alert_id == "test-alert-1"
        assert a.component == "api"
        assert a.severity == "warning"

    def test_resolved_defaults_false(self):
        assert self._make().resolved is False

    def test_resolved_can_be_true(self):
        a = self._make(resolved=True)
        assert a.resolved is True

    def test_threshold_and_current_stored(self):
        a = self._make(threshold=100.0, current_value=250.0)
        assert a.threshold == 100.0
        assert a.current_value == 250.0


# ===========================================================================
# PerformanceMonitor init and pure structure
# ===========================================================================


class TestPerformanceMonitorInit:
    @pytest.fixture
    def monitor(self, tmp_path):
        return PerformanceMonitor(db_path=str(tmp_path / "perf.db"))

    def test_db_path_stored(self, tmp_path):
        path = str(tmp_path / "perf.db")
        m = PerformanceMonitor(db_path=path)
        assert m.db_path == path

    def test_monitoring_enabled_on_init(self, monitor):
        assert monitor.monitoring_enabled is True

    def test_active_alerts_starts_empty(self, monitor):
        assert monitor.active_alerts == {}

    def test_metrics_buffer_starts_empty(self, monitor):
        assert len(monitor.metrics_buffer) == 0

    def test_alert_thresholds_defined(self, monitor):
        assert "video_processing_time" in monitor.alert_thresholds
        assert "database_query_time" in monitor.alert_thresholds
        assert "memory_usage_percent" in monitor.alert_thresholds

    def test_threshold_has_warning_and_critical(self, monitor):
        vt = monitor.alert_thresholds["video_processing_time"]
        assert "warning" in vt
        assert "critical" in vt

    def test_video_processing_warning_below_critical(self, monitor):
        vt = monitor.alert_thresholds["video_processing_time"]
        assert vt["warning"] < vt["critical"]

    def test_database_query_warning_is_100ms(self, monitor):
        assert monitor.alert_thresholds["database_query_time"]["warning"] == 100

    def test_db_file_created_on_init(self, tmp_path):
        path = str(tmp_path / "perf_test.db")
        PerformanceMonitor(db_path=path)
        import os
        assert os.path.exists(path)

    def test_video_processing_times_deque_empty(self, monitor):
        assert len(monitor.video_processing_times) == 0

    def test_database_query_times_deque_empty(self, monitor):
        assert len(monitor.database_query_times) == 0


# ===========================================================================
# PerformanceMonitor._get_system_health — pure structural test
# ===========================================================================


class TestGetSystemHealthStructure:
    @pytest.fixture
    def monitor(self, tmp_path):
        return PerformanceMonitor(db_path=str(tmp_path / "perf.db"))

    @pytest.mark.asyncio
    async def test_health_has_expected_keys(self, monitor):
        health = await monitor._get_system_health()
        assert "video_processing" in health
        assert "database_queries" in health
        assert "api_responses" in health

    @pytest.mark.asyncio
    async def test_empty_health_video_avg_zero(self, monitor):
        health = await monitor._get_system_health()
        assert health["video_processing"]["avg_time_ms"] == 0

    @pytest.mark.asyncio
    async def test_empty_health_db_avg_zero(self, monitor):
        health = await monitor._get_system_health()
        assert health["database_queries"]["avg_time_ms"] == 0

    @pytest.mark.asyncio
    async def test_health_target_values_present(self, monitor):
        health = await monitor._get_system_health()
        assert health["video_processing"]["target_ms"] == 30000
        assert health["database_queries"]["target_ms"] == 100
        assert health["api_responses"]["target_ms"] == 2000

    @pytest.mark.asyncio
    async def test_empty_meeting_target_is_false(self, monitor):
        health = await monitor._get_system_health()
        assert health["video_processing"]["meeting_target"] is False
        assert health["database_queries"]["meeting_target"] is False
