"""Unit tests for health_monitoring_service enums and dataclasses."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from youtube_extension.backend.services.health_monitoring_service import (
    ComponentHealth,
    ComponentType,
    HealthMetric,
    HealthStatus,
    SystemHealth,
)


# ===========================================================================
# HealthStatus enum
# ===========================================================================


class TestHealthStatusEnum:
    def test_healthy_value(self):
        assert HealthStatus.HEALTHY.value == "healthy"

    def test_warning_value(self):
        assert HealthStatus.WARNING.value == "warning"

    def test_degraded_value(self):
        assert HealthStatus.DEGRADED.value == "degraded"

    def test_critical_value(self):
        assert HealthStatus.CRITICAL.value == "critical"

    def test_failed_value(self):
        assert HealthStatus.FAILED.value == "failed"

    def test_has_five_members(self):
        assert len(HealthStatus) == 5


# ===========================================================================
# ComponentType enum
# ===========================================================================


class TestComponentTypeEnum:
    def test_api_server_value(self):
        assert ComponentType.API_SERVER.value == "api_server"

    def test_database_value(self):
        assert ComponentType.DATABASE.value == "database"

    def test_external_service_value(self):
        assert ComponentType.EXTERNAL_SERVICE.value == "external_service"

    def test_system_resource_value(self):
        assert ComponentType.SYSTEM_RESOURCE.value == "system_resource"

    def test_application_value(self):
        assert ComponentType.APPLICATION.value == "application"

    def test_has_five_members(self):
        assert len(ComponentType) == 5


# ===========================================================================
# HealthMetric dataclass
# ===========================================================================


class TestHealthMetric:
    @pytest.fixture
    def metric(self):
        return HealthMetric(
            name="cpu_usage",
            value=75.0,
            unit="percent",
            status=HealthStatus.WARNING,
            threshold_warning=70.0,
            threshold_critical=90.0,
            timestamp=1234567890.0,
        )

    def test_name_stored(self, metric):
        assert metric.name == "cpu_usage"

    def test_value_stored(self, metric):
        assert metric.value == 75.0

    def test_unit_stored(self, metric):
        assert metric.unit == "percent"

    def test_status_stored(self, metric):
        assert metric.status == HealthStatus.WARNING

    def test_threshold_warning_stored(self, metric):
        assert metric.threshold_warning == 70.0

    def test_threshold_critical_stored(self, metric):
        assert metric.threshold_critical == 90.0

    def test_timestamp_stored(self, metric):
        assert metric.timestamp == 1234567890.0

    def test_metadata_defaults_to_empty_dict(self, metric):
        assert metric.metadata == {}

    def test_explicit_metadata_preserved(self):
        m = HealthMetric(
            name="mem",
            value=50.0,
            unit="percent",
            status=HealthStatus.HEALTHY,
            threshold_warning=80.0,
            threshold_critical=95.0,
            timestamp=0.0,
            metadata={"cores": 4},
        )
        assert m.metadata["cores"] == 4


# ===========================================================================
# ComponentHealth dataclass
# ===========================================================================


class TestComponentHealth:
    @pytest.fixture
    def component(self):
        return ComponentHealth(
            name="database",
            component_type=ComponentType.DATABASE,
            status=HealthStatus.HEALTHY,
            uptime_seconds=3600.0,
            last_check=1234567890.0,
            metrics=[],
        )

    def test_name_stored(self, component):
        assert component.name == "database"

    def test_component_type_stored(self, component):
        assert component.component_type == ComponentType.DATABASE

    def test_status_stored(self, component):
        assert component.status == HealthStatus.HEALTHY

    def test_uptime_seconds_stored(self, component):
        assert component.uptime_seconds == 3600.0

    def test_last_check_stored(self, component):
        assert component.last_check == 1234567890.0

    def test_metrics_stored(self, component):
        assert component.metrics == []

    def test_dependencies_defaults_to_empty_list(self, component):
        assert component.dependencies == []

    def test_recovery_actions_defaults_to_empty_list(self, component):
        assert component.recovery_actions == []

    def test_explicit_dependencies(self):
        c = ComponentHealth(
            name="api",
            component_type=ComponentType.API_SERVER,
            status=HealthStatus.HEALTHY,
            uptime_seconds=100.0,
            last_check=0.0,
            metrics=[],
            dependencies=["db", "cache"],
        )
        assert c.dependencies == ["db", "cache"]

    def test_explicit_recovery_actions(self):
        c = ComponentHealth(
            name="api",
            component_type=ComponentType.API_SERVER,
            status=HealthStatus.CRITICAL,
            uptime_seconds=100.0,
            last_check=0.0,
            metrics=[],
            recovery_actions=["restart"],
        )
        assert c.recovery_actions == ["restart"]


# ===========================================================================
# SystemHealth dataclass
# ===========================================================================


class TestSystemHealth:
    @pytest.fixture
    def system_health(self):
        return SystemHealth(
            overall_status=HealthStatus.HEALTHY,
            score=95.0,
            timestamp=1234567890.0,
            uptime_seconds=7200.0,
            components=[],
            active_alerts=[],
            recent_incidents=[],
        )

    def test_overall_status_stored(self, system_health):
        assert system_health.overall_status == HealthStatus.HEALTHY

    def test_score_stored(self, system_health):
        assert system_health.score == 95.0

    def test_timestamp_stored(self, system_health):
        assert system_health.timestamp == 1234567890.0

    def test_uptime_seconds_stored(self, system_health):
        assert system_health.uptime_seconds == 7200.0

    def test_components_stored(self, system_health):
        assert system_health.components == []

    def test_active_alerts_stored(self, system_health):
        assert system_health.active_alerts == []

    def test_recent_incidents_stored(self, system_health):
        assert system_health.recent_incidents == []

    def test_recommendations_defaults_to_empty_list(self, system_health):
        assert system_health.recommendations == []

    def test_explicit_recommendations(self):
        sh = SystemHealth(
            overall_status=HealthStatus.WARNING,
            score=70.0,
            timestamp=0.0,
            uptime_seconds=100.0,
            components=[],
            active_alerts=[],
            recent_incidents=[],
            recommendations=["Scale up"],
        )
        assert sh.recommendations == ["Scale up"]
