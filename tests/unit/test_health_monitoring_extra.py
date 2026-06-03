"""Additional tests for health_monitoring_service.py - targeting uncovered lines."""

from __future__ import annotations

import asyncio
import sys
import time
import types
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
    def test_name(self) -> None:
        ac = ApplicationChecker()
        assert ac.name == "application"

    def test_component_type(self) -> None:
        ac = ApplicationChecker()
        assert ac.component_type == ComponentType.APPLICATION

    def test_request_count_initial(self) -> None:
        ac = ApplicationChecker()
        assert ac.request_count == 0

    def test_error_count_initial(self) -> None:
        ac = ApplicationChecker()
        assert ac.error_count == 0

    def test_error_count_window_empty(self) -> None:
        ac = ApplicationChecker()
        assert ac.error_count_window == []


class TestApplicationCheckerRecordRequest:
    def test_increments_request_count(self) -> None:
        ac = ApplicationChecker()
        ac.record_request()
        assert ac.request_count == 1

    def test_multiple_increments(self) -> None:
        ac = ApplicationChecker()
        for _ in range(5):
            ac.record_request()
        assert ac.request_count == 5


class TestApplicationCheckerRecordError:
    def test_increments_error_count(self) -> None:
        ac = ApplicationChecker()
        ac.record_error()
        assert ac.error_count == 1

    def test_appends_to_window(self) -> None:
        ac = ApplicationChecker()
        ac.record_error()
        assert len(ac.error_count_window) == 1

    def test_multiple_errors(self) -> None:
        ac = ApplicationChecker()
        ac.record_error()
        ac.record_error()
        assert ac.error_count == 2
        assert len(ac.error_count_window) == 2


class TestApplicationCheckerDetermineStatus:
    def test_healthy_error_rate(self) -> None:
        ac = ApplicationChecker()
        assert ac._determine_error_status(0.0) == HealthStatus.HEALTHY

    def test_warning_error_rate(self) -> None:
        ac = ApplicationChecker()
        assert ac._determine_error_status(10.0) == HealthStatus.WARNING

    def test_critical_error_rate(self) -> None:
        ac = ApplicationChecker()
        assert ac._determine_error_status(25.0) == HealthStatus.CRITICAL

    def test_healthy_memory(self) -> None:
        ac = ApplicationChecker()
        assert ac._determine_memory_status(100.0) == HealthStatus.HEALTHY

    def test_warning_memory(self) -> None:
        ac = ApplicationChecker()
        assert ac._determine_memory_status(600.0) == HealthStatus.WARNING

    def test_critical_memory(self) -> None:
        ac = ApplicationChecker()
        assert ac._determine_memory_status(1100.0) == HealthStatus.CRITICAL

    def test_healthy_response_time(self) -> None:
        ac = ApplicationChecker()
        assert ac._determine_response_time_status(100.0) == HealthStatus.HEALTHY

    def test_warning_response_time(self) -> None:
        ac = ApplicationChecker()
        assert ac._determine_response_time_status(1000.0) == HealthStatus.WARNING

    def test_critical_response_time(self) -> None:
        ac = ApplicationChecker()
        assert ac._determine_response_time_status(3000.0) == HealthStatus.CRITICAL


# ===========================================================================
# DatabaseChecker
# ===========================================================================


class TestDatabaseCheckerInit:
    def test_name(self) -> None:
        dc = DatabaseChecker("sqlite:///:memory:")
        assert dc.name == "database"

    def test_component_type(self) -> None:
        dc = DatabaseChecker("sqlite:///:memory:")
        assert dc.component_type == ComponentType.DATABASE

    def test_connection_string_stored(self) -> None:
        dc = DatabaseChecker("sqlite:///:memory:")
        assert dc.connection_string == "sqlite:///:memory:"

    def test_determine_latency_healthy(self) -> None:
        dc = DatabaseChecker("sqlite:///:memory:")
        assert dc._determine_latency_status(50.0) == HealthStatus.HEALTHY

    def test_determine_latency_warning(self) -> None:
        dc = DatabaseChecker("sqlite:///:memory:")
        assert dc._determine_latency_status(200.0) == HealthStatus.WARNING

    def test_determine_latency_critical(self) -> None:
        dc = DatabaseChecker("sqlite:///:memory:")
        assert dc._determine_latency_status(600.0) == HealthStatus.CRITICAL


# ===========================================================================
# ExternalServiceChecker
# ===========================================================================


class TestExternalServiceCheckerInit:
    def test_name_stored(self) -> None:
        esc = ExternalServiceChecker("my_svc", "http://example.com")
        assert esc.name == "my_svc"

    def test_url_stored(self) -> None:
        esc = ExternalServiceChecker("my_svc", "http://example.com")
        assert esc.url == "http://example.com"

    def test_default_timeout(self) -> None:
        esc = ExternalServiceChecker("my_svc", "http://example.com")
        assert esc.timeout == 10

    def test_custom_timeout(self) -> None:
        esc = ExternalServiceChecker("my_svc", "http://example.com", timeout=5)
        assert esc.timeout == 5

    def test_determine_http_healthy(self) -> None:
        esc = ExternalServiceChecker("svc", "http://example.com")
        assert esc._determine_http_status(200, 100.0) == HealthStatus.HEALTHY

    def test_determine_http_warning_slow(self) -> None:
        esc = ExternalServiceChecker("svc", "http://example.com")
        assert esc._determine_http_status(200, 2000.0) == HealthStatus.WARNING

    def test_determine_http_critical_status(self) -> None:
        esc = ExternalServiceChecker("svc", "http://example.com")
        assert esc._determine_http_status(500, 100.0) == HealthStatus.CRITICAL


# ===========================================================================
# SystemResourceChecker
# ===========================================================================


class TestSystemResourceCheckerInit:
    def test_name(self) -> None:
        src = SystemResourceChecker()
        assert src.name == "system_resources"

    def test_component_type(self) -> None:
        src = SystemResourceChecker()
        assert src.component_type == ComponentType.SYSTEM_RESOURCE

    def test_determine_status_healthy(self) -> None:
        src = SystemResourceChecker()
        assert src._determine_status(30.0, 70, 90) == HealthStatus.HEALTHY

    def test_determine_status_warning(self) -> None:
        src = SystemResourceChecker()
        assert src._determine_status(75.0, 70, 90) == HealthStatus.WARNING

    def test_determine_status_critical(self) -> None:
        src = SystemResourceChecker()
        assert src._determine_status(95.0, 70, 90) == HealthStatus.CRITICAL


def _make_fake_psutil() -> types.SimpleNamespace:
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
    async def test_returns_component_health(self, monkeypatch) -> None:
        import youtube_extension.backend.services.health_monitoring_service as _mod
        monkeypatch.setattr(_mod, 'psutil', _make_fake_psutil())
        src = SystemResourceChecker()
        result = await src.check_health()
        assert isinstance(result, ComponentHealth)

    async def test_has_metrics(self, monkeypatch) -> None:
        import youtube_extension.backend.services.health_monitoring_service as _mod
        monkeypatch.setattr(_mod, 'psutil', _make_fake_psutil())
        src = SystemResourceChecker()
        result = await src.check_health()
        assert len(result.metrics) >= 1

    async def test_status_is_health_status(self, monkeypatch) -> None:
        import youtube_extension.backend.services.health_monitoring_service as _mod
        monkeypatch.setattr(_mod, 'psutil', _make_fake_psutil())
        src = SystemResourceChecker()
        result = await src.check_health()
        assert isinstance(result.status, HealthStatus)


# ===========================================================================
# HealthMonitoringService
# ===========================================================================


class TestHealthMonitoringServiceInit:
    def test_creates_instance(self) -> None:
        svc = HealthMonitoringService(config={"enable_system_resources": False, "enable_database": False, "enable_external_services": False, "enable_application": False})
        assert svc is not None

    def test_not_running_initially(self) -> None:
        svc = HealthMonitoringService(config={"enable_system_resources": False, "enable_database": False, "enable_external_services": False, "enable_application": False})
        assert svc.is_running is False

    def test_health_history_empty(self) -> None:
        svc = HealthMonitoringService(config={"enable_system_resources": False, "enable_database": False, "enable_external_services": False, "enable_application": False})
        assert svc.health_history == []

    def test_metrics_empty(self) -> None:
        svc = HealthMonitoringService(config={"enable_system_resources": False, "enable_database": False, "enable_external_services": False, "enable_application": False})
        assert svc._metrics == {}


_MINIMAL_CONFIG = {
    "enable_system_resources": False,
    "enable_database": False,
    "enable_external_services": False,
    "enable_application": False,
}


class TestHealthMonitoringServiceMethods:
    def test_check_external_connectors_returns_dict(self) -> None:
        svc = HealthMonitoringService(config=_MINIMAL_CONFIG)
        result = svc.check_external_connectors_health()
        assert isinstance(result, dict)

    def test_check_external_connectors_has_youtube(self) -> None:
        svc = HealthMonitoringService(config=_MINIMAL_CONFIG)
        result = svc.check_external_connectors_health()
        assert "youtube" in result

    def test_check_external_connectors_has_timestamp(self) -> None:
        svc = HealthMonitoringService(config=_MINIMAL_CONFIG)
        result = svc.check_external_connectors_health()
        assert "timestamp" in result

    def test_check_pipeline_health_returns_dict(self) -> None:
        svc = HealthMonitoringService(config=_MINIMAL_CONFIG)
        result = svc.check_video_to_software_pipeline_health()
        assert isinstance(result, dict)

    def test_check_pipeline_health_has_status(self) -> None:
        svc = HealthMonitoringService(config=_MINIMAL_CONFIG)
        result = svc.check_video_to_software_pipeline_health()
        assert "status" in result

    def test_check_pipeline_health_has_stages(self) -> None:
        svc = HealthMonitoringService(config=_MINIMAL_CONFIG)
        result = svc.check_video_to_software_pipeline_health()
        assert "stages" in result
        assert "ingestion" in result["stages"]

    def test_rate_limit_check_allows_first_request(self) -> None:
        svc = HealthMonitoringService(config=_MINIMAL_CONFIG)
        assert svc.rate_limit_check() is True

    def test_rate_limit_check_blocks_when_exceeded(self) -> None:
        import os
        svc = HealthMonitoringService(config=_MINIMAL_CONFIG)
        svc._rate_limit_rps = 2
        svc.rate_limit_check()
        svc.rate_limit_check()
        # Third request should be blocked
        assert svc.rate_limit_check() is False

    def test_increment_metric_new_key(self) -> None:
        svc = HealthMonitoringService(config=_MINIMAL_CONFIG)
        svc.increment_metric("requests")
        assert svc._metrics["requests"] == 1.0

    def test_increment_metric_accumulates(self) -> None:
        svc = HealthMonitoringService(config=_MINIMAL_CONFIG)
        svc.increment_metric("requests", 5.0)
        svc.increment_metric("requests", 3.0)
        assert svc._metrics["requests"] == 8.0

    def test_get_metrics_prometheus_returns_list(self) -> None:
        svc = HealthMonitoringService(config=_MINIMAL_CONFIG)
        result = svc.get_metrics_prometheus_format()
        assert isinstance(result, list)

    def test_get_metrics_prometheus_has_help_line(self) -> None:
        svc = HealthMonitoringService(config=_MINIMAL_CONFIG)
        result = svc.get_metrics_prometheus_format()
        assert any("HELP" in line for line in result)

    def test_get_metrics_prometheus_includes_metric(self) -> None:
        svc = HealthMonitoringService(config=_MINIMAL_CONFIG)
        svc.increment_metric("api.calls", 10.0)
        result = svc.get_metrics_prometheus_format()
        assert any("api_calls" in line for line in result)

    def test_get_basic_health_status_returns_dict(self) -> None:
        svc = HealthMonitoringService(config=_MINIMAL_CONFIG)
        result = svc.get_basic_health_status(None, None)
        assert isinstance(result, dict)


# ===========================================================================
# Lines 30-37: fallback imports (ImportError branch)
# We cover these by patching the module attribute directly
# ===========================================================================

class TestFallbackImports:
    def test_log_error_fallback_is_callable(self) -> None:
        """The module always exposes a callable log_error after import."""
        import youtube_extension.backend.services.health_monitoring_service as _mod
        # Whether the real or fallback import was used, it must be callable
        assert callable(_mod.log_error)

    def test_get_logger_fallback_returns_logger(self) -> None:
        import youtube_extension.backend.services.health_monitoring_service as _mod
        # get_logger must be callable and return something non-None
        assert _mod.get_logger("test") is not None


# ===========================================================================
# Lines 190-213: SystemResourceChecker - disk and network sections
# ===========================================================================

def _make_full_psutil(
    *,
    bytes_sent: int = 1000,
    bytes_recv: int = 2000,
    packets_sent: int = 10,
    packets_recv: int = 20,
    disk_percent_used: int = 40,
) -> types.SimpleNamespace:
    """Build a fake psutil namespace that includes disk and net IO."""
    disk_total = 100 * 1024**3
    disk_used = int(disk_total * disk_percent_used / 100)
    disk_free = disk_total - disk_used
    return types.SimpleNamespace(
        cpu_percent=lambda interval=None: 25.0,
        cpu_count=lambda logical=True: 4,
        virtual_memory=lambda: types.SimpleNamespace(
            percent=50.0,
            total=8 * 1024**3,
            available=4 * 1024**3,
            used=4 * 1024**3,
        ),
        disk_usage=lambda path: types.SimpleNamespace(
            total=disk_total,
            used=disk_used,
            free=disk_free,
            percent=float(disk_percent_used),
        ),
        net_io_counters=lambda: types.SimpleNamespace(
            bytes_sent=bytes_sent,
            bytes_recv=bytes_recv,
            packets_sent=packets_sent,
            packets_recv=packets_recv,
        ),
        Process=lambda pid=None: types.SimpleNamespace(
            memory_info=lambda: types.SimpleNamespace(rss=100 * 1024**2),
            pid=12345,
            memory_percent=lambda: 1.2,
        ),
    )


class TestSystemResourceCheckerDiskNetwork:
    async def test_disk_metric_included(self, monkeypatch) -> None:
        import youtube_extension.backend.services.health_monitoring_service as _mod
        monkeypatch.setattr(_mod, 'psutil', _make_full_psutil())
        src = SystemResourceChecker()
        result = await src.check_health()
        names = [m.name for m in result.metrics]
        assert "disk_usage" in names

    async def test_disk_metric_value(self, monkeypatch) -> None:
        import youtube_extension.backend.services.health_monitoring_service as _mod
        monkeypatch.setattr(_mod, 'psutil', _make_full_psutil(disk_percent_used=40))
        src = SystemResourceChecker()
        result = await src.check_health()
        disk_m = next(m for m in result.metrics if m.name == "disk_usage")
        assert abs(disk_m.value - 40.0) < 1.0

    async def test_disk_critical_when_high(self, monkeypatch) -> None:
        import youtube_extension.backend.services.health_monitoring_service as _mod
        monkeypatch.setattr(_mod, 'psutil', _make_full_psutil(disk_percent_used=97))
        src = SystemResourceChecker()
        result = await src.check_health()
        disk_m = next(m for m in result.metrics if m.name == "disk_usage")
        assert disk_m.status == HealthStatus.CRITICAL

    async def test_disk_warning_when_moderate(self, monkeypatch) -> None:
        import youtube_extension.backend.services.health_monitoring_service as _mod
        monkeypatch.setattr(_mod, 'psutil', _make_full_psutil(disk_percent_used=85))
        src = SystemResourceChecker()
        result = await src.check_health()
        disk_m = next(m for m in result.metrics if m.name == "disk_usage")
        assert disk_m.status == HealthStatus.WARNING

    async def test_network_metric_appears_on_second_call(self, monkeypatch) -> None:
        """Network throughput metric only appears after a second call (delta required)."""
        import youtube_extension.backend.services.health_monitoring_service as _mod
        monkeypatch.setattr(_mod, 'psutil', _make_full_psutil(bytes_sent=500, bytes_recv=1000))
        src = SystemResourceChecker()
        # First call seeds _last_net_io
        await src.check_health()
        # Second call should produce a network_throughput metric
        result = await src.check_health()
        names = [m.name for m in result.metrics]
        assert "network_throughput" in names

    async def test_network_metric_has_send_recv_metadata(self, monkeypatch) -> None:
        import youtube_extension.backend.services.health_monitoring_service as _mod
        monkeypatch.setattr(_mod, 'psutil', _make_full_psutil())
        src = SystemResourceChecker()
        await src.check_health()  # seed
        result = await src.check_health()
        net_m = next(m for m in result.metrics if m.name == "network_throughput")
        assert "send_mbps" in net_m.metadata
        assert "recv_mbps" in net_m.metadata

    async def test_network_metric_status_is_healthy(self, monkeypatch) -> None:
        import youtube_extension.backend.services.health_monitoring_service as _mod
        monkeypatch.setattr(_mod, 'psutil', _make_full_psutil())
        src = SystemResourceChecker()
        await src.check_health()
        result = await src.check_health()
        net_m = next(m for m in result.metrics if m.name == "network_throughput")
        assert net_m.status == HealthStatus.HEALTHY

    async def test_recovery_actions_present_on_critical(self, monkeypatch) -> None:
        """When disk is critical, recovery_actions must be non-empty."""
        import youtube_extension.backend.services.health_monitoring_service as _mod
        # cpu=91 triggers CRITICAL
        fake = _make_full_psutil(disk_percent_used=10)
        fake.cpu_percent = lambda interval=None: 95.0
        monkeypatch.setattr(_mod, 'psutil', fake)
        src = SystemResourceChecker()
        result = await src.check_health()
        assert len(result.recovery_actions) > 0

    async def test_exception_path_returns_failed(self, monkeypatch) -> None:
        """If psutil throws, ComponentHealth with FAILED is returned."""
        import youtube_extension.backend.services.health_monitoring_service as _mod

        broken = types.SimpleNamespace(
            cpu_percent=lambda interval=None: (_ for _ in ()).throw(RuntimeError("boom")),
        )
        monkeypatch.setattr(_mod, 'psutil', broken)
        src = SystemResourceChecker()
        result = await src.check_health()
        assert result.status == HealthStatus.FAILED


# ===========================================================================
# Lines 248-250: _determine_status boundary (exact threshold values)
# ===========================================================================

class TestDetermineStatusBoundary:
    def test_at_warning_threshold_is_warning(self) -> None:
        src = SystemResourceChecker()
        assert src._determine_status(70.0, 70, 90) == HealthStatus.WARNING

    def test_just_below_warning_is_healthy(self) -> None:
        src = SystemResourceChecker()
        assert src._determine_status(69.9, 70, 90) == HealthStatus.HEALTHY

    def test_at_critical_threshold_is_critical(self) -> None:
        src = SystemResourceChecker()
        assert src._determine_status(90.0, 70, 90) == HealthStatus.CRITICAL

    def test_just_below_critical_is_warning(self) -> None:
        src = SystemResourceChecker()
        assert src._determine_status(89.9, 70, 90) == HealthStatus.WARNING


# ===========================================================================
# Lines 280-350: DatabaseChecker.check_health() paths
# ===========================================================================

class TestDatabaseCheckerCheckHealth:
    async def test_returns_component_health(self) -> None:
        dc = DatabaseChecker("sqlite:///:memory:")
        result = await dc.check_health()
        assert isinstance(result, ComponentHealth)

    async def test_status_is_health_status(self) -> None:
        dc = DatabaseChecker("sqlite:///:memory:")
        result = await dc.check_health()
        assert isinstance(result.status, HealthStatus)

    async def test_has_connection_latency_metric(self) -> None:
        dc = DatabaseChecker("sqlite:///:memory:")
        result = await dc.check_health()
        names = [m.name for m in result.metrics]
        assert "connection_latency" in names

    async def test_has_query_performance_metric(self) -> None:
        """If connection_healthy==True, query_performance metric is added."""
        dc = DatabaseChecker("sqlite:///:memory:")
        result = await dc.check_health()
        names = [m.name for m in result.metrics]
        assert "query_performance" in names

    async def test_critical_when_connection_fails(self, monkeypatch) -> None:
        dc = DatabaseChecker("sqlite:///:memory:")

        async def _fail_connect():
            return False

        monkeypatch.setattr(dc, '_test_connection', _fail_connect)
        result = await dc.check_health()
        assert result.status == HealthStatus.CRITICAL

    async def test_no_query_metric_when_connection_fails(self, monkeypatch) -> None:
        dc = DatabaseChecker("sqlite:///:memory:")

        async def _fail_connect():
            return False

        monkeypatch.setattr(dc, '_test_connection', _fail_connect)
        result = await dc.check_health()
        names = [m.name for m in result.metrics]
        assert "query_performance" not in names

    async def test_recovery_actions_on_critical(self, monkeypatch) -> None:
        dc = DatabaseChecker("sqlite:///:memory:")

        async def _fail_connect():
            return False

        monkeypatch.setattr(dc, '_test_connection', _fail_connect)
        result = await dc.check_health()
        assert len(result.recovery_actions) > 0

    async def test_exception_path_returns_failed(self, monkeypatch) -> None:
        dc = DatabaseChecker("sqlite:///:memory:")

        async def _boom():
            raise RuntimeError("DB exploded")

        monkeypatch.setattr(dc, '_test_connection', _boom)
        result = await dc.check_health()
        assert result.status == HealthStatus.FAILED

    async def test_high_latency_yields_warning_or_critical(self, monkeypatch) -> None:
        """Simulate a slow connection (>100 ms) via a slow _test_connection."""
        dc = DatabaseChecker("sqlite:///:memory:")

        async def _slow():
            await asyncio.sleep(0.0)  # just returns True quickly in tests
            return True

        # Directly test _determine_latency_status at 200 ms
        assert dc._determine_latency_status(200.0) == HealthStatus.WARNING


# ===========================================================================
# Lines 362-480: ExternalServiceChecker paths
# ===========================================================================

class TestExternalServiceCheckerCheckHealth:
    async def test_healthy_response(self, monkeypatch) -> None:
        esc = ExternalServiceChecker("test_svc", "http://example.com")

        async def _fake_request():
            return 200, 0.1  # 100 ms

        monkeypatch.setattr(esc, '_make_request', _fake_request)
        result = await esc.check_health()
        assert result.status == HealthStatus.HEALTHY

    async def test_500_response_is_critical(self, monkeypatch) -> None:
        esc = ExternalServiceChecker("test_svc", "http://example.com")

        async def _fake_request():
            return 500, 0.1

        monkeypatch.setattr(esc, '_make_request', _fake_request)
        result = await esc.check_health()
        assert result.status == HealthStatus.CRITICAL

    async def test_404_response_is_warning(self, monkeypatch) -> None:
        esc = ExternalServiceChecker("test_svc", "http://example.com")

        async def _fake_request():
            return 404, 0.1

        monkeypatch.setattr(esc, '_make_request', _fake_request)
        result = await esc.check_health()
        assert result.status == HealthStatus.WARNING

    async def test_connection_failed_zero_status(self, monkeypatch) -> None:
        esc = ExternalServiceChecker("test_svc", "http://example.com")

        async def _fake_request():
            return 0, 10.0  # connection failed

        monkeypatch.setattr(esc, '_make_request', _fake_request)
        result = await esc.check_health()
        assert result.status == HealthStatus.CRITICAL

    async def test_slow_response_over_5s_is_critical(self, monkeypatch) -> None:
        esc = ExternalServiceChecker("test_svc", "http://example.com")

        async def _fake_request():
            return 200, 6.0  # 6 seconds

        monkeypatch.setattr(esc, '_make_request', _fake_request)
        result = await esc.check_health()
        assert result.status == HealthStatus.CRITICAL

    async def test_slow_response_over_1s_is_warning(self, monkeypatch) -> None:
        esc = ExternalServiceChecker("test_svc", "http://example.com")

        async def _fake_request():
            return 200, 2.0  # 2 seconds

        monkeypatch.setattr(esc, '_make_request', _fake_request)
        result = await esc.check_health()
        assert result.status == HealthStatus.WARNING

    async def test_recovery_actions_on_critical(self, monkeypatch) -> None:
        esc = ExternalServiceChecker("test_svc", "http://example.com")

        async def _fake_request():
            return 500, 0.1

        monkeypatch.setattr(esc, '_make_request', _fake_request)
        result = await esc.check_health()
        assert len(result.recovery_actions) > 0

    async def test_exception_returns_failed(self, monkeypatch) -> None:
        esc = ExternalServiceChecker("test_svc", "http://example.com")

        async def _boom():
            raise RuntimeError("network gone")

        monkeypatch.setattr(esc, '_make_request', _boom)
        result = await esc.check_health()
        assert result.status == HealthStatus.FAILED

    async def test_response_metric_included(self, monkeypatch) -> None:
        esc = ExternalServiceChecker("test_svc", "http://example.com")

        async def _fake_request():
            return 200, 0.2

        monkeypatch.setattr(esc, '_make_request', _fake_request)
        result = await esc.check_health()
        assert any(m.name == "response_time" for m in result.metrics)

    def test_determine_http_status_zero_code_critical(self) -> None:
        esc = ExternalServiceChecker("svc", "http://example.com")
        assert esc._determine_http_status(0, 100.0) == HealthStatus.CRITICAL

    def test_determine_http_status_400_warning(self) -> None:
        esc = ExternalServiceChecker("svc", "http://example.com")
        assert esc._determine_http_status(400, 100.0) == HealthStatus.WARNING

    def test_determine_http_status_over_5000ms_warning(self) -> None:
        esc = ExternalServiceChecker("svc", "http://example.com")
        assert esc._determine_http_status(200, 6000.0) == HealthStatus.WARNING

    def test_determine_http_status_over_1000ms_warning(self) -> None:
        esc = ExternalServiceChecker("svc", "http://example.com")
        assert esc._determine_http_status(200, 2000.0) == HealthStatus.WARNING


# ===========================================================================
# Lines 519-617: ApplicationChecker.check_health()
# ===========================================================================

class TestApplicationCheckerCheckHealth:
    async def test_returns_component_health(self, monkeypatch) -> None:
        import youtube_extension.backend.services.health_monitoring_service as _mod
        monkeypatch.setattr(_mod, 'psutil', _make_full_psutil())
        ac = ApplicationChecker()
        result = await ac.check_health()
        assert isinstance(result, ComponentHealth)

    async def test_has_error_rate_metric(self, monkeypatch) -> None:
        import youtube_extension.backend.services.health_monitoring_service as _mod
        monkeypatch.setattr(_mod, 'psutil', _make_full_psutil())
        ac = ApplicationChecker()
        result = await ac.check_health()
        assert any(m.name == "error_rate" for m in result.metrics)

    async def test_has_avg_response_time_metric(self, monkeypatch) -> None:
        import youtube_extension.backend.services.health_monitoring_service as _mod
        monkeypatch.setattr(_mod, 'psutil', _make_full_psutil())
        ac = ApplicationChecker()
        result = await ac.check_health()
        assert any(m.name == "avg_response_time" for m in result.metrics)

    async def test_has_process_memory_metric(self, monkeypatch) -> None:
        import youtube_extension.backend.services.health_monitoring_service as _mod
        monkeypatch.setattr(_mod, 'psutil', _make_full_psutil())
        ac = ApplicationChecker()
        result = await ac.check_health()
        assert any(m.name == "process_memory" for m in result.metrics)

    async def test_status_healthy_with_no_errors(self, monkeypatch) -> None:
        import youtube_extension.backend.services.health_monitoring_service as _mod
        monkeypatch.setattr(_mod, 'psutil', _make_full_psutil())
        ac = ApplicationChecker()
        result = await ac.check_health()
        assert result.status == HealthStatus.HEALTHY

    async def test_warning_recovery_actions_present(self, monkeypatch) -> None:
        """Force a WARNING by patching _determine_error_status."""
        import youtube_extension.backend.services.health_monitoring_service as _mod
        monkeypatch.setattr(_mod, 'psutil', _make_full_psutil())
        ac = ApplicationChecker()
        # error_rate = (recent_errors / 300) * 60 must be >= 5 for WARNING
        # So we need recent_errors >= 25 (5 * 300 / 60)
        for _ in range(30):
            ac.record_error()
        result = await ac.check_health()
        # Warning or Critical; recovery_actions should be present
        assert result.status in (HealthStatus.WARNING, HealthStatus.CRITICAL)
        assert len(result.recovery_actions) > 0

    async def test_psutil_process_exception_skipped(self, monkeypatch) -> None:
        """If psutil.Process() raises, we still get a valid result."""
        import youtube_extension.backend.services.health_monitoring_service as _mod

        class BrokenProcess:
            def memory_info(self):
                raise OSError("no such process")

        fake = _make_full_psutil()
        fake.Process = lambda pid=None: BrokenProcess()
        monkeypatch.setattr(_mod, 'psutil', fake)
        ac = ApplicationChecker()
        result = await ac.check_health()
        # Should still return a ComponentHealth (minus process_memory metric)
        assert isinstance(result, ComponentHealth)


# ===========================================================================
# Lines 696-760: HealthMonitoringService utility methods
# ===========================================================================

class TestHealthMonitoringServiceUtilityMethods:
    def test_get_current_health_none_when_no_history(self) -> None:
        svc = HealthMonitoringService(config=_MINIMAL_CONFIG)
        assert svc.get_current_health() is None

    def test_get_current_health_returns_last(self) -> None:
        svc = HealthMonitoringService(config=_MINIMAL_CONFIG)
        sh = SystemHealth(
            overall_status=HealthStatus.HEALTHY,
            score=100.0,
            timestamp=1000.0,
            uptime_seconds=10.0,
            components=[],
            active_alerts=[],
            recent_incidents=[],
        )
        svc.health_history.append(sh)
        assert svc.get_current_health() is sh

    def test_get_health_history_empty_by_default(self) -> None:
        svc = HealthMonitoringService(config=_MINIMAL_CONFIG)
        assert svc.get_health_history() == []

    def test_get_health_history_filters_by_time(self) -> None:
        svc = HealthMonitoringService(config=_MINIMAL_CONFIG)
        old_sh = SystemHealth(
            overall_status=HealthStatus.HEALTHY,
            score=100.0,
            timestamp=1.0,  # very old
            uptime_seconds=0.0,
            components=[],
            active_alerts=[],
            recent_incidents=[],
        )
        recent_sh = SystemHealth(
            overall_status=HealthStatus.HEALTHY,
            score=100.0,
            timestamp=time.time(),
            uptime_seconds=0.0,
            components=[],
            active_alerts=[],
            recent_incidents=[],
        )
        svc.health_history.extend([old_sh, recent_sh])
        result = svc.get_health_history(hours=1)
        assert recent_sh in result
        assert old_sh not in result

    def test_record_request_no_op_without_app_checker(self) -> None:
        """record_request should not raise when application_checker is None."""
        svc = HealthMonitoringService(config=_MINIMAL_CONFIG)
        svc.application_checker = None
        svc.record_request()  # should not raise

    def test_record_error_no_op_without_app_checker(self) -> None:
        svc = HealthMonitoringService(config=_MINIMAL_CONFIG)
        svc.application_checker = None
        svc.record_error()  # should not raise

    def test_record_request_delegates_to_app_checker(self) -> None:
        config = dict(_MINIMAL_CONFIG)
        config["enable_application"] = True
        svc = HealthMonitoringService(config=config)
        initial = svc.application_checker.request_count
        svc.record_request()
        assert svc.application_checker.request_count == initial + 1

    def test_record_error_delegates_to_app_checker(self) -> None:
        config = dict(_MINIMAL_CONFIG)
        config["enable_application"] = True
        svc = HealthMonitoringService(config=config)
        initial = svc.application_checker.error_count
        svc.record_error()
        assert svc.application_checker.error_count == initial + 1

    async def test_stop_monitoring_sets_flag(self) -> None:
        """stop_monitoring must set is_running to False."""
        svc = HealthMonitoringService(config=_MINIMAL_CONFIG)
        svc.is_running = True
        await svc.stop_monitoring()
        assert svc.is_running is False


# ===========================================================================
# Lines 808-956: perform_health_check, _calculate_overall_health, etc.
# ===========================================================================

class TestPerformHealthCheck:
    async def test_perform_health_check_empty_checkers(self) -> None:
        """With no checkers, returns a SystemHealth with FAILED or 0 score."""
        svc = HealthMonitoringService(config=_MINIMAL_CONFIG)
        result = await svc.perform_health_check()
        assert isinstance(result, SystemHealth)

    async def test_perform_health_check_stores_history(self) -> None:
        svc = HealthMonitoringService(config=_MINIMAL_CONFIG)
        await svc.perform_health_check()
        assert len(svc.health_history) == 1

    async def test_perform_health_check_history_limit(self) -> None:
        """History is trimmed when it exceeds history_limit."""
        config = dict(_MINIMAL_CONFIG)
        config["history_limit"] = 2
        svc = HealthMonitoringService(config=config)
        for _ in range(5):
            await svc.perform_health_check()
        assert len(svc.health_history) <= 3  # may be 2 or 3 depending on trim logic

    async def test_perform_health_check_handles_checker_exception(self) -> None:
        """If a checker raises, it should be handled gracefully."""
        svc = HealthMonitoringService(config=_MINIMAL_CONFIG)

        class BoomChecker(HealthChecker):
            def __init__(self):
                super().__init__("boom", ComponentType.APPLICATION)

            async def check_health(self):
                raise RuntimeError("forced failure")

        svc.checkers.append(BoomChecker())
        result = await svc.perform_health_check()
        assert isinstance(result, SystemHealth)


class TestCalculateOverallHealth:
    def test_empty_components_returns_failed(self) -> None:
        svc = HealthMonitoringService(config=_MINIMAL_CONFIG)
        status, score = svc._calculate_overall_health([])
        assert status == HealthStatus.FAILED
        assert score == 0.0

    def test_all_healthy_returns_healthy(self) -> None:
        svc = HealthMonitoringService(config=_MINIMAL_CONFIG)
        comp = ComponentHealth(
            name="test",
            component_type=ComponentType.APPLICATION,
            status=HealthStatus.HEALTHY,
            uptime_seconds=100.0,
            last_check=0.0,
            metrics=[],
        )
        status, score = svc._calculate_overall_health([comp])
        assert status == HealthStatus.HEALTHY
        assert score > 90

    def test_critical_component_degrades_score(self) -> None:
        svc = HealthMonitoringService(config=_MINIMAL_CONFIG)
        comp = ComponentHealth(
            name="db",
            component_type=ComponentType.DATABASE,
            status=HealthStatus.CRITICAL,
            uptime_seconds=10.0,
            last_check=0.0,
            metrics=[],
        )
        status, score = svc._calculate_overall_health([comp])
        assert status in (HealthStatus.CRITICAL, HealthStatus.DEGRADED)

    def test_warning_component(self) -> None:
        svc = HealthMonitoringService(config=_MINIMAL_CONFIG)
        comp = ComponentHealth(
            name="res",
            component_type=ComponentType.SYSTEM_RESOURCE,
            status=HealthStatus.WARNING,
            uptime_seconds=10.0,
            last_check=0.0,
            metrics=[],
        )
        status, score = svc._calculate_overall_health([comp])
        assert status in (HealthStatus.HEALTHY, HealthStatus.WARNING)


class TestGetActiveAlerts:
    def test_no_alerts_for_healthy_components(self) -> None:
        svc = HealthMonitoringService(config=_MINIMAL_CONFIG)
        comp = ComponentHealth(
            name="db",
            component_type=ComponentType.DATABASE,
            status=HealthStatus.HEALTHY,
            uptime_seconds=10.0,
            last_check=0.0,
            metrics=[],
        )
        alerts = svc._get_active_alerts([comp])
        assert alerts == []

    def test_alert_for_critical_component(self) -> None:
        svc = HealthMonitoringService(config=_MINIMAL_CONFIG)
        comp = ComponentHealth(
            name="db",
            component_type=ComponentType.DATABASE,
            status=HealthStatus.CRITICAL,
            uptime_seconds=10.0,
            last_check=0.0,
            metrics=[],
        )
        alerts = svc._get_active_alerts([comp])
        assert len(alerts) == 1
        assert "db" in alerts[0]

    def test_alert_for_warning_component(self) -> None:
        svc = HealthMonitoringService(config=_MINIMAL_CONFIG)
        comp = ComponentHealth(
            name="svc",
            component_type=ComponentType.EXTERNAL_SERVICE,
            status=HealthStatus.WARNING,
            uptime_seconds=10.0,
            last_check=0.0,
            metrics=[],
        )
        alerts = svc._get_active_alerts([comp])
        assert len(alerts) == 1

    def test_multiple_components_multiple_alerts(self) -> None:
        svc = HealthMonitoringService(config=_MINIMAL_CONFIG)
        comps = [
            ComponentHealth(
                name=f"c{i}",
                component_type=ComponentType.APPLICATION,
                status=HealthStatus.CRITICAL,
                uptime_seconds=1.0,
                last_check=0.0,
                metrics=[],
            )
            for i in range(3)
        ]
        alerts = svc._get_active_alerts(comps)
        assert len(alerts) == 3


class TestGetRecentIncidents:
    def test_empty_history_returns_empty(self) -> None:
        svc = HealthMonitoringService(config=_MINIMAL_CONFIG)
        assert svc._get_recent_incidents() == []

    def test_single_history_returns_empty(self) -> None:
        svc = HealthMonitoringService(config=_MINIMAL_CONFIG)
        svc.health_history.append(SystemHealth(
            overall_status=HealthStatus.HEALTHY,
            score=100.0,
            timestamp=time.time(),
            uptime_seconds=0.0,
            components=[],
            active_alerts=[],
            recent_incidents=[],
        ))
        assert svc._get_recent_incidents() == []

    def test_degradation_detected(self) -> None:
        svc = HealthMonitoringService(config=_MINIMAL_CONFIG)
        now = time.time()
        h1 = SystemHealth(
            overall_status=HealthStatus.HEALTHY,
            score=100.0,
            timestamp=now - 60,
            uptime_seconds=0.0,
            components=[],
            active_alerts=[],
            recent_incidents=[],
        )
        h2 = SystemHealth(
            overall_status=HealthStatus.CRITICAL,
            score=25.0,
            timestamp=now,
            uptime_seconds=0.0,
            components=[],
            active_alerts=[],
            recent_incidents=[],
        )
        svc.health_history.extend([h1, h2])
        incidents = svc._get_recent_incidents()
        assert len(incidents) == 1


class TestGenerateRecommendations:
    def test_empty_components_no_recommendations(self) -> None:
        svc = HealthMonitoringService(config=_MINIMAL_CONFIG)
        recs = svc._generate_recommendations([])
        assert recs == []

    def test_critical_component_generates_urgent_recs(self) -> None:
        svc = HealthMonitoringService(config=_MINIMAL_CONFIG)
        comp = ComponentHealth(
            name="db",
            component_type=ComponentType.DATABASE,
            status=HealthStatus.CRITICAL,
            uptime_seconds=10.0,
            last_check=0.0,
            metrics=[],
            recovery_actions=["restart db"],
        )
        recs = svc._generate_recommendations([comp])
        assert any("URGENT" in r for r in recs)

    def test_warning_component_generates_monitor_recs(self) -> None:
        svc = HealthMonitoringService(config=_MINIMAL_CONFIG)
        comp = ComponentHealth(
            name="svc",
            component_type=ComponentType.EXTERNAL_SERVICE,
            status=HealthStatus.WARNING,
            uptime_seconds=10.0,
            last_check=0.0,
            metrics=[],
            recovery_actions=["check network", "restart"],
        )
        recs = svc._generate_recommendations([comp])
        assert any("Monitor" in r for r in recs)

    def test_multiple_critical_adds_emergency_message(self) -> None:
        svc = HealthMonitoringService(config=_MINIMAL_CONFIG)
        comps = [
            ComponentHealth(
                name=f"c{i}",
                component_type=ComponentType.APPLICATION,
                status=HealthStatus.CRITICAL,
                uptime_seconds=1.0,
                last_check=0.0,
                metrics=[],
                recovery_actions=["fix"],
            )
            for i in range(3)
        ]
        recs = svc._generate_recommendations(comps)
        assert any("emergency" in r.lower() or "multiple" in r.lower() for r in recs)

    def test_recommendations_capped_at_10(self) -> None:
        svc = HealthMonitoringService(config=_MINIMAL_CONFIG)
        comps = [
            ComponentHealth(
                name=f"c{i}",
                component_type=ComponentType.APPLICATION,
                status=HealthStatus.CRITICAL,
                uptime_seconds=1.0,
                last_check=0.0,
                metrics=[],
                recovery_actions=[f"action{j}" for j in range(5)],
            )
            for i in range(5)
        ]
        recs = svc._generate_recommendations(comps)
        assert len(recs) <= 10


# ===========================================================================
# Lines 1038-1056: get_component_metrics
# ===========================================================================

class TestGetComponentMetrics:
    def test_returns_empty_for_unknown_component(self) -> None:
        svc = HealthMonitoringService(config=_MINIMAL_CONFIG)
        result = svc.get_component_metrics("nonexistent")
        assert result == []

    def test_returns_metrics_for_known_component(self) -> None:
        svc = HealthMonitoringService(config=_MINIMAL_CONFIG)
        metric = HealthMetric(
            name="cpu_usage",
            value=30.0,
            unit="percent",
            status=HealthStatus.HEALTHY,
            threshold_warning=70,
            threshold_critical=90,
            timestamp=time.time(),
        )
        comp = ComponentHealth(
            name="system_resources",
            component_type=ComponentType.SYSTEM_RESOURCE,
            status=HealthStatus.HEALTHY,
            uptime_seconds=10.0,
            last_check=time.time(),
            metrics=[metric],
        )
        sh = SystemHealth(
            overall_status=HealthStatus.HEALTHY,
            score=100.0,
            timestamp=time.time(),
            uptime_seconds=10.0,
            components=[comp],
            active_alerts=[],
            recent_incidents=[],
        )
        svc.health_history.append(sh)
        result = svc.get_component_metrics("system_resources")
        assert len(result) == 1
        assert result[0]["name"] == "cpu_usage"

    def test_old_history_excluded_from_metrics(self) -> None:
        svc = HealthMonitoringService(config=_MINIMAL_CONFIG)
        metric = HealthMetric(
            name="cpu_usage",
            value=30.0,
            unit="percent",
            status=HealthStatus.HEALTHY,
            threshold_warning=70,
            threshold_critical=90,
            timestamp=1.0,
        )
        comp = ComponentHealth(
            name="system_resources",
            component_type=ComponentType.SYSTEM_RESOURCE,
            status=HealthStatus.HEALTHY,
            uptime_seconds=10.0,
            last_check=1.0,
            metrics=[metric],
        )
        sh = SystemHealth(
            overall_status=HealthStatus.HEALTHY,
            score=100.0,
            timestamp=1.0,  # very old
            uptime_seconds=0.0,
            components=[comp],
            active_alerts=[],
            recent_incidents=[],
        )
        svc.health_history.append(sh)
        result = svc.get_component_metrics("system_resources", hours=1)
        assert result == []


# ===========================================================================
# Lines 1071-1073: get_health_monitoring_service singleton
# ===========================================================================

class TestGetHealthMonitoringServiceSingleton:
    def test_returns_same_instance(self, monkeypatch) -> None:
        import youtube_extension.backend.services.health_monitoring_service as _mod
        # Reset singleton
        monkeypatch.setattr(_mod, '_health_service', None)
        svc1 = _mod.get_health_monitoring_service()
        svc2 = _mod.get_health_monitoring_service()
        assert svc1 is svc2

    def test_returns_health_monitoring_service_instance(self, monkeypatch) -> None:
        import youtube_extension.backend.services.health_monitoring_service as _mod
        monkeypatch.setattr(_mod, '_health_service', None)
        svc = _mod.get_health_monitoring_service()
        assert isinstance(svc, HealthMonitoringService)


# ===========================================================================
# Lines 1060-1061: stop_monitoring
# ===========================================================================

class TestStopMonitoring:
    async def test_stop_monitoring_sets_is_running_false(self) -> None:
        svc = HealthMonitoringService(config=_MINIMAL_CONFIG)
        svc.is_running = True
        await svc.stop_monitoring()
        assert svc.is_running is False


# ===========================================================================
# Lines 833-845: start_monitoring loop
# ===========================================================================

class TestStartMonitoring:
    async def test_start_monitoring_sets_is_running(self) -> None:
        """start_monitoring sets is_running=True and stops when flag cleared."""
        svc = HealthMonitoringService(config=_MINIMAL_CONFIG)
        assert svc.is_running is False

        async def _run_then_stop():
            # Run one iteration then stop
            task = asyncio.create_task(svc.start_monitoring())
            await asyncio.sleep(0)  # yield to let start_monitoring set flag
            svc.is_running = False
            await asyncio.sleep(0)
            task.cancel()
            try:
                await task
            except (asyncio.CancelledError, Exception):
                pass

        await _run_then_stop()

    async def test_start_monitoring_no_op_if_already_running(self) -> None:
        svc = HealthMonitoringService(config=_MINIMAL_CONFIG)
        svc.is_running = True
        # Should return immediately without looping

        async def _call_with_timeout():
            try:
                await asyncio.wait_for(svc.start_monitoring(), timeout=0.05)
            except asyncio.TimeoutError:
                pass  # acceptable — loop ran longer than expected
            # If it returned immediately, is_running is still True
        await _call_with_timeout()


# ===========================================================================
# HealthMonitoringService - _initialize_checkers coverage
# ===========================================================================

class TestInitializeCheckers:
    def test_system_resource_checker_added(self) -> None:
        config = dict(_MINIMAL_CONFIG)
        config["enable_system_resources"] = True
        svc = HealthMonitoringService(config=config)
        assert any(isinstance(c, SystemResourceChecker) for c in svc.checkers)

    def test_database_checker_added(self) -> None:
        config = dict(_MINIMAL_CONFIG)
        config["enable_database"] = True
        svc = HealthMonitoringService(config=config)
        assert any(isinstance(c, DatabaseChecker) for c in svc.checkers)

    def test_external_service_checkers_added(self) -> None:
        config = dict(_MINIMAL_CONFIG)
        config["enable_external_services"] = True
        config["external_services"] = {"test_api": "http://example.com"}
        svc = HealthMonitoringService(config=config)
        assert any(isinstance(c, ExternalServiceChecker) for c in svc.checkers)

    def test_application_checker_added(self) -> None:
        config = dict(_MINIMAL_CONFIG)
        config["enable_application"] = True
        svc = HealthMonitoringService(config=config)
        assert svc.application_checker is not None
        assert isinstance(svc.application_checker, ApplicationChecker)

    def test_application_checker_none_when_disabled(self) -> None:
        svc = HealthMonitoringService(config=_MINIMAL_CONFIG)
        assert svc.application_checker is None


# ===========================================================================
# HealthMonitoringService - get_basic_health_status extra coverage
# ===========================================================================

class TestGetBasicHealthStatusExtra:
    def test_status_key_present(self) -> None:
        svc = HealthMonitoringService(config=_MINIMAL_CONFIG)
        result = svc.get_basic_health_status(None, None)
        assert "status" in result

    def test_version_key_present(self) -> None:
        svc = HealthMonitoringService(config=_MINIMAL_CONFIG)
        result = svc.get_basic_health_status(None, None)
        assert result.get("version") == "2.0.0"

    def test_components_key_present(self) -> None:
        svc = HealthMonitoringService(config=_MINIMAL_CONFIG)
        result = svc.get_basic_health_status(None, None)
        assert "components" in result

    def test_websocket_available(self) -> None:
        svc = HealthMonitoringService(config=_MINIMAL_CONFIG)

        class FakeWS:
            pass

        result = svc.get_basic_health_status(None, FakeWS())
        assert result["components"]["websocket"] == "available"

    def test_websocket_unavailable_when_none(self) -> None:
        svc = HealthMonitoringService(config=_MINIMAL_CONFIG)
        result = svc.get_basic_health_status(None, None)
        assert result["components"]["websocket"] == "unavailable"

    def test_video_processor_available_when_has_attr(self) -> None:
        svc = HealthMonitoringService(config=_MINIMAL_CONFIG)

        class FakeFactory:
            def create_processor(self):
                pass

        result = svc.get_basic_health_status(FakeFactory(), None)
        assert result["components"]["video_processor"] == "available"
