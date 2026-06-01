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
