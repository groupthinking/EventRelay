"""
Pytest tests for load_balancer.py — LoadBalancer class and related components.

Covers:
- LoadBalancingAlgorithm enum values
- ServiceStatus enum values
- ServiceInstance dataclass (__post_init__, url, failure_rate, load_score)
- HealthCheckConfig defaults
- CircuitBreakerConfig defaults
- CircuitBreaker init, can_execute, record_success, record_failure
- LoadBalancer init, register_service, unregister_service,
  get_healthy_services, _select_service (multiple algorithms),
  _update_global_metrics, get_load_balancer_stats, route_request,
  record_response, should_scale_up, should_scale_down
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from youtube_extension.backend.services.load_balancer import (
    CircuitBreaker,
    CircuitBreakerConfig,
    HealthCheckConfig,
    LoadBalancer,
    LoadBalancingAlgorithm,
    ServiceInstance,
    ServiceStatus,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_instance(id_="i1", host="127.0.0.1", port=8001, **kwargs) -> ServiceInstance:
    return ServiceInstance(id=id_, host=host, port=port, **kwargs)


def make_lb(name="svc", algorithm=LoadBalancingAlgorithm.ROUND_ROBIN) -> LoadBalancer:
    lb = LoadBalancer(name, algorithm)
    lb.health_check_enabled = False  # avoid background tasks in unit tests
    return lb


# ===========================================================================
# LoadBalancingAlgorithm enum
# ===========================================================================


class TestLoadBalancingAlgorithmEnum:
    def test_round_robin_value(self):
        assert LoadBalancingAlgorithm.ROUND_ROBIN.value == "round_robin"

    def test_weighted_round_robin_value(self):
        assert LoadBalancingAlgorithm.WEIGHTED_ROUND_ROBIN.value == "weighted_round_robin"

    def test_least_connections_value(self):
        assert LoadBalancingAlgorithm.LEAST_CONNECTIONS.value == "least_connections"

    def test_least_response_time_value(self):
        assert LoadBalancingAlgorithm.LEAST_RESPONSE_TIME.value == "least_response_time"

    def test_ip_hash_value(self):
        assert LoadBalancingAlgorithm.IP_HASH.value == "ip_hash"

    def test_random_value(self):
        assert LoadBalancingAlgorithm.RANDOM.value == "random"

    def test_health_aware_value(self):
        assert LoadBalancingAlgorithm.HEALTH_AWARE.value == "health_aware"

    def test_enum_member_count(self):
        assert len(LoadBalancingAlgorithm) == 7


# ===========================================================================
# ServiceStatus enum
# ===========================================================================


class TestServiceStatusEnum:
    def test_healthy_value(self):
        assert ServiceStatus.HEALTHY.value == "healthy"

    def test_unhealthy_value(self):
        assert ServiceStatus.UNHEALTHY.value == "unhealthy"

    def test_draining_value(self):
        assert ServiceStatus.DRAINING.value == "draining"

    def test_maintenance_value(self):
        assert ServiceStatus.MAINTENANCE.value == "maintenance"

    def test_enum_member_count(self):
        assert len(ServiceStatus) == 4


# ===========================================================================
# ServiceInstance dataclass
# ===========================================================================


class TestServiceInstancePostInit:
    def test_last_health_check_set_when_none(self):
        inst = make_instance(last_health_check=None)
        assert inst.last_health_check is not None

    def test_metadata_set_to_empty_dict_when_none(self):
        inst = make_instance(metadata=None)
        assert inst.metadata == {}

    def test_explicit_metadata_preserved(self):
        inst = make_instance(metadata={"zone": "eu-west"})
        assert inst.metadata["zone"] == "eu-west"

    def test_failure_count_field_absent_does_not_exist(self):
        # total_failures defaults to 0, not a 'failure_count' field
        inst = make_instance()
        assert inst.total_failures == 0

    def test_current_connections_default_zero(self):
        inst = make_instance()
        assert inst.current_connections == 0

    def test_total_requests_default_zero(self):
        inst = make_instance()
        assert inst.total_requests == 0

    def test_weight_default_one(self):
        inst = make_instance()
        assert inst.weight == 1

    def test_status_default_healthy(self):
        inst = make_instance()
        assert inst.status == ServiceStatus.HEALTHY

    def test_avg_response_time_default_zero(self):
        inst = make_instance()
        assert inst.avg_response_time == 0.0


class TestServiceInstanceUrl:
    def test_url_format(self):
        inst = make_instance(host="10.0.0.5", port=9000)
        assert inst.url == "http://10.0.0.5:9000"

    def test_url_localhost(self):
        inst = make_instance(host="localhost", port=8080)
        assert inst.url == "http://localhost:8080"

    def test_url_contains_port(self):
        inst = make_instance(host="example.com", port=443)
        assert "443" in inst.url

    def test_url_contains_host(self):
        inst = make_instance(host="myhost", port=1234)
        assert "myhost" in inst.url


class TestServiceInstanceFailureRate:
    def test_zero_when_no_requests(self):
        inst = make_instance()
        assert inst.failure_rate == 0.0

    def test_zero_when_all_succeed(self):
        inst = make_instance(total_requests=100, total_failures=0)
        assert inst.failure_rate == 0.0

    def test_fifty_percent(self):
        inst = make_instance(total_requests=50, total_failures=50)
        assert abs(inst.failure_rate - 50.0) < 1e-9

    def test_hundred_percent_only_failures(self):
        inst = make_instance(total_requests=0, total_failures=10)
        assert abs(inst.failure_rate - 100.0) < 1e-9

    def test_partial_failure_rate(self):
        inst = make_instance(total_requests=90, total_failures=10)
        assert abs(inst.failure_rate - 10.0) < 1e-6


class TestServiceInstanceLoadScore:
    def test_zero_when_all_zero(self):
        inst = make_instance()
        assert inst.load_score == 0.0

    def test_connection_component(self):
        # 3 connections * 10 = 30
        inst = make_instance(current_connections=3)
        assert abs(inst.load_score - 30.0) < 1e-9

    def test_response_time_component(self):
        # avg_response_time=500 / 100 = 5.0
        inst = make_instance(avg_response_time=500.0)
        assert abs(inst.load_score - 5.0) < 1e-9

    def test_combined_score(self):
        # connections=2→20, response=100ms→1.0, no failures→0 → total=21.0
        inst = make_instance(current_connections=2, avg_response_time=100.0)
        assert abs(inst.load_score - 21.0) < 1e-9


# ===========================================================================
# HealthCheckConfig defaults
# ===========================================================================


class TestHealthCheckConfigDefaults:
    def setup_method(self):
        self.cfg = HealthCheckConfig()

    def test_interval_default(self):
        assert self.cfg.interval == 30

    def test_timeout_default(self):
        assert self.cfg.timeout == 5

    def test_unhealthy_threshold_default(self):
        assert self.cfg.unhealthy_threshold == 3

    def test_healthy_threshold_default(self):
        assert self.cfg.healthy_threshold == 2

    def test_endpoint_default(self):
        assert self.cfg.endpoint == "/health"

    def test_expected_status_default(self):
        assert self.cfg.expected_status == 200


# ===========================================================================
# CircuitBreakerConfig defaults
# ===========================================================================


class TestCircuitBreakerConfigDefaults:
    def setup_method(self):
        self.cfg = CircuitBreakerConfig()

    def test_failure_threshold_default(self):
        assert self.cfg.failure_threshold == 5

    def test_recovery_timeout_default(self):
        assert self.cfg.recovery_timeout == 60

    def test_half_open_max_calls_default(self):
        assert self.cfg.half_open_max_calls == 3


# ===========================================================================
# CircuitBreaker
# ===========================================================================


class TestCircuitBreakerInit:
    def setup_method(self):
        self.cb = CircuitBreaker("svc-1", CircuitBreakerConfig())

    def test_state_starts_closed(self):
        assert self.cb.state == "CLOSED"

    def test_failure_count_starts_zero(self):
        assert self.cb.failure_count == 0

    def test_last_failure_time_starts_none(self):
        assert self.cb.last_failure_time is None

    def test_half_open_calls_starts_zero(self):
        assert self.cb.half_open_calls == 0

    def test_service_id_stored(self):
        assert self.cb.service_id == "svc-1"

    def test_config_stored(self):
        cfg = CircuitBreakerConfig(failure_threshold=7)
        cb = CircuitBreaker("s", cfg)
        assert cb.config.failure_threshold == 7


class TestCircuitBreakerCanExecute:
    def test_closed_state_returns_true(self):
        cb = CircuitBreaker("s", CircuitBreakerConfig())
        assert cb.can_execute() is True

    def test_open_blocks_when_within_timeout(self):
        cb = CircuitBreaker("s", CircuitBreakerConfig(recovery_timeout=9999))
        cb.state = "OPEN"
        cb.last_failure_time = time.time()
        assert cb.can_execute() is False

    def test_open_transitions_to_half_open_after_timeout(self):
        cb = CircuitBreaker("s", CircuitBreakerConfig(recovery_timeout=0))
        cb.state = "OPEN"
        cb.last_failure_time = time.time() - 100
        result = cb.can_execute()
        assert result is True
        assert cb.state == "HALF_OPEN"

    def test_half_open_allows_below_max(self):
        cb = CircuitBreaker("s", CircuitBreakerConfig(half_open_max_calls=3))
        cb.state = "HALF_OPEN"
        cb.half_open_calls = 2
        assert cb.can_execute() is True

    def test_half_open_blocks_at_max(self):
        cb = CircuitBreaker("s", CircuitBreakerConfig(half_open_max_calls=3))
        cb.state = "HALF_OPEN"
        cb.half_open_calls = 3
        assert cb.can_execute() is False


class TestCircuitBreakerRecordSuccess:
    def test_closed_decrements_failure_count(self):
        cb = CircuitBreaker("s", CircuitBreakerConfig())
        cb.failure_count = 2
        cb.record_success()
        assert cb.failure_count == 1

    def test_closed_failure_count_not_below_zero(self):
        cb = CircuitBreaker("s", CircuitBreakerConfig())
        cb.failure_count = 0
        cb.record_success()
        assert cb.failure_count == 0

    def test_half_open_increments_half_open_calls(self):
        cb = CircuitBreaker("s", CircuitBreakerConfig(half_open_max_calls=5))
        cb.state = "HALF_OPEN"
        cb.half_open_calls = 0
        cb.record_success()
        assert cb.half_open_calls == 1

    def test_half_open_closes_at_max(self):
        cb = CircuitBreaker("s", CircuitBreakerConfig(half_open_max_calls=3))
        cb.state = "HALF_OPEN"
        cb.half_open_calls = 2
        cb.record_success()
        assert cb.state == "CLOSED"
        assert cb.failure_count == 0

    def test_half_open_stays_half_open_below_max(self):
        cb = CircuitBreaker("s", CircuitBreakerConfig(half_open_max_calls=3))
        cb.state = "HALF_OPEN"
        cb.half_open_calls = 1
        cb.record_success()
        assert cb.state == "HALF_OPEN"


class TestCircuitBreakerRecordFailure:
    def test_increments_failure_count(self):
        cb = CircuitBreaker("s", CircuitBreakerConfig())
        cb.record_failure()
        assert cb.failure_count == 1

    def test_sets_last_failure_time(self):
        cb = CircuitBreaker("s", CircuitBreakerConfig())
        cb.record_failure()
        assert cb.last_failure_time is not None

    def test_opens_at_threshold(self):
        cb = CircuitBreaker("s", CircuitBreakerConfig(failure_threshold=3))
        for _ in range(3):
            cb.record_failure()
        assert cb.state == "OPEN"

    def test_stays_closed_below_threshold(self):
        cb = CircuitBreaker("s", CircuitBreakerConfig(failure_threshold=5))
        for _ in range(4):
            cb.record_failure()
        assert cb.state == "CLOSED"

    def test_half_open_transitions_to_open(self):
        cb = CircuitBreaker("s", CircuitBreakerConfig())
        cb.state = "HALF_OPEN"
        cb.record_failure()
        assert cb.state == "OPEN"


# ===========================================================================
# LoadBalancer.__init__
# ===========================================================================


class TestLoadBalancerInit:
    def setup_method(self):
        self.lb = make_lb()

    def test_service_name_stored(self):
        assert self.lb.service_name == "svc"

    def test_algorithm_stored(self):
        assert self.lb.algorithm == LoadBalancingAlgorithm.ROUND_ROBIN

    def test_service_instances_empty(self):
        assert self.lb.services == {}

    def test_circuit_breakers_empty(self):
        assert self.lb.circuit_breakers == {}

    def test_round_robin_index_starts_zero(self):
        assert self.lb.round_robin_index == 0

    def test_metrics_total_requests_zero(self):
        assert self.lb.metrics["total_requests"] == 0

    def test_metrics_successful_requests_zero(self):
        assert self.lb.metrics["successful_requests"] == 0

    def test_metrics_failed_requests_zero(self):
        assert self.lb.metrics["failed_requests"] == 0

    def test_metrics_avg_response_time_zero(self):
        assert self.lb.metrics["avg_response_time"] == 0.0

    def test_health_check_config_defaults(self):
        lb = LoadBalancer("test_svc")
        assert lb.health_check_config is not None
        assert lb.health_check_config.interval == 30

    def test_custom_health_check_config(self):
        cfg = HealthCheckConfig(interval=60)
        lb = LoadBalancer("test_svc", health_check_config=cfg)
        assert lb.health_check_config.interval == 60


# ===========================================================================
# LoadBalancer.register_service
# ===========================================================================


class TestLoadBalancerRegisterService:
    def setup_method(self):
        self.lb = make_lb()

    def test_registers_instance_in_services(self):
        inst = make_instance(id_="x1")
        self.lb.register_service(inst)
        assert "x1" in self.lb.services

    def test_creates_circuit_breaker_for_instance(self):
        inst = make_instance(id_="x2")
        self.lb.register_service(inst)
        assert "x2" in self.lb.circuit_breakers

    def test_circuit_breaker_is_closed_initially(self):
        inst = make_instance(id_="x3")
        self.lb.register_service(inst)
        assert self.lb.circuit_breakers["x3"].state == "CLOSED"

    def test_stores_correct_instance_object(self):
        inst = make_instance(id_="x4")
        self.lb.register_service(inst)
        assert self.lb.services["x4"] is inst

    def test_registering_multiple_instances(self):
        for i in range(3):
            self.lb.register_service(make_instance(id_=f"inst-{i}", port=8000 + i))
        assert len(self.lb.services) == 3
        assert len(self.lb.circuit_breakers) == 3


# ===========================================================================
# LoadBalancer.unregister_service
# ===========================================================================


class TestLoadBalancerUnregisterService:
    def setup_method(self):
        self.lb = make_lb()
        self.inst = make_instance(id_="u1")
        self.lb.register_service(self.inst)

    def test_removes_instance_from_services(self):
        self.lb.unregister_service("u1")
        assert "u1" not in self.lb.services

    def test_removes_circuit_breaker(self):
        self.lb.unregister_service("u1")
        assert "u1" not in self.lb.circuit_breakers

    def test_unregister_nonexistent_id_does_not_raise(self):
        self.lb.unregister_service("nonexistent-id")  # should not raise

    def test_other_instances_unaffected(self):
        other = make_instance(id_="u2", port=8002)
        self.lb.register_service(other)
        self.lb.unregister_service("u1")
        assert "u2" in self.lb.services


# ===========================================================================
# LoadBalancer.get_healthy_services
# ===========================================================================


class TestLoadBalancerGetHealthyServices:
    def setup_method(self):
        self.lb = make_lb()

    def test_returns_only_healthy_instances(self):
        healthy = make_instance(id_="h1", port=8001, status=ServiceStatus.HEALTHY)
        unhealthy = make_instance(id_="u1", port=8002, status=ServiceStatus.UNHEALTHY)
        self.lb.register_service(healthy)
        self.lb.register_service(unhealthy)
        result = self.lb.get_healthy_services()
        ids = [s.id for s in result]
        assert "h1" in ids
        assert "u1" not in ids

    def test_empty_when_no_services(self):
        assert self.lb.get_healthy_services() == []

    def test_empty_when_all_unhealthy(self):
        for i in range(3):
            inst = make_instance(id_=f"u{i}", port=8000 + i, status=ServiceStatus.UNHEALTHY)
            self.lb.register_service(inst)
        assert self.lb.get_healthy_services() == []

    def test_excludes_instances_with_open_circuit_breaker(self):
        inst = make_instance(id_="cb1", port=8001, status=ServiceStatus.HEALTHY)
        self.lb.register_service(inst)
        # Force circuit breaker open and block execution
        cb = self.lb.circuit_breakers["cb1"]
        cb.state = "OPEN"
        cb.last_failure_time = time.time()
        cb.config = CircuitBreakerConfig(recovery_timeout=9999)
        result = self.lb.get_healthy_services()
        assert len(result) == 0

    def test_includes_draining_status_excluded(self):
        draining = make_instance(id_="d1", port=8001, status=ServiceStatus.DRAINING)
        self.lb.register_service(draining)
        result = self.lb.get_healthy_services()
        assert len(result) == 0

    def test_returns_all_healthy(self):
        for i in range(5):
            self.lb.register_service(make_instance(id_=f"h{i}", port=8000 + i))
        result = self.lb.get_healthy_services()
        assert len(result) == 5


# ===========================================================================
# LoadBalancer._select_service — ROUND_ROBIN
# ===========================================================================


class TestSelectServiceRoundRobin:
    def setup_method(self):
        self.lb = make_lb(algorithm=LoadBalancingAlgorithm.ROUND_ROBIN)
        self.instances = [
            make_instance(id_=f"rr{i}", port=8000 + i) for i in range(3)
        ]

    def test_first_call_returns_first_instance(self):
        result = self.lb._select_service(self.instances, None)
        assert result is self.instances[0]

    def test_second_call_returns_second_instance(self):
        self.lb._select_service(self.instances, None)
        result = self.lb._select_service(self.instances, None)
        assert result is self.instances[1]

    def test_cycles_back_to_start(self):
        for _ in range(3):
            self.lb._select_service(self.instances, None)
        result = self.lb._select_service(self.instances, None)
        assert result is self.instances[0]

    def test_increments_round_robin_index(self):
        self.lb._select_service(self.instances, None)
        assert self.lb.round_robin_index == 1

    def test_single_instance_always_returned(self):
        single = [self.instances[0]]
        for _ in range(5):
            assert self.lb._select_service(single, None) is single[0]


# ===========================================================================
# LoadBalancer._select_service — LEAST_CONNECTIONS
# ===========================================================================


class TestSelectServiceLeastConnections:
    def setup_method(self):
        self.lb = make_lb(algorithm=LoadBalancingAlgorithm.LEAST_CONNECTIONS)

    def test_selects_instance_with_fewer_connections(self):
        inst_busy = make_instance(id_="lc1", port=8001, current_connections=10)
        inst_free = make_instance(id_="lc2", port=8002, current_connections=1)
        result = self.lb._select_service([inst_busy, inst_free], None)
        assert result is inst_free

    def test_returns_none_for_empty_list(self):
        result = self.lb._select_service([], None)
        assert result is None

    def test_returns_only_instance_when_one(self):
        inst = make_instance(id_="lc3", port=8001, current_connections=100)
        result = self.lb._select_service([inst], None)
        assert result is inst

    def test_selects_zero_connections_over_one(self):
        inst_zero = make_instance(id_="lc4", port=8001, current_connections=0)
        inst_one = make_instance(id_="lc5", port=8002, current_connections=1)
        result = self.lb._select_service([inst_one, inst_zero], None)
        assert result is inst_zero


# ===========================================================================
# LoadBalancer._select_service — LEAST_RESPONSE_TIME
# ===========================================================================


class TestSelectServiceLeastResponseTime:
    def setup_method(self):
        self.lb = make_lb(algorithm=LoadBalancingAlgorithm.LEAST_RESPONSE_TIME)

    def test_selects_instance_with_lower_response_time(self):
        fast = make_instance(id_="rt1", port=8001, avg_response_time=50.0)
        slow = make_instance(id_="rt2", port=8002, avg_response_time=500.0)
        result = self.lb._select_service([slow, fast], None)
        assert result is fast


# ===========================================================================
# LoadBalancer._select_service — HEALTH_AWARE
# ===========================================================================


class TestSelectServiceHealthAware:
    def setup_method(self):
        self.lb = make_lb(algorithm=LoadBalancingAlgorithm.HEALTH_AWARE)

    def test_selects_instance_with_lowest_load_score(self):
        low_load = make_instance(id_="ha1", port=8001, current_connections=0)
        high_load = make_instance(id_="ha2", port=8002, current_connections=5)
        result = self.lb._select_service([high_load, low_load], None)
        assert result is low_load


# ===========================================================================
# LoadBalancer._select_service — WEIGHTED_ROUND_ROBIN
# ===========================================================================


class TestSelectServiceWeightedRoundRobin:
    def setup_method(self):
        self.lb = make_lb(algorithm=LoadBalancingAlgorithm.WEIGHTED_ROUND_ROBIN)

    def test_higher_weight_appears_more_often(self):
        light = make_instance(id_="wrr1", port=8001, weight=1)
        heavy = make_instance(id_="wrr2", port=8002, weight=3)
        services = [light, heavy]
        selections = [self.lb._select_service(services, None) for _ in range(4)]
        heavy_count = sum(1 for s in selections if s is heavy)
        light_count = sum(1 for s in selections if s is light)
        assert heavy_count > light_count


# ===========================================================================
# LoadBalancer._select_service — IP_HASH
# ===========================================================================


class TestSelectServiceIpHash:
    def setup_method(self):
        self.lb = make_lb(algorithm=LoadBalancingAlgorithm.IP_HASH)
        self.instances = [make_instance(id_=f"ip{i}", port=8000 + i) for i in range(3)]

    def test_same_ip_routes_to_same_instance(self):
        req = {"client_ip": "192.168.1.10"}
        first = self.lb._select_service(self.instances, req)
        second = self.lb._select_service(self.instances, req)
        assert first is second

    def test_no_client_ip_returns_some_instance(self):
        result = self.lb._select_service(self.instances, {})
        assert result in self.instances


# ===========================================================================
# LoadBalancer._update_global_metrics
# ===========================================================================


class TestUpdateGlobalMetrics:
    def setup_method(self):
        self.lb = make_lb()

    def test_updates_avg_response_time_after_first_request(self):
        self.lb.metrics["successful_requests"] = 1
        self.lb._update_global_metrics(200.0)
        assert self.lb.metrics["avg_response_time"] == 200.0

    def test_updates_avg_response_time_incrementally(self):
        self.lb.metrics["successful_requests"] = 1
        self.lb._update_global_metrics(100.0)
        self.lb.metrics["successful_requests"] = 2
        self.lb._update_global_metrics(200.0)
        # After 2 requests: avg = (100*(2-1) + 200) / 2 = 150
        assert abs(self.lb.metrics["avg_response_time"] - 150.0) < 1e-6

    def test_no_update_when_no_requests(self):
        # total_requests = 0 → avg unchanged
        self.lb._update_global_metrics(500.0)
        assert self.lb.metrics["avg_response_time"] == 0.0

    def test_initializes_minute_tracking_attributes(self):
        self.lb.metrics["successful_requests"] = 1
        self.lb._update_global_metrics(100.0)
        assert hasattr(self.lb, "_last_minute")
        assert hasattr(self.lb, "_current_minute_requests")

    def test_increments_current_minute_requests(self):
        self.lb.metrics["successful_requests"] = 1
        self.lb._update_global_metrics(100.0)
        first = self.lb._current_minute_requests
        self.lb.metrics["successful_requests"] = 2
        self.lb._update_global_metrics(100.0)
        assert self.lb._current_minute_requests == first + 1


# ===========================================================================
# LoadBalancer.get_load_balancer_stats
# ===========================================================================


class TestGetLoadBalancerStats:
    def setup_method(self):
        self.lb = make_lb(name="stats_svc")

    def test_returns_dict(self):
        stats = self.lb.get_load_balancer_stats()
        assert isinstance(stats, dict)

    def test_service_name_in_stats(self):
        stats = self.lb.get_load_balancer_stats()
        assert stats["service_name"] == "stats_svc"

    def test_algorithm_in_stats(self):
        stats = self.lb.get_load_balancer_stats()
        assert stats["algorithm"] == LoadBalancingAlgorithm.ROUND_ROBIN.value

    def test_service_instances_section(self):
        stats = self.lb.get_load_balancer_stats()
        assert "service_instances" in stats
        assert stats["service_instances"]["total"] == 0

    def test_request_metrics_section(self):
        stats = self.lb.get_load_balancer_stats()
        assert "request_metrics" in stats

    def test_instances_section_populated(self):
        inst = make_instance(id_="stat1", port=8001)
        self.lb.register_service(inst)
        stats = self.lb.get_load_balancer_stats()
        assert len(stats["instances"]) == 1
        assert stats["instances"][0]["id"] == "stat1"


# ===========================================================================
# LoadBalancer.route_request (async)
# ===========================================================================


class TestRouteRequest:
    async def test_returns_none_when_no_services(self):
        lb = make_lb()
        result = await lb.route_request({})
        assert result is None

    async def test_returns_service_instance(self):
        lb = make_lb()
        inst = make_instance(id_="r1", port=8001)
        lb.register_service(inst)
        result = await lb.route_request({})
        assert result is inst

    async def test_increments_total_requests(self):
        lb = make_lb()
        inst = make_instance(id_="r2", port=8001)
        lb.register_service(inst)
        await lb.route_request({})
        assert lb.metrics["total_requests"] == 1

    async def test_increments_current_connections(self):
        lb = make_lb()
        inst = make_instance(id_="r3", port=8001)
        lb.register_service(inst)
        await lb.route_request({})
        assert inst.current_connections == 1


# ===========================================================================
# LoadBalancer.record_response (async)
# ===========================================================================


class TestRecordResponse:
    async def test_successful_response_updates_total_requests(self):
        lb = make_lb()
        inst = make_instance(id_="rec1", port=8001, current_connections=1)
        lb.register_service(inst)
        await lb.record_response("rec1", 100.0, success=True)
        assert inst.total_requests == 1

    async def test_failed_response_updates_total_failures(self):
        lb = make_lb()
        inst = make_instance(id_="rec2", port=8001, current_connections=1)
        lb.register_service(inst)
        await lb.record_response("rec2", 100.0, success=False)
        assert inst.total_failures == 1

    async def test_decrements_current_connections(self):
        lb = make_lb()
        inst = make_instance(id_="rec3", port=8001, current_connections=3)
        lb.register_service(inst)
        await lb.record_response("rec3", 50.0, success=True)
        assert inst.current_connections == 2

    async def test_nonexistent_service_id_is_no_op(self):
        lb = make_lb()
        await lb.record_response("nonexistent", 100.0, success=True)  # no exception

    async def test_updates_avg_response_time(self):
        lb = make_lb()
        inst = make_instance(id_="rec4", port=8001, current_connections=1)
        lb.register_service(inst)
        await lb.record_response("rec4", 200.0, success=True)
        assert inst.avg_response_time > 0


# ===========================================================================
# LoadBalancer.should_scale_up / should_scale_down
# ===========================================================================


class TestShouldScaleUp:
    def test_returns_true_when_no_healthy_services(self):
        lb = make_lb()
        assert lb.should_scale_up() is True

    def test_returns_false_when_all_instances_low_load(self):
        lb = make_lb()
        for i in range(3):
            lb.register_service(make_instance(
                id_=f"up{i}", port=8000 + i,
                current_connections=0, avg_response_time=10.0
            ))
        assert lb.should_scale_up() is False

    def test_returns_true_when_majority_high_load(self):
        lb = make_lb()
        for i in range(3):
            lb.register_service(make_instance(
                id_=f"up{i}", port=8000 + i,
                current_connections=20, avg_response_time=2000.0
            ))
        assert lb.should_scale_up() is True


class TestShouldScaleDown:
    def test_returns_false_when_one_or_fewer_instances(self):
        lb = make_lb()
        lb.register_service(make_instance(id_="sd1", port=8001))
        assert lb.should_scale_down() is False

    def test_returns_false_when_no_instances(self):
        lb = make_lb()
        assert lb.should_scale_down() is False

    def test_returns_true_when_all_instances_idle(self):
        lb = make_lb()
        for i in range(3):
            lb.register_service(make_instance(
                id_=f"sd{i}", port=8000 + i,
                current_connections=0, avg_response_time=50.0,
                metadata={"cpu_percent": 5}
            ))
        assert lb.should_scale_down() is True
