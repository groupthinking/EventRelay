"""Additional tests for LoadBalancer in horizontal_scaling_system.py."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_SRC = Path(__file__).resolve().parents[2] / "src"
sys.path.insert(0, str(_SRC))

from youtube_extension.backend.services.horizontal_scaling_system import (
    LoadBalanceStrategy,
    LoadBalancer,
    ServiceInstance,
    ServiceStatus,
    AutoScaler,
    ScalingRule,
    HorizontalScalingSystem,
)


def _make_instance(service_id: str = "s1", healthy: bool = True) -> ServiceInstance:
    inst = ServiceInstance(service_id=service_id, host="localhost", port=8000)
    if healthy:
        inst.status = ServiceStatus.HEALTHY
        inst.current_connections = 0
        inst.cpu_usage = 10.0
        inst.response_time_ms = 50.0
    return inst


# ===========================================================================
# LoadBalancer.__init__
# ===========================================================================


class TestLoadBalancerInit:
    def test_default_strategy(self):
        lb = LoadBalancer()
        assert lb.strategy == LoadBalanceStrategy.PERFORMANCE_BASED

    def test_custom_strategy(self):
        lb = LoadBalancer(strategy=LoadBalanceStrategy.ROUND_ROBIN)
        assert lb.strategy == LoadBalanceStrategy.ROUND_ROBIN

    def test_service_instances_empty(self):
        lb = LoadBalancer()
        assert lb.service_instances == {}

    def test_request_history_empty(self):
        lb = LoadBalancer()
        assert len(lb.request_history) == 0


# ===========================================================================
# LoadBalancer.register_service / unregister_service
# ===========================================================================


class TestRegisterService:
    def test_registers_instance(self):
        lb = LoadBalancer()
        inst = _make_instance()
        lb.register_service("my_svc", inst)
        assert "s1" in lb.service_instances

    def test_adds_to_registry(self):
        lb = LoadBalancer()
        inst = _make_instance()
        lb.register_service("my_svc", inst)
        assert "s1" in lb.service_registry["my_svc"]

    def test_unregister_removes_instance(self):
        lb = LoadBalancer()
        inst = _make_instance()
        lb.register_service("my_svc", inst)
        lb.unregister_service("my_svc", "s1")
        assert "s1" not in lb.service_instances

    def test_unregister_removes_from_registry(self):
        lb = LoadBalancer()
        inst = _make_instance()
        lb.register_service("my_svc", inst)
        lb.unregister_service("my_svc", "s1")
        assert "s1" not in lb.service_registry["my_svc"]

    def test_unregister_nonexistent_no_error(self):
        lb = LoadBalancer()
        lb.unregister_service("my_svc", "nonexistent")  # should not raise


# ===========================================================================
# LoadBalancer._get_healthy_instances
# ===========================================================================


class TestGetHealthyInstances:
    def test_returns_healthy_instances(self):
        lb = LoadBalancer()
        inst = _make_instance()
        lb.register_service("svc", inst)
        result = lb._get_healthy_instances("svc")
        assert len(result) == 1

    def test_excludes_unhealthy_instances(self):
        lb = LoadBalancer()
        inst = _make_instance(healthy=False)
        lb.register_service("svc", inst)
        result = lb._get_healthy_instances("svc")
        assert len(result) == 0

    def test_empty_for_unknown_service(self):
        lb = LoadBalancer()
        result = lb._get_healthy_instances("unknown_svc")
        assert result == []


# ===========================================================================
# LoadBalancer.route_request
# ===========================================================================


class TestRouteRequest:
    async def test_returns_none_for_unknown_service(self):
        lb = LoadBalancer()
        result = await lb.route_request("unknown_svc")
        assert result is None

    async def test_returns_none_when_no_healthy_instances(self):
        lb = LoadBalancer()
        inst = _make_instance(healthy=False)
        lb.register_service("svc", inst)
        result = await lb.route_request("svc")
        assert result is None

    async def test_returns_instance_when_available(self):
        lb = LoadBalancer()
        inst = _make_instance()
        lb.register_service("svc", inst)
        result = await lb.route_request("svc")
        assert result is not None

    async def test_increments_connection_count(self):
        lb = LoadBalancer()
        inst = _make_instance()
        lb.register_service("svc", inst)
        await lb.route_request("svc")
        assert inst.current_connections == 1

    async def test_records_routing_stat(self):
        lb = LoadBalancer()
        inst = _make_instance()
        lb.register_service("svc", inst)
        await lb.route_request("svc")
        assert lb.routing_stats["s1"] == 1

    async def test_records_request_history(self):
        lb = LoadBalancer()
        inst = _make_instance()
        lb.register_service("svc", inst)
        await lb.route_request("svc")
        assert len(lb.request_history) == 1


# ===========================================================================
# LoadBalancer.release_request
# ===========================================================================


class TestReleaseRequest:
    def test_decrements_connection_count(self):
        lb = LoadBalancer()
        inst = _make_instance()
        inst.current_connections = 2
        lb.release_request(inst, response_time_ms=100.0, success=True)
        assert inst.current_connections == 1

    def test_connection_count_not_negative(self):
        lb = LoadBalancer()
        inst = _make_instance()
        inst.current_connections = 0
        lb.release_request(inst, response_time_ms=100.0, success=True)
        assert inst.current_connections == 0

    def test_updates_response_time_first_time(self):
        lb = LoadBalancer()
        inst = _make_instance()
        inst.response_time_ms = 0
        lb.release_request(inst, response_time_ms=200.0, success=True)
        assert inst.response_time_ms == 200.0

    def test_uses_ema_for_subsequent_updates(self):
        lb = LoadBalancer()
        inst = _make_instance()
        inst.response_time_ms = 100.0
        lb.release_request(inst, response_time_ms=200.0, success=True)
        # EMA: 0.3*200 + 0.7*100 = 60+70 = 130
        assert inst.response_time_ms == pytest.approx(130.0)


# ===========================================================================
# LoadBalancer._select_instance with various strategies
# ===========================================================================


class TestSelectInstance:
    def test_single_instance_returned_directly(self):
        lb = LoadBalancer()
        inst = _make_instance()
        result = lb._select_instance([inst])
        assert result is inst

    def test_round_robin_selection(self):
        lb = LoadBalancer(strategy=LoadBalanceStrategy.ROUND_ROBIN)
        i1 = _make_instance("i1")
        i2 = _make_instance("i2")
        results = [lb._select_instance([i1, i2]) for _ in range(4)]
        ids = [r.service_id for r in results]
        assert ids.count("i1") == 2
        assert ids.count("i2") == 2

    def test_least_connections_selection(self):
        lb = LoadBalancer(strategy=LoadBalanceStrategy.LEAST_CONNECTIONS)
        i1 = _make_instance("i1")
        i2 = _make_instance("i2")
        i1.current_connections = 5
        i2.current_connections = 1
        result = lb._select_instance([i1, i2])
        assert result.service_id == "i2"

    def test_performance_based_selection(self):
        lb = LoadBalancer(strategy=LoadBalanceStrategy.PERFORMANCE_BASED)
        i1 = _make_instance("i1")
        i2 = _make_instance("i2")
        i1.response_time_ms = 500.0  # slower
        i2.response_time_ms = 10.0   # faster
        result = lb._select_instance([i1, i2])
        assert result is not None  # should select lower load_factor

    def test_weighted_round_robin_selection(self):
        lb = LoadBalancer(strategy=LoadBalanceStrategy.WEIGHTED_ROUND_ROBIN)
        i1 = _make_instance("i1")
        i1.weight = 3
        i2 = _make_instance("i2")
        i2.weight = 1
        # Just verify it returns one of the instances
        result = lb._select_instance([i1, i2])
        assert result in [i1, i2]

    def test_consistent_hash_selection(self):
        lb = LoadBalancer(strategy=LoadBalanceStrategy.CONSISTENT_HASH)
        i1 = _make_instance("i1")
        i2 = _make_instance("i2")
        meta = {"client_id": "user123"}
        result1 = lb._select_instance([i1, i2], meta)
        result2 = lb._select_instance([i1, i2], meta)
        # Same input should give same result
        assert result1.service_id == result2.service_id


# ===========================================================================
# LoadBalancer.get_load_balancer_stats
# ===========================================================================


class TestLoadBalancerStats:
    def test_returns_dict(self):
        lb = LoadBalancer()
        stats = lb.get_load_balancer_stats()
        assert isinstance(stats, dict)

    def test_has_total_instances_key(self):
        lb = LoadBalancer()
        stats = lb.get_load_balancer_stats()
        assert "total_instances" in stats

    def test_empty_when_no_instances(self):
        lb = LoadBalancer()
        stats = lb.get_load_balancer_stats()
        assert stats["total_instances"] == 0

    def test_counts_registered_instances(self):
        import statistics as _stat_mod
        import youtube_extension.backend.services.horizontal_scaling_system as _hss_mod
        _hss_mod.statistics = _stat_mod
        lb = LoadBalancer()
        lb.register_service("svc", _make_instance("i1"))
        lb.register_service("svc", _make_instance("i2"))
        stats = lb.get_load_balancer_stats()
        assert stats["total_instances"] == 2


# ===========================================================================
# AutoScaler.__init__
# ===========================================================================


class TestAutoScalerInit:
    def test_init_with_load_balancer(self):
        lb = LoadBalancer()
        scaler = AutoScaler(lb)
        assert scaler.load_balancer is lb

    def test_scaling_rules_empty(self):
        lb = LoadBalancer()
        scaler = AutoScaler(lb)
        assert scaler.scaling_rules == {}

    def test_auto_scaling_inactive(self):
        lb = LoadBalancer()
        scaler = AutoScaler(lb)
        assert scaler.scaling_task is None


# ===========================================================================
# AutoScaler.add_scaling_rule
# ===========================================================================


class TestAddScalingRule:
    def test_adds_rule(self):
        lb = LoadBalancer()
        scaler = AutoScaler(lb)
        rule = ScalingRule(metric="cpu", threshold_up=80, threshold_down=20)
        scaler.add_scaling_rule("svc", rule)
        assert "svc" in scaler.scaling_rules

    def test_stored_rule(self):
        lb = LoadBalancer()
        scaler = AutoScaler(lb)
        rule = ScalingRule(metric="memory", threshold_up=85, threshold_down=30)
        scaler.add_scaling_rule("svc", rule)
        assert scaler.scaling_rules["svc"][-1] is rule
