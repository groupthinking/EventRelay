"""Unit tests for PerformanceMetric dataclass and PerformanceMonitor pure logic."""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Restore real psutil BEFORE importing any module under test.
# test_index_analysis.py replaces sys.modules['psutil'] with a MagicMock at
# collection time; because test files are collected alphabetically, any file
# that sorts after it would receive the mock.  We undo that here so that
# performance_monitor (which calls psutil.cpu_percent etc.) gets the real lib.
# ---------------------------------------------------------------------------
import sys
sys.modules.pop('psutil', None)
import psutil as _real_psutil
sys.modules['psutil'] = _real_psutil
sys.modules.pop('youtube_extension.backend.services.performance_monitor', None)

from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch, AsyncMock

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

    def test_tags_is_dict_type(self):
        m = self._make()
        assert isinstance(m.tags, dict)

    def test_multiple_tags_stored(self):
        tags = {"endpoint": "/v1/events", "method": "POST"}
        m = self._make(tags=tags)
        assert m.tags == tags


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

    def test_message_stored(self):
        a = self._make(message="CPU critical")
        assert a.message == "CPU critical"

    def test_severity_critical(self):
        a = self._make(severity="critical")
        assert a.severity == "critical"

    def test_timestamp_stored(self):
        ts = datetime(2025, 1, 15, 8, 0, 0, tzinfo=timezone.utc)
        a = self._make(timestamp=ts)
        assert a.timestamp == ts


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

    def test_metrics_buffer_is_deque(self, monitor):
        assert isinstance(monitor.metrics_buffer, deque)

    def test_api_response_times_deque_empty(self, monitor):
        assert len(monitor.api_response_times) == 0

    def test_alert_thresholds_has_cpu(self, monitor):
        assert "cpu_usage_percent" in monitor.alert_thresholds

    def test_alert_thresholds_has_api_response(self, monitor):
        assert "api_response_time" in monitor.alert_thresholds

    def test_monitoring_task_is_none(self, monitor):
        # No running event loop at construction time → task deferred
        assert monitor.monitoring_task is None

    def test_benchmark_results_starts_empty(self, monitor):
        assert monitor.benchmark_results == {}

    def test_optimization_history_starts_empty(self, monitor):
        assert monitor.optimization_history == []


# ===========================================================================
# PerformanceMonitor.record_metric (async)
# ===========================================================================


class TestRecordMetric:
    @pytest.fixture
    def monitor(self, tmp_path):
        return PerformanceMonitor(db_path=str(tmp_path / "perf.db"))

    async def test_record_metric_adds_to_buffer(self, monitor):
        await monitor.record_metric("api", "response_time", 123.4)
        assert len(monitor.metrics_buffer) == 1

    async def test_record_metric_multiple_adds(self, monitor):
        await monitor.record_metric("api", "response_time", 100.0)
        await monitor.record_metric("db", "query_time", 50.0)
        assert len(monitor.metrics_buffer) == 2

    async def test_record_metric_updates_video_deque(self, monitor):
        await monitor.record_metric("video_processor", "video_processing_time", 15000.0)
        assert len(monitor.video_processing_times) == 1
        assert monitor.video_processing_times[0] == 15000.0

    async def test_record_metric_updates_db_deque(self, monitor):
        await monitor.record_metric("database", "database_query_time", 75.0)
        assert len(monitor.database_query_times) == 1
        assert monitor.database_query_times[0] == 75.0

    async def test_record_metric_updates_api_deque(self, monitor):
        await monitor.record_metric("api", "api_response_time", 500.0)
        assert len(monitor.api_response_times) == 1
        assert monitor.api_response_times[0] == 500.0

    async def test_record_metric_stores_correct_component(self, monitor):
        await monitor.record_metric("frontend", "page_load_time", 800.0)
        item = monitor.metrics_buffer[-1]
        assert item.component == "frontend"
        assert item.metric_name == "page_load_time"
        assert item.value == 800.0

    async def test_record_metric_default_unit_ms(self, monitor):
        await monitor.record_metric("sys", "cpu", 55.0)
        item = monitor.metrics_buffer[-1]
        assert item.unit == "ms"

    async def test_record_metric_custom_unit(self, monitor):
        await monitor.record_metric("system", "memory_usage_percent", 60.0, unit="%")
        item = monitor.metrics_buffer[-1]
        assert item.unit == "%"

    async def test_record_metric_tags_stored(self, monitor):
        await monitor.record_metric("api", "response_time", 200.0, tags={"endpoint": "/health"})
        item = monitor.metrics_buffer[-1]
        assert item.tags.get("endpoint") == "/health"


# ===========================================================================
# PerformanceMonitor.get_current_performance_summary (async)
# ===========================================================================


class TestGetCurrentPerformanceSummary:
    @pytest.fixture
    def monitor(self, tmp_path):
        return PerformanceMonitor(db_path=str(tmp_path / "perf.db"))

    async def test_returns_dict(self, monitor):
        result = await monitor.get_current_performance_summary()
        assert isinstance(result, dict)

    async def test_empty_db_returns_empty_dict(self, monitor):
        result = await monitor.get_current_performance_summary()
        assert result == {}

    async def test_after_recording_returns_component(self, monitor):
        await monitor.record_metric("api", "response_time", 100.0)
        result = await monitor.get_current_performance_summary()
        assert "api" in result

    async def test_summary_has_metric_values(self, monitor):
        await monitor.record_metric("api", "response_time", 200.0)
        result = await monitor.get_current_performance_summary()
        assert "response_time" in result.get("api", {})

    async def test_avg_value_is_float(self, monitor):
        await monitor.record_metric("db", "query_time", 50.0)
        await monitor.record_metric("db", "query_time", 100.0)
        result = await monitor.get_current_performance_summary()
        avg = result["db"]["query_time"]
        assert isinstance(avg, float)
        assert avg == 75.0

    async def test_multiple_components_returned(self, monitor):
        await monitor.record_metric("api", "response_time", 100.0)
        await monitor.record_metric("db", "query_time", 50.0)
        result = await monitor.get_current_performance_summary()
        assert "api" in result
        assert "db" in result


# ===========================================================================
# PerformanceMonitor.trigger_manual_cleanup (async)
# ===========================================================================


class TestTriggerManualCleanup:
    @pytest.fixture
    def monitor(self, tmp_path):
        return PerformanceMonitor(db_path=str(tmp_path / "perf.db"))

    async def test_returns_dict(self, monitor):
        result = await monitor.trigger_manual_cleanup()
        assert isinstance(result, dict)

    async def test_result_has_database_key_when_cleanup_available(self, monitor):
        import youtube_extension.backend.services.performance_monitor as pm_mod
        if pm_mod.CLEANUP_AVAILABLE:
            result = await monitor.trigger_manual_cleanup()
            assert "database" in result or "error" in result
        else:
            result = await monitor.trigger_manual_cleanup()
            assert "error" in result

    async def test_error_key_when_cleanup_not_available(self, tmp_path):
        import youtube_extension.backend.services.performance_monitor as pm_mod
        monitor = PerformanceMonitor(db_path=str(tmp_path / "perf2.db"))
        original = pm_mod.CLEANUP_AVAILABLE
        pm_mod.CLEANUP_AVAILABLE = False
        try:
            result = await monitor.trigger_manual_cleanup()
            assert "error" in result
            assert result["error"] == "Cleanup service not available"
        finally:
            pm_mod.CLEANUP_AVAILABLE = original

    async def test_cleanup_available_returns_tables_cleaned(self, monitor):
        import youtube_extension.backend.services.performance_monitor as pm_mod
        if pm_mod.CLEANUP_AVAILABLE:
            result = await monitor.trigger_manual_cleanup()
            if "error" not in result:
                assert "tables_cleaned" in result

    async def test_cleanup_available_returns_execution_time(self, monitor):
        import youtube_extension.backend.services.performance_monitor as pm_mod
        if pm_mod.CLEANUP_AVAILABLE:
            result = await monitor.trigger_manual_cleanup()
            if "error" not in result:
                assert "execution_time_seconds" in result
                assert isinstance(result["execution_time_seconds"], float)

    async def test_cleanup_available_returns_details_list(self, monitor):
        import youtube_extension.backend.services.performance_monitor as pm_mod
        if pm_mod.CLEANUP_AVAILABLE:
            result = await monitor.trigger_manual_cleanup()
            if "error" not in result:
                assert "details" in result
                assert isinstance(result["details"], list)


# ===========================================================================
# PerformanceMonitor._generate_optimization_recommendations (async)
# ===========================================================================


class TestGenerateOptimizationRecommendations:
    @pytest.fixture
    def monitor(self, tmp_path):
        return PerformanceMonitor(db_path=str(tmp_path / "perf.db"))

    async def test_returns_list(self, monitor):
        result = await monitor._generate_optimization_recommendations()
        assert isinstance(result, list)

    async def test_no_data_returns_all_recommendations(self, monitor):
        # With no data, no performance target is being met → all 3 default recs
        result = await monitor._generate_optimization_recommendations()
        # video, db, api are all not meeting targets when empty
        assert len(result) >= 3

    async def test_each_recommendation_is_dict(self, monitor):
        result = await monitor._generate_optimization_recommendations()
        for rec in result:
            assert isinstance(rec, dict)

    async def test_recommendation_has_component_key(self, monitor):
        result = await monitor._generate_optimization_recommendations()
        for rec in result:
            assert "component" in rec

    async def test_recommendation_has_priority_key(self, monitor):
        result = await monitor._generate_optimization_recommendations()
        for rec in result:
            assert "priority" in rec

    async def test_recommendation_has_recommendation_key(self, monitor):
        result = await monitor._generate_optimization_recommendations()
        for rec in result:
            assert "recommendation" in rec

    async def test_recommendation_has_expected_improvement(self, monitor):
        result = await monitor._generate_optimization_recommendations()
        for rec in result:
            assert "expected_improvement" in rec

    async def test_video_recommendation_present_when_no_data(self, monitor):
        result = await monitor._generate_optimization_recommendations()
        components = [r["component"] for r in result]
        assert "video_processing" in components

    async def test_database_recommendation_present_when_no_data(self, monitor):
        result = await monitor._generate_optimization_recommendations()
        components = [r["component"] for r in result]
        assert "database" in components

    async def test_api_recommendation_present_when_no_data(self, monitor):
        result = await monitor._generate_optimization_recommendations()
        components = [r["component"] for r in result]
        assert "api" in components


# ===========================================================================
# PerformanceMonitor._get_system_health — pure structural test
# ===========================================================================


class TestGetSystemHealthStructure:
    @pytest.fixture
    def monitor(self, tmp_path):
        return PerformanceMonitor(db_path=str(tmp_path / "perf.db"))

    async def test_health_has_expected_keys(self, monitor):
        health = await monitor._get_system_health()
        assert "video_processing" in health
        assert "database_queries" in health
        assert "api_responses" in health

    async def test_empty_health_video_avg_zero(self, monitor):
        health = await monitor._get_system_health()
        assert health["video_processing"]["avg_time_ms"] == 0

    async def test_empty_health_db_avg_zero(self, monitor):
        health = await monitor._get_system_health()
        assert health["database_queries"]["avg_time_ms"] == 0

    async def test_health_target_values_present(self, monitor):
        health = await monitor._get_system_health()
        assert health["video_processing"]["target_ms"] == 30000
        assert health["database_queries"]["target_ms"] == 100
        assert health["api_responses"]["target_ms"] == 2000

    async def test_empty_meeting_target_is_false(self, monitor):
        health = await monitor._get_system_health()
        assert health["video_processing"]["meeting_target"] is False
        assert health["database_queries"]["meeting_target"] is False
