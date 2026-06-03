"""Unit tests for health monitoring dataclasses and pure threshold methods."""

from __future__ import annotations

import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from youtube_extension.backend.services.health_monitoring_service import (
    ApplicationChecker,
    ComponentHealth,
    ComponentType,
    DatabaseChecker,
    ExternalServiceChecker,
    HealthMetric,
    HealthMonitoringService,
    HealthStatus,
    SystemHealth,
    SystemResourceChecker,
)


# ===========================================================================
# HealthStatus enum
# ===========================================================================


class TestHealthStatus:
    def test_all_values(self):
        values = {s.value for s in HealthStatus}
        assert values == {"healthy", "warning", "degraded", "critical", "failed"}

    def test_str_equality(self):
        assert HealthStatus.HEALTHY.value == "healthy"
        assert HealthStatus.CRITICAL.value == "critical"


# ===========================================================================
# ComponentType enum
# ===========================================================================


class TestComponentType:
    def test_all_values(self):
        values = {c.value for c in ComponentType}
        assert values == {
            "api_server", "database", "external_service",
            "system_resource", "application",
        }


# ===========================================================================
# HealthMetric dataclass
# ===========================================================================


class TestHealthMetric:
    def _make(self, **kw) -> HealthMetric:
        defaults = dict(
            name="cpu", value=50.0, unit="percent",
            status=HealthStatus.HEALTHY,
            threshold_warning=70.0, threshold_critical=90.0,
            timestamp=time.time(),
        )
        return HealthMetric(**{**defaults, **kw})

    def test_metadata_defaults_to_empty_dict(self):
        m = self._make()
        assert m.metadata == {}

    def test_metadata_none_replaced_with_dict(self):
        m = self._make(metadata=None)
        assert m.metadata == {}

    def test_custom_metadata_preserved(self):
        m = self._make(metadata={"cores": 4})
        assert m.metadata["cores"] == 4

    def test_fields_stored(self):
        m = self._make(value=75.0, unit="percent")
        assert m.value == 75.0
        assert m.unit == "percent"


# ===========================================================================
# ComponentHealth dataclass
# ===========================================================================


class TestComponentHealth:
    def _make(self, **kw) -> ComponentHealth:
        defaults = dict(
            name="api", component_type=ComponentType.API_SERVER,
            status=HealthStatus.HEALTHY,
            uptime_seconds=100.0, last_check=time.time(), metrics=[],
        )
        return ComponentHealth(**{**defaults, **kw})

    def test_dependencies_defaults_empty(self):
        assert self._make().dependencies == []

    def test_recovery_actions_defaults_empty(self):
        assert self._make().recovery_actions == []

    def test_none_dependencies_replaced(self):
        c = self._make(dependencies=None)
        assert c.dependencies == []

    def test_none_recovery_actions_replaced(self):
        c = self._make(recovery_actions=None)
        assert c.recovery_actions == []

    def test_custom_dependencies_preserved(self):
        c = self._make(dependencies=["postgres"])
        assert c.dependencies == ["postgres"]


# ===========================================================================
# SystemHealth dataclass
# ===========================================================================


class TestSystemHealth:
    def _make(self, **kw) -> SystemHealth:
        defaults = dict(
            overall_status=HealthStatus.HEALTHY, score=95.0,
            timestamp=time.time(), uptime_seconds=1000.0,
            components=[], active_alerts=[], recent_incidents=[],
        )
        return SystemHealth(**{**defaults, **kw})

    def test_recommendations_defaults_empty(self):
        assert self._make().recommendations == []

    def test_none_recommendations_replaced(self):
        s = self._make(recommendations=None)
        assert s.recommendations == []

    def test_custom_recommendations_preserved(self):
        s = self._make(recommendations=["Add more memory"])
        assert s.recommendations == ["Add more memory"]


# ===========================================================================
# SystemResourceChecker._determine_status — pure threshold logic
# ===========================================================================


class TestDetermineStatus:
    @pytest.fixture
    def checker(self):
        return SystemResourceChecker()

    def test_below_warning_is_healthy(self, checker):
        assert checker._determine_status(50.0, 70.0, 90.0) == HealthStatus.HEALTHY

    def test_at_warning_threshold_is_warning(self, checker):
        assert checker._determine_status(70.0, 70.0, 90.0) == HealthStatus.WARNING

    def test_between_thresholds_is_warning(self, checker):
        assert checker._determine_status(80.0, 70.0, 90.0) == HealthStatus.WARNING

    def test_at_critical_threshold_is_critical(self, checker):
        assert checker._determine_status(90.0, 70.0, 90.0) == HealthStatus.CRITICAL

    def test_above_critical_is_critical(self, checker):
        assert checker._determine_status(99.9, 70.0, 90.0) == HealthStatus.CRITICAL

    def test_zero_value_is_healthy(self, checker):
        assert checker._determine_status(0.0, 70.0, 90.0) == HealthStatus.HEALTHY


# ===========================================================================
# DatabaseChecker._determine_latency_status
# ===========================================================================


class TestDetermineLatencyStatus:
    @pytest.fixture
    def checker(self):
        return DatabaseChecker("sqlite:///test.db")

    def test_low_latency_healthy(self, checker):
        assert checker._determine_latency_status(50.0) == HealthStatus.HEALTHY

    def test_at_warning_threshold(self, checker):
        assert checker._determine_latency_status(100.0) == HealthStatus.WARNING

    def test_between_thresholds_warning(self, checker):
        assert checker._determine_latency_status(300.0) == HealthStatus.WARNING

    def test_at_critical_threshold(self, checker):
        assert checker._determine_latency_status(500.0) == HealthStatus.CRITICAL

    def test_above_critical(self, checker):
        assert checker._determine_latency_status(1000.0) == HealthStatus.CRITICAL


# ===========================================================================
# ExternalServiceChecker._determine_http_status
# ===========================================================================


class TestDetermineHttpStatus:
    @pytest.fixture
    def checker(self):
        return ExternalServiceChecker("test", "http://example.com")

    def test_200_fast_is_healthy(self, checker):
        assert checker._determine_http_status(200, 100.0) == HealthStatus.HEALTHY

    def test_connection_failure_is_critical(self, checker):
        assert checker._determine_http_status(0, 0.0) == HealthStatus.CRITICAL

    def test_500_is_critical(self, checker):
        assert checker._determine_http_status(500, 100.0) == HealthStatus.CRITICAL

    def test_503_is_critical(self, checker):
        assert checker._determine_http_status(503, 100.0) == HealthStatus.CRITICAL

    def test_404_is_warning(self, checker):
        assert checker._determine_http_status(404, 100.0) == HealthStatus.WARNING

    def test_slow_response_is_warning(self, checker):
        assert checker._determine_http_status(200, 2000.0) == HealthStatus.WARNING

    def test_very_slow_response_is_warning(self, checker):
        assert checker._determine_http_status(200, 5001.0) == HealthStatus.WARNING


# ===========================================================================
# ApplicationChecker threshold methods
# ===========================================================================


class TestApplicationCheckerThresholds:
    @pytest.fixture
    def checker(self):
        return ApplicationChecker()

    def test_low_error_rate_healthy(self, checker):
        assert checker._determine_error_status(1.0) == HealthStatus.HEALTHY

    def test_error_rate_at_warning(self, checker):
        assert checker._determine_error_status(5.0) == HealthStatus.WARNING

    def test_error_rate_at_critical(self, checker):
        assert checker._determine_error_status(20.0) == HealthStatus.CRITICAL

    def test_high_error_rate_critical(self, checker):
        assert checker._determine_error_status(50.0) == HealthStatus.CRITICAL

    def test_low_memory_healthy(self, checker):
        assert checker._determine_memory_status(200.0) == HealthStatus.HEALTHY

    def test_memory_at_warning(self, checker):
        assert checker._determine_memory_status(500.0) == HealthStatus.WARNING

    def test_memory_at_critical(self, checker):
        assert checker._determine_memory_status(1000.0) == HealthStatus.CRITICAL

    def test_fast_response_healthy(self, checker):
        assert checker._determine_response_time_status(100.0) == HealthStatus.HEALTHY

    def test_response_at_warning(self, checker):
        assert checker._determine_response_time_status(500.0) == HealthStatus.WARNING

    def test_response_at_critical(self, checker):
        assert checker._determine_response_time_status(2000.0) == HealthStatus.CRITICAL


def _make_component(name="svc", component_type=ComponentType.APPLICATION,
                    status=HealthStatus.HEALTHY, recovery_actions=None) -> ComponentHealth:
    return ComponentHealth(
        name=name, component_type=component_type, status=status,
        uptime_seconds=100.0, last_check=time.time(), metrics=[],
        recovery_actions=recovery_actions or [],
    )


def _minimal_svc() -> HealthMonitoringService:
    return HealthMonitoringService({
        "enable_system_resources": False, "enable_database": False,
        "enable_external_services": False, "enable_application": False,
    })


# ===========================================================================
# ApplicationChecker counters
# ===========================================================================


class TestApplicationCheckerCounters:
    def test_record_request_increments(self):
        checker = ApplicationChecker()
        checker.record_request()
        assert checker.request_count == 1

    def test_record_multiple_requests(self):
        checker = ApplicationChecker()
        for _ in range(3):
            checker.record_request()
        assert checker.request_count == 3

    def test_record_error_increments_count(self):
        checker = ApplicationChecker()
        checker.record_error()
        assert checker.error_count == 1

    def test_record_error_adds_to_window(self):
        checker = ApplicationChecker()
        checker.record_error()
        assert len(checker.error_count_window) == 1


# ===========================================================================
# HealthMonitoringService._load_config
# ===========================================================================


class TestHealthMonitoringServiceLoadConfig:
    def test_default_check_interval(self):
        assert _minimal_svc().config["check_interval"] == 30

    def test_default_history_limit(self):
        assert _minimal_svc().config["history_limit"] == 1000

    def test_custom_config_overrides_default(self):
        svc = HealthMonitoringService({"check_interval": 60,
            "enable_system_resources": False, "enable_database": False,
            "enable_external_services": False, "enable_application": False})
        assert svc.config["check_interval"] == 60

    def test_custom_preserves_other_defaults(self):
        svc = HealthMonitoringService({"check_interval": 60,
            "enable_system_resources": False, "enable_database": False,
            "enable_external_services": False, "enable_application": False})
        assert svc.config["history_limit"] == 1000


# ===========================================================================
# HealthMonitoringService.rate_limit_check
# ===========================================================================


class TestRateLimitCheck:
    def test_first_request_allowed(self):
        assert _minimal_svc().rate_limit_check() is True

    def test_over_limit_denied(self, monkeypatch):
        monkeypatch.setenv("RATE_LIMIT_RPS", "2")
        svc = _minimal_svc()
        svc.rate_limit_check()
        svc.rate_limit_check()
        assert svc.rate_limit_check() is False


# ===========================================================================
# HealthMonitoringService.increment_metric / get_metrics_prometheus_format
# ===========================================================================


class TestIncrementMetric:
    def test_stores_value(self):
        svc = _minimal_svc()
        svc.increment_metric("requests", 1.0)
        assert svc._metrics["requests"] == 1.0

    def test_accumulates(self):
        svc = _minimal_svc()
        svc.increment_metric("requests", 1.0)
        svc.increment_metric("requests", 2.0)
        assert svc._metrics["requests"] == 3.0

    def test_default_amount_is_one(self):
        svc = _minimal_svc()
        svc.increment_metric("hits")
        assert svc._metrics["hits"] == 1.0


class TestGetMetricsPrometheusFormat:
    def test_returns_list(self):
        assert isinstance(_minimal_svc().get_metrics_prometheus_format(), list)

    def test_includes_header(self):
        lines = _minimal_svc().get_metrics_prometheus_format()
        assert any("HELP" in line for line in lines)

    def test_includes_metric_line(self):
        svc = _minimal_svc()
        svc.increment_metric("requests", 5.0)
        lines = svc.get_metrics_prometheus_format()
        assert any("requests" in line for line in lines)


# ===========================================================================
# HealthMonitoringService._calculate_overall_health
# ===========================================================================


class TestCalculateOverallHealth:
    def test_empty_components_fails(self):
        status, score = _minimal_svc()._calculate_overall_health([])
        assert status == HealthStatus.FAILED
        assert score == 0.0

    def test_healthy_component_gives_positive_score(self):
        comps = [_make_component(status=HealthStatus.HEALTHY,
                                  component_type=ComponentType.SYSTEM_RESOURCE)]
        _, score = _minimal_svc()._calculate_overall_health(comps)
        assert score > 0

    def test_critical_component_reduces_score(self):
        comps = [_make_component(status=HealthStatus.CRITICAL,
                                  component_type=ComponentType.DATABASE)]
        _, score = _minimal_svc()._calculate_overall_health(comps)
        assert score < 50


# ===========================================================================
# HealthMonitoringService._get_active_alerts
# ===========================================================================


class TestGetActiveAlerts:
    def test_no_alerts_when_all_healthy(self):
        comps = [_make_component(status=HealthStatus.HEALTHY)]
        assert _minimal_svc()._get_active_alerts(comps) == []

    def test_alert_for_warning(self):
        comps = [_make_component(name="db", status=HealthStatus.WARNING)]
        alerts = _minimal_svc()._get_active_alerts(comps)
        assert len(alerts) == 1 and "db" in alerts[0]

    def test_alert_for_critical(self):
        comps = [_make_component(name="api", status=HealthStatus.CRITICAL)]
        assert len(_minimal_svc()._get_active_alerts(comps)) == 1

    def test_alert_for_failed(self):
        comps = [_make_component(name="app", status=HealthStatus.FAILED)]
        assert len(_minimal_svc()._get_active_alerts(comps)) == 1


# ===========================================================================
# HealthMonitoringService._generate_recommendations
# ===========================================================================


class TestGenerateRecommendations:
    def test_no_recs_when_healthy(self):
        comps = [_make_component(status=HealthStatus.HEALTHY)]
        assert _minimal_svc()._generate_recommendations(comps) == []

    def test_urgent_for_critical(self):
        comps = [_make_component(status=HealthStatus.CRITICAL,
                                  recovery_actions=["restart service"])]
        recs = _minimal_svc()._generate_recommendations(comps)
        assert any("URGENT" in r for r in recs)

    def test_limited_to_ten(self):
        comps = [_make_component(status=HealthStatus.CRITICAL,
                                  recovery_actions=[f"action {i}" for i in range(20)])]
        assert len(_minimal_svc()._generate_recommendations(comps)) <= 10


# ===========================================================================
# HealthMonitoringService.get_basic_health_status
# ===========================================================================


class TestGetBasicHealthStatus:
    def test_returns_dict(self):
        assert isinstance(_minimal_svc().get_basic_health_status(None, None), dict)

    def test_has_status_key(self):
        assert "status" in _minimal_svc().get_basic_health_status(None, None)

    def test_degraded_when_inputs_none(self):
        assert _minimal_svc().get_basic_health_status(None, None)["status"] == "degraded"

    def test_version_is_set(self):
        assert _minimal_svc().get_basic_health_status(None, None)["version"] == "2.0.0"

    def test_gemini_key_present_true(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "key123")
        result = _minimal_svc().get_basic_health_status(None, None)
        assert result["components"]["gemini_key_present"] is True

    def test_gemini_key_present_false(self, monkeypatch):
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        result = _minimal_svc().get_basic_health_status(None, None)
        assert result["components"]["gemini_key_present"] is False


# ===========================================================================
# HealthMonitoringService utility methods
# ===========================================================================


class TestHealthMonitoringUtilityMethods:
    def test_external_connectors_returns_dict(self):
        assert isinstance(_minimal_svc().check_external_connectors_health(), dict)

    def test_pipeline_health_returns_dict(self):
        result = _minimal_svc().check_video_to_software_pipeline_health()
        assert "status" in result

    def test_get_current_health_none_initially(self):
        assert _minimal_svc().get_current_health() is None

    def test_get_health_history_empty_initially(self):
        assert _minimal_svc().get_health_history() == []

    def test_get_recent_incidents_empty_no_history(self):
        assert _minimal_svc()._get_recent_incidents() == []

    def test_get_component_metrics_empty_no_history(self):
        assert _minimal_svc().get_component_metrics("cpu") == []

    def test_record_request_with_app_checker(self):
        svc = HealthMonitoringService({
            "enable_system_resources": False, "enable_database": False,
            "enable_external_services": False, "enable_application": True,
        })
        svc.record_request()
        assert svc.application_checker.request_count == 1

    def test_record_request_no_op_without_app_checker(self):
        svc = _minimal_svc()
        svc.record_request()  # should not raise

    def test_record_error_with_app_checker(self):
        svc = HealthMonitoringService({
            "enable_system_resources": False, "enable_database": False,
            "enable_external_services": False, "enable_application": True,
        })
        svc.record_error()
        assert svc.application_checker.error_count == 1
