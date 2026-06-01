"""Additional tests for health_monitoring_service.py - targeting uncovered lines."""

from __future__ import annotations

import sys
from pathlib import Path

# Restore real psutil before import (test_index_analysis.py mocks it globally)
import psutil as _real_psutil
sys.modules['psutil'] = _real_psutil

_SRC = Path(__file__).resolve().parents[2] / "src"
sys.path.insert(0, str(_SRC))

import pytest

from youtube_extension.backend.services.health_monitoring_service import (
    ApplicationChecker,
    ComponentHealth,
    ComponentType,
    DatabaseChecker,
    ExternalServiceChecker,
    HealthChecker,
    HealthMetric,
    HealthMonitoringService,
    HealthStatus,
    SystemHealth,
    SystemResourceChecker,
)


# ===========================================================================
# ApplicationChecker
# ===========================================================================


class TestApplicationCheckerInit:
    def test_name(self):
        ac = ApplicationChecker()
        assert ac.name == "application"

    def test_component_type(self):
        ac = ApplicationChecker()
        assert ac.component_type == ComponentType.APPLICATION

    def test_request_count_initial(self):
        ac = ApplicationChecker()
        assert ac.request_count == 0

    def test_error_count_initial(self):
        ac = ApplicationChecker()
        assert ac.error_count == 0

    def test_error_count_window_empty(self):
        ac = ApplicationChecker()
        assert ac.error_count_window == []


class TestApplicationCheckerRecordRequest:
    def test_increments_request_count(self):
        ac = ApplicationChecker()
        ac.record_request()
        assert ac.request_count == 1

    def test_multiple_increments(self):
        ac = ApplicationChecker()
        for _ in range(5):
            ac.record_request()
        assert ac.request_count == 5


class TestApplicationCheckerRecordError:
    def test_increments_error_count(self):
        ac = ApplicationChecker()
        ac.record_error()
        assert ac.error_count == 1

    def test_appends_to_window(self):
        ac = ApplicationChecker()
        ac.record_error()
        assert len(ac.error_count_window) == 1

    def test_multiple_errors(self):
        ac = ApplicationChecker()
        ac.record_error()
        ac.record_error()
        assert ac.error_count == 2
        assert len(ac.error_count_window) == 2


class TestApplicationCheckerDetermineStatus:
    def test_healthy_error_rate(self):
        ac = ApplicationChecker()
        assert ac._determine_error_status(0.0) == HealthStatus.HEALTHY

    def test_warning_error_rate(self):
        ac = ApplicationChecker()
        assert ac._determine_error_status(10.0) == HealthStatus.WARNING

    def test_critical_error_rate(self):
        ac = ApplicationChecker()
        assert ac._determine_error_status(25.0) == HealthStatus.CRITICAL

    def test_healthy_memory(self):
        ac = ApplicationChecker()
        assert ac._determine_memory_status(100.0) == HealthStatus.HEALTHY

    def test_warning_memory(self):
        ac = ApplicationChecker()
        assert ac._determine_memory_status(600.0) == HealthStatus.WARNING

    def test_critical_memory(self):
        ac = ApplicationChecker()
        assert ac._determine_memory_status(1100.0) == HealthStatus.CRITICAL

    def test_healthy_response_time(self):
        ac = ApplicationChecker()
        assert ac._determine_response_time_status(100.0) == HealthStatus.HEALTHY

    def test_warning_response_time(self):
        ac = ApplicationChecker()
        assert ac._determine_response_time_status(1000.0) == HealthStatus.WARNING

    def test_critical_response_time(self):
        ac = ApplicationChecker()
        assert ac._determine_response_time_status(3000.0) == HealthStatus.CRITICAL


# ===========================================================================
# DatabaseChecker
# ===========================================================================


class TestDatabaseCheckerInit:
    def test_name(self):
        dc = DatabaseChecker("sqlite:///:memory:")
        assert dc.name == "database"

    def test_component_type(self):
        dc = DatabaseChecker("sqlite:///:memory:")
        assert dc.component_type == ComponentType.DATABASE

    def test_connection_string_stored(self):
        dc = DatabaseChecker("sqlite:///:memory:")
        assert dc.connection_string == "sqlite:///:memory:"

    def test_determine_latency_healthy(self):
        dc = DatabaseChecker("sqlite:///:memory:")
        assert dc._determine_latency_status(50.0) == HealthStatus.HEALTHY

    def test_determine_latency_warning(self):
        dc = DatabaseChecker("sqlite:///:memory:")
        assert dc._determine_latency_status(200.0) == HealthStatus.WARNING

    def test_determine_latency_critical(self):
        dc = DatabaseChecker("sqlite:///:memory:")
        assert dc._determine_latency_status(600.0) == HealthStatus.CRITICAL


# ===========================================================================
# ExternalServiceChecker
# ===========================================================================


class TestExternalServiceCheckerInit:
    def test_name_stored(self):
        esc = ExternalServiceChecker("my_svc", "http://example.com")
        assert esc.name == "my_svc"

    def test_url_stored(self):
        esc = ExternalServiceChecker("my_svc", "http://example.com")
        assert esc.url == "http://example.com"

    def test_default_timeout(self):
        esc = ExternalServiceChecker("my_svc", "http://example.com")
        assert esc.timeout == 10

    def test_custom_timeout(self):
        esc = ExternalServiceChecker("my_svc", "http://example.com", timeout=5)
        assert esc.timeout == 5

    def test_determine_http_healthy(self):
        esc = ExternalServiceChecker("svc", "http://example.com")
        assert esc._determine_http_status(200, 100.0) == HealthStatus.HEALTHY

    def test_determine_http_warning_slow(self):
        esc = ExternalServiceChecker("svc", "http://example.com")
        assert esc._determine_http_status(200, 2000.0) == HealthStatus.WARNING

    def test_determine_http_critical_status(self):
        esc = ExternalServiceChecker("svc", "http://example.com")
        assert esc._determine_http_status(500, 100.0) == HealthStatus.CRITICAL


# ===========================================================================
# SystemResourceChecker
# ===========================================================================


class TestSystemResourceCheckerInit:
    def test_name(self):
        src = SystemResourceChecker()
        assert src.name == "system_resources"

    def test_component_type(self):
        src = SystemResourceChecker()
        assert src.component_type == ComponentType.SYSTEM_RESOURCE

    def test_determine_status_healthy(self):
        src = SystemResourceChecker()
        assert src._determine_status(30.0, 70, 90) == HealthStatus.HEALTHY

    def test_determine_status_warning(self):
        src = SystemResourceChecker()
        assert src._determine_status(75.0, 70, 90) == HealthStatus.WARNING

    def test_determine_status_critical(self):
        src = SystemResourceChecker()
        assert src._determine_status(95.0, 70, 90) == HealthStatus.CRITICAL


def _make_fake_psutil():
    import types
    return types.SimpleNamespace(
        cpu_percent=lambda interval=None: 25.0,
        cpu_count=lambda: 4,
        virtual_memory=lambda: types.SimpleNamespace(
            percent=50.0, total=8 * 1024**3, available=4 * 1024**3, used=4 * 1024**3
        ),
        disk_usage=lambda path: types.SimpleNamespace(
            total=100 * 1024**3, used=50 * 1024**3, free=50 * 1024**3
        ),
        net_io_counters=lambda: types.SimpleNamespace(bytes_sent=0, bytes_recv=0),
    )


class TestSystemResourceCheckerCheckHealth:
    async def test_returns_component_health(self, monkeypatch):
        import youtube_extension.backend.services.health_monitoring_service as _mod
        monkeypatch.setattr(_mod, 'psutil', _make_fake_psutil())
        src = SystemResourceChecker()
        result = await src.check_health()
        assert isinstance(result, ComponentHealth)

    async def test_has_metrics(self, monkeypatch):
        import youtube_extension.backend.services.health_monitoring_service as _mod
        monkeypatch.setattr(_mod, 'psutil', _make_fake_psutil())
        src = SystemResourceChecker()
        result = await src.check_health()
        assert len(result.metrics) >= 1

    async def test_status_is_health_status(self, monkeypatch):
        import youtube_extension.backend.services.health_monitoring_service as _mod
        monkeypatch.setattr(_mod, 'psutil', _make_fake_psutil())
        src = SystemResourceChecker()
        result = await src.check_health()
        assert isinstance(result.status, HealthStatus)


# ===========================================================================
# HealthMonitoringService
# ===========================================================================


class TestHealthMonitoringServiceInit:
    def test_creates_instance(self):
        svc = HealthMonitoringService(config={"enable_system_resources": False, "enable_database": False, "enable_external_services": False, "enable_application": False})
        assert svc is not None

    def test_not_running_initially(self):
        svc = HealthMonitoringService(config={"enable_system_resources": False, "enable_database": False, "enable_external_services": False, "enable_application": False})
        assert svc.is_running is False

    def test_health_history_empty(self):
        svc = HealthMonitoringService(config={"enable_system_resources": False, "enable_database": False, "enable_external_services": False, "enable_application": False})
        assert svc.health_history == []

    def test_metrics_empty(self):
        svc = HealthMonitoringService(config={"enable_system_resources": False, "enable_database": False, "enable_external_services": False, "enable_application": False})
        assert svc._metrics == {}


_MINIMAL_CONFIG = {
    "enable_system_resources": False,
    "enable_database": False,
    "enable_external_services": False,
    "enable_application": False,
}


class TestHealthMonitoringServiceMethods:
    def test_check_external_connectors_returns_dict(self):
        svc = HealthMonitoringService(config=_MINIMAL_CONFIG)
        result = svc.check_external_connectors_health()
        assert isinstance(result, dict)

    def test_check_external_connectors_has_youtube(self):
        svc = HealthMonitoringService(config=_MINIMAL_CONFIG)
        result = svc.check_external_connectors_health()
        assert "youtube" in result

    def test_check_external_connectors_has_timestamp(self):
        svc = HealthMonitoringService(config=_MINIMAL_CONFIG)
        result = svc.check_external_connectors_health()
        assert "timestamp" in result

    def test_check_pipeline_health_returns_dict(self):
        svc = HealthMonitoringService(config=_MINIMAL_CONFIG)
        result = svc.check_video_to_software_pipeline_health()
        assert isinstance(result, dict)

    def test_check_pipeline_health_has_status(self):
        svc = HealthMonitoringService(config=_MINIMAL_CONFIG)
        result = svc.check_video_to_software_pipeline_health()
        assert "status" in result

    def test_check_pipeline_health_has_stages(self):
        svc = HealthMonitoringService(config=_MINIMAL_CONFIG)
        result = svc.check_video_to_software_pipeline_health()
        assert "stages" in result
        assert "ingestion" in result["stages"]

    def test_rate_limit_check_allows_first_request(self):
        svc = HealthMonitoringService(config=_MINIMAL_CONFIG)
        assert svc.rate_limit_check() is True

    def test_rate_limit_check_blocks_when_exceeded(self):
        import os
        svc = HealthMonitoringService(config=_MINIMAL_CONFIG)
        svc._rate_limit_rps = 2
        svc.rate_limit_check()
        svc.rate_limit_check()
        # Third request should be blocked
        assert svc.rate_limit_check() is False

    def test_increment_metric_new_key(self):
        svc = HealthMonitoringService(config=_MINIMAL_CONFIG)
        svc.increment_metric("requests")
        assert svc._metrics["requests"] == 1.0

    def test_increment_metric_accumulates(self):
        svc = HealthMonitoringService(config=_MINIMAL_CONFIG)
        svc.increment_metric("requests", 5.0)
        svc.increment_metric("requests", 3.0)
        assert svc._metrics["requests"] == 8.0

    def test_get_metrics_prometheus_returns_list(self):
        svc = HealthMonitoringService(config=_MINIMAL_CONFIG)
        result = svc.get_metrics_prometheus_format()
        assert isinstance(result, list)

    def test_get_metrics_prometheus_has_help_line(self):
        svc = HealthMonitoringService(config=_MINIMAL_CONFIG)
        result = svc.get_metrics_prometheus_format()
        assert any("HELP" in line for line in result)

    def test_get_metrics_prometheus_includes_metric(self):
        svc = HealthMonitoringService(config=_MINIMAL_CONFIG)
        svc.increment_metric("api.calls", 10.0)
        result = svc.get_metrics_prometheus_format()
        assert any("api_calls" in line for line in result)

    def test_get_basic_health_status_returns_dict(self):
        svc = HealthMonitoringService(config=_MINIMAL_CONFIG)
        result = svc.get_basic_health_status(None, None)
        assert isinstance(result, dict)
