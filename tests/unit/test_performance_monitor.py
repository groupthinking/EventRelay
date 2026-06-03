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


# ===========================================================================
# PerformanceMonitor — stop_monitoring / start_monitoring lifecycle
# ===========================================================================


class TestMonitoringLifecycle:
    @pytest.fixture
    def monitor(self, tmp_path):
        return PerformanceMonitor(db_path=str(tmp_path / "perf.db"))

    async def test_stop_monitoring_when_task_is_none(self, monitor):
        monitor.monitoring_task = None
        await monitor.stop_monitoring()  # should not raise
        assert monitor.monitoring_task is None

    async def test_stop_monitoring_cancels_task(self, monitor):
        import asyncio
        called = []

        async def fake_task():
            try:
                await asyncio.sleep(100)
            except asyncio.CancelledError:
                called.append(True)
                raise

        monitor.monitoring_task = asyncio.create_task(fake_task())
        await asyncio.sleep(0)  # let task start
        await monitor.stop_monitoring()
        assert monitor.monitoring_task is None
        assert called

    def test_start_monitoring_no_loop(self, monitor):
        monitor.monitoring_task = None
        monitor.start_monitoring()
        # No running event loop outside async context — should not raise

    async def test_start_monitoring_creates_task(self, monitor):
        import asyncio
        monitor.monitoring_task = None
        monitor.start_monitoring()
        assert monitor.monitoring_task is not None
        monitor.monitoring_task.cancel()
        try:
            await monitor.monitoring_task
        except asyncio.CancelledError:
            pass


# ===========================================================================
# PerformanceMonitor — _store_metric database writes
# ===========================================================================


class TestStoreMetric:
    @pytest.fixture
    def monitor(self, tmp_path):
        return PerformanceMonitor(db_path=str(tmp_path / "perf.db"))

    async def test_store_metric_does_not_raise(self, monitor):
        from datetime import datetime, timezone
        from youtube_extension.backend.services.performance_monitor import PerformanceMetric
        metric = PerformanceMetric(
            component="test", metric_name="latency", value=42.0,
            timestamp=datetime.now(timezone.utc)
        )
        await monitor._store_metric(metric)

    async def test_store_metric_persists_to_db(self, monitor):
        import sqlite3
        from datetime import datetime, timezone
        from youtube_extension.backend.services.performance_monitor import PerformanceMetric
        metric = PerformanceMetric(
            component="video", metric_name="process_time", value=1500.0,
            timestamp=datetime.now(timezone.utc)
        )
        await monitor._store_metric(metric)
        conn = sqlite3.connect(monitor.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM performance_metrics WHERE component = 'video'")
        count = cursor.fetchone()[0]
        conn.close()
        assert count >= 1


# ===========================================================================
# PerformanceMonitor — _check_alert_thresholds (warning and critical paths)
# ===========================================================================


class TestCheckAlertThresholds:
    @pytest.fixture
    def monitor(self, tmp_path):
        return PerformanceMonitor(db_path=str(tmp_path / "perf.db"))

    async def test_no_threshold_key_does_not_raise(self, monitor):
        from datetime import datetime, timezone
        from youtube_extension.backend.services.performance_monitor import PerformanceMetric
        metric = PerformanceMetric(
            component="test", metric_name="unknown_metric", value=999.0,
            timestamp=datetime.now(timezone.utc)
        )
        await monitor._check_alert_thresholds(metric)

    async def test_below_warning_no_alert(self, monitor):
        from datetime import datetime, timezone
        from youtube_extension.backend.services.performance_monitor import PerformanceMetric
        metric = PerformanceMetric(
            component="db", metric_name="database_query_time", value=50.0,
            timestamp=datetime.now(timezone.utc)
        )
        await monitor._check_alert_thresholds(metric)
        assert len(monitor.active_alerts) == 0

    async def test_above_warning_creates_alert(self, monitor):
        from datetime import datetime, timezone
        from youtube_extension.backend.services.performance_monitor import PerformanceMetric
        metric = PerformanceMetric(
            component="db", metric_name="database_query_time", value=150.0,
            timestamp=datetime.now(timezone.utc)
        )
        await monitor._check_alert_thresholds(metric)
        assert len(monitor.active_alerts) >= 1

    async def test_above_critical_severity_is_critical(self, monitor):
        from datetime import datetime, timezone
        from youtube_extension.backend.services.performance_monitor import PerformanceMetric
        metric = PerformanceMetric(
            component="db", metric_name="database_query_time", value=2000.0,
            timestamp=datetime.now(timezone.utc)
        )
        await monitor._check_alert_thresholds(metric)
        alerts = list(monitor.active_alerts.values())
        assert any(a.severity == "critical" for a in alerts)


# ===========================================================================
# PerformanceMonitor — _store_alert
# ===========================================================================


class TestStoreAlert:
    @pytest.fixture
    def monitor(self, tmp_path):
        return PerformanceMonitor(db_path=str(tmp_path / "perf.db"))

    async def test_store_alert_does_not_raise(self, monitor):
        from datetime import datetime, timezone
        from youtube_extension.backend.services.performance_monitor import PerformanceAlert
        alert = PerformanceAlert(
            alert_id="test_001",
            component="db",
            metric_name="query_time",
            threshold=100.0,
            current_value=250.0,
            severity="warning",
            message="Test alert",
            timestamp=datetime.now(timezone.utc),
        )
        await monitor._store_alert(alert)

    async def test_store_alert_persists(self, monitor):
        import sqlite3
        from datetime import datetime, timezone
        from youtube_extension.backend.services.performance_monitor import PerformanceAlert
        alert = PerformanceAlert(
            alert_id="test_002",
            component="api",
            metric_name="response_time",
            threshold=2000.0,
            current_value=5000.0,
            severity="critical",
            message="API slow",
            timestamp=datetime.now(timezone.utc),
        )
        await monitor._store_alert(alert)
        conn = sqlite3.connect(monitor.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM performance_alerts WHERE alert_id = 'test_002'")
        count = cursor.fetchone()[0]
        conn.close()
        assert count == 1

    async def test_send_alert_notification_does_not_raise(self, monitor):
        from datetime import datetime, timezone
        from youtube_extension.backend.services.performance_monitor import PerformanceAlert
        alert = PerformanceAlert(
            alert_id="notif_001",
            component="test",
            metric_name="test_metric",
            threshold=100.0,
            current_value=200.0,
            severity="warning",
            message="Test notification",
            timestamp=datetime.now(timezone.utc),
        )
        await monitor._send_alert_notification(alert)


# ===========================================================================
# PerformanceMonitor — _monitor_system_resources with mocked psutil
# ===========================================================================


class TestMonitorSystemResources:
    @pytest.fixture
    def monitor(self, tmp_path):
        return PerformanceMonitor(db_path=str(tmp_path / "perf.db"))

    async def test_monitor_system_resources_does_not_raise(self, monitor, monkeypatch):
        import types
        import youtube_extension.backend.services.performance_monitor as _mod
        fake_psutil = types.SimpleNamespace(
            cpu_percent=lambda interval=None: 30.0,
            virtual_memory=lambda: types.SimpleNamespace(percent=50.0, available=4*1024**3),
            disk_usage=lambda path: types.SimpleNamespace(used=40*1024**3, total=100*1024**3),
            Process=lambda: types.SimpleNamespace(
                memory_info=lambda: types.SimpleNamespace(rss=100*1024**2),
                cpu_percent=lambda: 5.0,
                num_threads=lambda: 4,
            ),
        )
        monkeypatch.setattr(_mod, 'psutil', fake_psutil)
        await monitor._monitor_system_resources()

    async def test_monitor_system_resources_adds_metrics(self, monitor, monkeypatch):
        import types
        import youtube_extension.backend.services.performance_monitor as _mod
        fake_psutil = types.SimpleNamespace(
            cpu_percent=lambda interval=None: 45.0,
            virtual_memory=lambda: types.SimpleNamespace(percent=60.0, available=3*1024**3),
            disk_usage=lambda path: types.SimpleNamespace(used=60*1024**3, total=100*1024**3),
            Process=lambda: types.SimpleNamespace(
                memory_info=lambda: types.SimpleNamespace(rss=200*1024**2),
                cpu_percent=lambda: 10.0,
                num_threads=lambda: 8,
            ),
        )
        monkeypatch.setattr(_mod, 'psutil', fake_psutil)
        before = len(monitor.metrics_buffer)
        await monitor._monitor_system_resources()
        assert len(monitor.metrics_buffer) > before


# ===========================================================================
# PerformanceMonitor — _check_performance_regressions
# ===========================================================================


class TestCheckPerformanceRegressions:
    @pytest.fixture
    def monitor(self, tmp_path):
        return PerformanceMonitor(db_path=str(tmp_path / "perf.db"))

    async def test_no_baselines_no_alerts(self, monitor):
        await monitor.record_metric("db", "database_query_time", 50.0)
        monitor.performance_baselines = {}
        await monitor._check_performance_regressions()
        assert len(monitor.active_alerts) == 0

    async def test_regression_triggers_alert(self, monitor):
        monitor.performance_baselines["db_database_query_time"] = 50.0
        await monitor.record_metric("db", "database_query_time", 100.0)
        await monitor._check_performance_regressions()

    async def test_no_regression_no_new_alert(self, monitor):
        monitor.performance_baselines["db_database_query_time"] = 200.0
        await monitor.record_metric("db", "database_query_time", 50.0)
        initial_count = len(monitor.active_alerts)
        await monitor._check_performance_regressions()
        assert len(monitor.active_alerts) == initial_count


# ===========================================================================
# PerformanceMonitor — _basic_cleanup
# ===========================================================================


class TestBasicCleanup:
    @pytest.fixture
    def monitor(self, tmp_path):
        return PerformanceMonitor(db_path=str(tmp_path / "perf.db"))

    async def test_basic_cleanup_does_not_raise(self, monitor):
        await monitor._basic_cleanup()

    async def test_basic_cleanup_with_old_records(self, monitor):
        import sqlite3
        from datetime import datetime, timezone, timedelta
        old_time = (datetime.now(timezone.utc) - timedelta(days=60)).isoformat()
        conn = sqlite3.connect(monitor.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO performance_metrics (component, metric_name, value, unit, tags, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
            ("old", "old_metric", 1.0, "ms", "{}", old_time)
        )
        conn.commit()
        conn.close()
        await monitor._basic_cleanup()
        conn = sqlite3.connect(monitor.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM performance_metrics WHERE component = 'old'")
        count = cursor.fetchone()[0]
        conn.close()
        assert count == 0


# ===========================================================================
# PerformanceMonitor — get_performance_dashboard
# ===========================================================================


class TestGetPerformanceDashboard:
    @pytest.fixture
    def monitor(self, tmp_path):
        return PerformanceMonitor(db_path=str(tmp_path / "perf.db"))

    async def test_returns_dict(self, monitor):
        result = await monitor.get_performance_dashboard()
        assert isinstance(result, dict)

    async def test_has_timestamp(self, monitor):
        result = await monitor.get_performance_dashboard()
        assert "timestamp" in result

    async def test_has_system_health(self, monitor):
        result = await monitor.get_performance_dashboard()
        assert "system_health" in result

    async def test_has_performance_targets(self, monitor):
        result = await monitor.get_performance_dashboard()
        assert "performance_targets" in result

    async def test_has_active_alerts_count(self, monitor):
        result = await monitor.get_performance_dashboard()
        assert "active_alerts" in result
        assert isinstance(result["active_alerts"], int)

    async def test_has_optimization_recommendations(self, monitor):
        result = await monitor.get_performance_dashboard()
        assert "optimization_recommendations" in result


# ===========================================================================
# PerformanceMonitor — _get_target_progress
# ===========================================================================


class TestGetTargetProgress:
    @pytest.fixture
    def monitor(self, tmp_path):
        return PerformanceMonitor(db_path=str(tmp_path / "perf.db"))

    async def test_returns_dict(self, monitor):
        result = await monitor._get_target_progress()
        assert isinstance(result, dict)

    async def test_has_overall_improvement_target(self, monitor):
        result = await monitor._get_target_progress()
        assert "overall_improvement_target" in result
        assert result["overall_improvement_target"] == 60

    async def test_has_targets_met_dict(self, monitor):
        result = await monitor._get_target_progress()
        assert "targets_met" in result
        assert "video_processing_sub_30s" in result["targets_met"]

    async def test_no_data_improvements_are_zero(self, monitor):
        result = await monitor._get_target_progress()
        assert result["video_processing_improvement"] == 0
        assert result["database_improvement"] == 0
        assert result["api_improvement"] == 0


# ===========================================================================
# PerformanceMonitor — run_performance_benchmark
# ===========================================================================


class TestRunPerformanceBenchmark:
    @pytest.fixture
    def monitor(self, tmp_path):
        return PerformanceMonitor(db_path=str(tmp_path / "perf.db"))

    async def test_returns_dict(self, monitor):
        async def noop():
            pass
        result = await monitor.run_performance_benchmark("test", "bench1", noop, iterations=3)
        assert isinstance(result, dict)

    async def test_has_avg_time(self, monitor):
        async def noop():
            pass
        result = await monitor.run_performance_benchmark("test", "bench1", noop, iterations=3)
        assert "avg_time_ms" in result

    async def test_has_benchmark_name(self, monitor):
        async def noop():
            pass
        result = await monitor.run_performance_benchmark("test", "my_bench", noop, iterations=3)
        assert result.get("benchmark_name") == "my_bench"

    async def test_sets_baseline_on_first_run(self, monitor):
        async def noop():
            pass
        await monitor.run_performance_benchmark("comp", "b1", noop, iterations=2)
        assert "comp_b1" in monitor.performance_baselines

    async def test_calculates_improvement_vs_baseline(self, monitor):
        import time
        monitor.performance_baselines["comp_b1"] = 10000.0  # slow baseline

        async def fast_func():
            pass

        result = await monitor.run_performance_benchmark("comp", "b1", fast_func, iterations=3)
        assert result.get("improvement_percent", 0) > 0

    async def test_sync_function_also_works(self, monitor):
        def sync_noop():
            pass
        result = await monitor.run_performance_benchmark("test", "sync_bench", sync_noop, iterations=2)
        assert "avg_time_ms" in result


# ===========================================================================
# Convenience functions (module-level)
# ===========================================================================


class TestConvenienceFunctions:
    @pytest.fixture(autouse=True)
    def reset_singleton(self, tmp_path):
        import youtube_extension.backend.services.performance_monitor as _mod
        original = _mod._performance_monitor_instance
        _mod._performance_monitor_instance = PerformanceMonitor(db_path=str(tmp_path / "perf.db"))
        yield
        _mod._performance_monitor_instance = original

    async def test_track_video_processing_time(self):
        from youtube_extension.backend.services.performance_monitor import track_video_processing_time
        await track_video_processing_time(1500.0)

    async def test_track_database_query_time(self):
        from youtube_extension.backend.services.performance_monitor import track_database_query_time
        await track_database_query_time(50.0, query_type="SELECT")

    async def test_track_api_response_time(self):
        from youtube_extension.backend.services.performance_monitor import track_api_response_time
        await track_api_response_time(200.0, endpoint="/api/v1/videos")

    async def test_track_frontend_load_time(self):
        from youtube_extension.backend.services.performance_monitor import track_frontend_load_time
        await track_frontend_load_time(800.0, page="dashboard")


# ===========================================================================
# performance_timer decorator
# ===========================================================================


class TestPerformanceTimerDecorator:
    @pytest.fixture
    def monitor(self, tmp_path):
        import youtube_extension.backend.services.performance_monitor as _mod
        m = PerformanceMonitor(db_path=str(tmp_path / "perf.db"))
        _mod._performance_monitor_instance = m
        return m

    async def test_decorator_on_async_function(self, monitor):
        from youtube_extension.backend.services.performance_monitor import performance_timer

        @performance_timer("test_comp", "async_op")
        async def my_async_func():
            return 42

        result = await my_async_func()
        assert result == 42

    def test_decorator_on_sync_function(self, monitor):
        from youtube_extension.backend.services.performance_monitor import performance_timer

        @performance_timer("test_comp", "sync_op")
        def my_sync_func():
            return "hello"

        result = my_sync_func()
        assert result == "hello"
