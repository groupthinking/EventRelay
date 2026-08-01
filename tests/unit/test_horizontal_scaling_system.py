"""Unit tests for ServiceStatus, LoadBalanceStrategy, ServiceInstance, and ScalingRule."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from youtube_extension.backend.services.horizontal_scaling_system import (
    LoadBalanceStrategy,
    ScalingRule,
    ServiceInstance,
    ServiceStatus,
)

# ===========================================================================
# ServiceStatus enum
# ===========================================================================


class TestServiceStatusEnum:
    def test_healthy_value(self):
        assert ServiceStatus.HEALTHY.value == "healthy"

    def test_unhealthy_value(self):
        assert ServiceStatus.UNHEALTHY.value == "unhealthy"

    def test_starting_value(self):
        assert ServiceStatus.STARTING.value == "starting"

    def test_stopping_value(self):
        assert ServiceStatus.STOPPING.value == "stopping"

    def test_maintenance_value(self):
        assert ServiceStatus.MAINTENANCE.value == "maintenance"

    def test_has_five_members(self):
        assert len(ServiceStatus) == 5


# ===========================================================================
# LoadBalanceStrategy enum
# ===========================================================================


class TestLoadBalanceStrategyEnum:
    def test_round_robin_value(self):
        assert LoadBalanceStrategy.ROUND_ROBIN.value == "round_robin"

    def test_least_connections_value(self):
        assert LoadBalanceStrategy.LEAST_CONNECTIONS.value == "least_connections"

    def test_weighted_round_robin_value(self):
        assert LoadBalanceStrategy.WEIGHTED_ROUND_ROBIN.value == "weighted_round_robin"

    def test_consistent_hash_value(self):
        assert LoadBalanceStrategy.CONSISTENT_HASH.value == "consistent_hash"

    def test_performance_based_value(self):
        assert LoadBalanceStrategy.PERFORMANCE_BASED.value == "performance_based"

    def test_has_five_members(self):
        assert len(LoadBalanceStrategy) == 5


# ===========================================================================
# ServiceInstance — defaults
# ===========================================================================


class TestServiceInstanceDefaults:
    @pytest.fixture
    def inst(self):
        return ServiceInstance(service_id="svc-1", host="localhost", port=8080)

    def test_status_default_starting(self, inst):
        assert inst.status == ServiceStatus.STARTING

    def test_weight_default_one(self, inst):
        assert inst.weight == 1

    def test_max_connections_default(self, inst):
        assert inst.max_connections == 100

    def test_current_connections_default_zero(self, inst):
        assert inst.current_connections == 0

    def test_response_time_default_zero(self, inst):
        assert inst.response_time_ms == 0.0

    def test_cpu_usage_default_zero(self, inst):
        assert inst.cpu_usage == 0.0

    def test_memory_usage_default_zero(self, inst):
        assert inst.memory_usage_mb == 0.0

    def test_metadata_default_empty_dict(self, inst):
        assert inst.metadata == {}

    def test_last_health_check_set(self, inst):
        assert inst.last_health_check is not None


# ===========================================================================
# ServiceInstance.load_factor
# ===========================================================================


class TestServiceInstanceLoadFactor:
    def _make(self, connections=0, cpu=0.0, response_ms=0.0, max_conn=100):
        return ServiceInstance(
            service_id="s",
            host="h",
            port=8000,
            current_connections=connections,
            cpu_usage=cpu,
            response_time_ms=response_ms,
            max_connections=max_conn,
        )

    def test_all_zero_gives_zero(self):
        assert self._make().load_factor == 0.0

    def test_connection_component(self):
        # 50/100 = 0.5 * 0.4 = 0.2; cpu=0; response=0
        inst = self._make(connections=50, cpu=0.0, response_ms=0.0)
        assert abs(inst.load_factor - 0.2) < 1e-9

    def test_cpu_component(self):
        # connections=0; cpu=50 → 0.5 * 0.3 = 0.15; response=0
        inst = self._make(connections=0, cpu=50.0, response_ms=0.0)
        assert abs(inst.load_factor - 0.15) < 1e-9

    def test_response_component(self):
        # connections=0; cpu=0; response=500ms → 0.5 * 0.3 = 0.15
        inst = self._make(connections=0, cpu=0.0, response_ms=500.0)
        assert abs(inst.load_factor - 0.15) < 1e-9

    def test_response_capped_at_1s(self):
        # response=2000ms → capped to 1.0 * 0.3 = 0.3
        inst = self._make(connections=0, cpu=0.0, response_ms=2000.0)
        assert abs(inst.load_factor - 0.3) < 1e-9

    def test_full_load_is_one(self):
        # 100/100=1.0*0.4 + 100%cpu=1.0*0.3 + 1000ms=1.0*0.3 = 1.0
        inst = self._make(connections=100, cpu=100.0, response_ms=1000.0)
        assert abs(inst.load_factor - 1.0) < 1e-9

    def test_zero_max_connections_no_divide_error(self):
        inst = self._make(connections=5, cpu=0.0, response_ms=0.0, max_conn=0)
        assert inst.load_factor == 0.0


# ===========================================================================
# ServiceInstance.is_healthy
# ===========================================================================


class TestServiceInstanceIsHealthy:
    def _make(self, status=ServiceStatus.HEALTHY, connections=0, cpu=0.0, response_ms=0.0):
        return ServiceInstance(
            service_id="s",
            host="h",
            port=8000,
            status=status,
            current_connections=connections,
            cpu_usage=cpu,
            response_time_ms=response_ms,
        )

    def test_healthy_when_all_ok(self):
        assert self._make().is_healthy is True

    def test_unhealthy_status_fails(self):
        assert self._make(status=ServiceStatus.UNHEALTHY).is_healthy is False

    def test_starting_status_fails(self):
        assert self._make(status=ServiceStatus.STARTING).is_healthy is False

    def test_stopping_status_fails(self):
        assert self._make(status=ServiceStatus.STOPPING).is_healthy is False

    def test_maintenance_status_fails(self):
        assert self._make(status=ServiceStatus.MAINTENANCE).is_healthy is False

    def test_at_max_connections_is_unhealthy(self):
        # current_connections must be *less than* max_connections
        inst = self._make(connections=100)  # max_connections default 100
        assert inst.is_healthy is False

    def test_below_max_connections_ok(self):
        inst = self._make(connections=99)
        assert inst.is_healthy is True

    def test_cpu_at_90_is_unhealthy(self):
        # cpu_usage < 90 required
        assert self._make(cpu=90.0).is_healthy is False

    def test_cpu_just_below_90_ok(self):
        assert self._make(cpu=89.9).is_healthy is True

    def test_response_at_5000_is_unhealthy(self):
        # response_time_ms < 5000 required
        assert self._make(response_ms=5000.0).is_healthy is False

    def test_response_just_below_5000_ok(self):
        assert self._make(response_ms=4999.9).is_healthy is True


# ===========================================================================
# ScalingRule — defaults
# ===========================================================================


class TestScalingRuleDefaults:
    @pytest.fixture
    def rule(self):
        return ScalingRule(metric="cpu", threshold_up=80.0, threshold_down=20.0)

    def test_metric_stored(self, rule):
        assert rule.metric == "cpu"

    def test_threshold_up_stored(self, rule):
        assert rule.threshold_up == 80.0

    def test_threshold_down_stored(self, rule):
        assert rule.threshold_down == 20.0

    def test_scale_up_count_default_one(self, rule):
        assert rule.scale_up_count == 1

    def test_scale_down_count_default_one(self, rule):
        assert rule.scale_down_count == 1

    def test_cooldown_seconds_default_300(self, rule):
        assert rule.cooldown_seconds == 300

    def test_min_instances_default_one(self, rule):
        assert rule.min_instances == 1

    def test_max_instances_default_ten(self, rule):
        assert rule.max_instances == 10

    def test_last_scaled_auto_set(self, rule):
        assert rule.last_scaled is not None

    def test_custom_values(self):
        rule = ScalingRule(
            metric="memory",
            threshold_up=90.0,
            threshold_down=30.0,
            scale_up_count=3,
            scale_down_count=2,
            cooldown_seconds=120,
            min_instances=2,
            max_instances=20,
        )
        assert rule.scale_up_count == 3
        assert rule.scale_down_count == 2
        assert rule.cooldown_seconds == 120
        assert rule.min_instances == 2
        assert rule.max_instances == 20
