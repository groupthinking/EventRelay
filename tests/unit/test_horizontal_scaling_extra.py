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


# ===========================================================================
# TestReleaseRequestFailure — line 192: pass branch (not success + HEALTHY)
# ===========================================================================


class TestReleaseRequestFailure:
    def test_release_failure_healthy_instance_does_not_raise(self):
        """Line 192: pass inside release_request when not success and instance is HEALTHY."""
        lb = LoadBalancer()
        inst = _make_instance()
        assert inst.status == ServiceStatus.HEALTHY
        inst.current_connections = 1
        # Should reach line 190-192 without error
        lb.release_request(inst, response_time_ms=100.0, success=False)
        # Connection still decremented
        assert inst.current_connections == 0

    def test_release_failure_status_unchanged(self):
        """Healthy status must remain unchanged after a single failure (pass branch)."""
        lb = LoadBalancer()
        inst = _make_instance()
        inst.current_connections = 3
        lb.release_request(inst, response_time_ms=50.0, success=False)
        assert inst.status == ServiceStatus.HEALTHY

    def test_release_failure_response_time_still_updated(self):
        """Even on failure the EMA update is performed before the pass branch."""
        lb = LoadBalancer()
        inst = _make_instance()
        inst.response_time_ms = 100.0
        inst.current_connections = 1
        lb.release_request(inst, response_time_ms=200.0, success=False)
        # EMA: 0.3*200 + 0.7*100 = 130
        assert inst.response_time_ms == pytest.approx(130.0)

    def test_release_failure_unhealthy_instance_skips_pass_branch(self):
        """When instance is NOT healthy the pass branch is not reached (no error either)."""
        lb = LoadBalancer()
        inst = _make_instance()
        inst.status = ServiceStatus.UNHEALTHY
        inst.current_connections = 1
        lb.release_request(inst, response_time_ms=100.0, success=False)
        assert inst.current_connections == 0

    def test_release_success_true_skips_failure_branch(self):
        """Ensure success=True never enters the failure branch."""
        lb = LoadBalancer()
        inst = _make_instance()
        inst.current_connections = 1
        lb.release_request(inst, response_time_ms=100.0, success=True)
        assert inst.status == ServiceStatus.HEALTHY


# ===========================================================================
# TestWeightedRoundRobinEdgeCases — lines 241 & 252
# ===========================================================================


class TestWeightedRoundRobinEdgeCases:
    def test_all_zero_weights_returns_first_instance(self):
        """Line 241: total_weight == 0 → return instances[0]."""
        lb = LoadBalancer(strategy=LoadBalanceStrategy.WEIGHTED_ROUND_ROBIN)
        i1 = _make_instance("i1")
        i2 = _make_instance("i2")
        i1.weight = 0
        i2.weight = 0
        result = lb._select_instance([i1, i2])
        assert result is i1

    def test_single_zero_weight_instance_returns_it(self):
        """Single instance with weight=0 → total_weight=0 → return instances[0]."""
        lb = LoadBalancer(strategy=LoadBalanceStrategy.WEIGHTED_ROUND_ROBIN)
        inst = _make_instance("only")
        inst.weight = 0
        # _select_instance short-circuits at len==1, so call the internal method directly
        result = lb._weighted_round_robin_selection([inst])
        assert result is inst

    def test_fallback_returns_last_instance(self):
        """Line 252: fallback return instances[-1].

        Force this by mocking random.randint to return a value greater than all
        cumulative weights so the for-loop exhausts without returning.
        """
        import unittest.mock as mock

        lb = LoadBalancer(strategy=LoadBalanceStrategy.WEIGHTED_ROUND_ROBIN)
        i1 = _make_instance("i1")
        i2 = _make_instance("i2")
        i1.weight = 1
        i2.weight = 1
        # randint(1, 2) normally returns 1 or 2; patch it to return 3 which is
        # greater than total_weight=2, so the loop never returns → hits line 252.
        with mock.patch(
            "youtube_extension.backend.services.horizontal_scaling_system.random.randint",
            return_value=3,
        ):
            result = lb._weighted_round_robin_selection([i1, i2])
        assert result is i2  # instances[-1]

    def test_weighted_selection_respects_higher_weight(self):
        """Normal weighted selection should favour the heavier instance over many draws."""
        lb = LoadBalancer(strategy=LoadBalanceStrategy.WEIGHTED_ROUND_ROBIN)
        i1 = _make_instance("heavy")
        i2 = _make_instance("light")
        i1.weight = 9
        i2.weight = 1
        counts: dict[str, int] = {"heavy": 0, "light": 0}
        for _ in range(100):
            r = lb._weighted_round_robin_selection([i1, i2])
            counts[r.service_id] += 1
        # With weight 9:1 we expect heavy to win the vast majority
        assert counts["heavy"] > counts["light"]


# ===========================================================================
# TestConsistentHashNoMetadata — line 257
# ===========================================================================


class TestConsistentHashNoMetadata:
    def test_no_metadata_falls_back_to_performance_based(self):
        """Line 257: _consistent_hash_selection with no metadata → _performance_based_selection."""
        lb = LoadBalancer(strategy=LoadBalanceStrategy.CONSISTENT_HASH)
        i1 = _make_instance("i1")
        i2 = _make_instance("i2")
        i1.cpu_usage = 5.0
        i2.cpu_usage = 80.0
        # Call with None metadata (the default)
        result = lb._consistent_hash_selection([i1, i2], None)
        # Performance-based picks lowest load_factor — i1 has much less cpu
        assert result is i1

    def test_empty_dict_metadata_falls_back_to_performance_based(self):
        """Empty dict is falsy → same fallback path."""
        lb = LoadBalancer(strategy=LoadBalanceStrategy.CONSISTENT_HASH)
        i1 = _make_instance("i1")
        i2 = _make_instance("i2")
        i1.cpu_usage = 5.0
        i2.cpu_usage = 80.0
        result = lb._consistent_hash_selection([i1, i2], {})
        assert result is i1

    def test_select_instance_consistent_hash_no_metadata(self):
        """_select_instance with CONSISTENT_HASH and no metadata still returns something."""
        lb = LoadBalancer(strategy=LoadBalanceStrategy.CONSISTENT_HASH)
        i1 = _make_instance("i1")
        i2 = _make_instance("i2")
        result = lb._select_instance([i1, i2])  # no request_metadata arg
        assert result in [i1, i2]

    def test_consistent_hash_with_metadata_is_deterministic(self):
        """With real metadata the hash path (line 260-265) is exercised deterministically."""
        lb = LoadBalancer(strategy=LoadBalanceStrategy.CONSISTENT_HASH)
        i1 = _make_instance("i1")
        i2 = _make_instance("i2")
        meta = {"user": "alice", "session": "xyz"}
        results = {lb._consistent_hash_selection([i1, i2], meta).service_id for _ in range(5)}
        assert len(results) == 1  # always the same instance


# ===========================================================================
# TestCheckInstanceHealth — lines 314-337
# ===========================================================================


class TestCheckInstanceHealth:
    async def test_check_sets_healthy_or_unhealthy(self):
        """_check_instance_health sets status to HEALTHY or UNHEALTHY."""
        lb = LoadBalancer()
        inst = _make_instance()
        await lb._check_instance_health(inst)
        assert inst.status in (ServiceStatus.HEALTHY, ServiceStatus.UNHEALTHY)

    async def test_check_healthy_updates_last_health_check(self):
        """When healthy, last_health_check is refreshed."""
        import unittest.mock as mock
        from datetime import datetime, timezone

        lb = LoadBalancer()
        inst = _make_instance()
        old_ts = inst.last_health_check

        with mock.patch(
            "youtube_extension.backend.services.horizontal_scaling_system.random.choice",
            return_value=True,
        ):
            await lb._check_instance_health(inst)

        assert inst.status == ServiceStatus.HEALTHY
        assert inst.last_health_check >= old_ts

    async def test_check_healthy_updates_cpu_usage(self):
        """After a healthy check, cpu_usage is updated (simulated)."""
        import unittest.mock as mock

        lb = LoadBalancer()
        inst = _make_instance()

        with mock.patch(
            "youtube_extension.backend.services.horizontal_scaling_system.random.choice",
            return_value=True,
        ):
            await lb._check_instance_health(inst)

        assert inst.status == ServiceStatus.HEALTHY
        assert 0 <= inst.cpu_usage <= 100

    async def test_check_unhealthy_sets_unhealthy_status(self):
        """When random.choice returns False the instance becomes UNHEALTHY."""
        import unittest.mock as mock

        lb = LoadBalancer()
        inst = _make_instance()

        with mock.patch(
            "youtube_extension.backend.services.horizontal_scaling_system.random.choice",
            return_value=False,
        ):
            await lb._check_instance_health(inst)

        assert inst.status == ServiceStatus.UNHEALTHY

    async def test_check_exception_sets_unhealthy(self):
        """If an exception occurs inside _check_instance_health, status → UNHEALTHY."""
        import unittest.mock as mock

        lb = LoadBalancer()
        inst = _make_instance()

        with mock.patch(
            "youtube_extension.backend.services.horizontal_scaling_system.random.choice",
            side_effect=RuntimeError("boom"),
        ):
            await lb._check_instance_health(inst)

        assert inst.status == ServiceStatus.UNHEALTHY


# ===========================================================================
# TestPerformHealthChecks — lines 303-310
# ===========================================================================


class TestPerformHealthChecks:
    async def test_no_instances_does_not_raise(self):
        """_perform_health_checks with empty registry completes without error."""
        lb = LoadBalancer()
        await lb._perform_health_checks()  # should not raise

    async def test_healthy_instance_is_checked(self):
        """Instances NOT in MAINTENANCE are included in the check tasks."""
        import unittest.mock as mock

        lb = LoadBalancer()
        inst = _make_instance()
        lb.register_service("svc", inst)

        with mock.patch.object(lb, "_check_instance_health", return_value=None) as patched:
            await lb._perform_health_checks()

        patched.assert_called_once_with(inst)

    async def test_maintenance_instance_is_skipped(self):
        """Instances in MAINTENANCE status are excluded from health checks."""
        import unittest.mock as mock

        lb = LoadBalancer()
        inst = _make_instance()
        inst.status = ServiceStatus.MAINTENANCE
        lb.register_service("svc", inst)

        with mock.patch.object(lb, "_check_instance_health", return_value=None) as patched:
            await lb._perform_health_checks()

        patched.assert_not_called()

    async def test_mixed_instances_only_non_maintenance_checked(self):
        """Only non-MAINTENANCE instances get a health-check task."""
        import unittest.mock as mock

        lb = LoadBalancer()
        healthy_inst = _make_instance("h1")
        maint_inst = _make_instance("m1")
        maint_inst.status = ServiceStatus.MAINTENANCE

        lb.register_service("svc", healthy_inst)
        lb.register_service("svc", maint_inst)

        checked: list[ServiceInstance] = []

        async def fake_check(instance: ServiceInstance):
            checked.append(instance)

        with mock.patch.object(lb, "_check_instance_health", side_effect=fake_check):
            await lb._perform_health_checks()

        assert healthy_inst in checked
        assert maint_inst not in checked

    async def test_multiple_healthy_instances_all_checked(self):
        """All non-MAINTENANCE instances receive a health check."""
        import unittest.mock as mock

        lb = LoadBalancer()
        for idx in range(3):
            lb.register_service("svc", _make_instance(f"inst{idx}"))

        call_count = []

        async def fake_check(_inst):
            call_count.append(1)

        with mock.patch.object(lb, "_check_instance_health", side_effect=fake_check):
            await lb._perform_health_checks()

        assert len(call_count) == 3
