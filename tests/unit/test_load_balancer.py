"""Unit tests for load_balancer module: enums, ServiceInstance, configs, CircuitBreaker."""

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
    LoadBalancingAlgorithm,
    ServiceInstance,
    ServiceStatus,
)

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

    def test_has_seven_members(self):
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

    def test_has_four_members(self):
        assert len(ServiceStatus) == 4


# ===========================================================================
# ServiceInstance — __post_init__ and defaults
# ===========================================================================


class TestServiceInstancePostInit:
    @pytest.fixture
    def inst(self):
        return ServiceInstance(id="s1", host="10.0.0.1", port=8080)

    def test_metadata_none_replaced_with_dict(self):
        inst = ServiceInstance(id="s1", host="h", port=8080, metadata=None)
        assert inst.metadata == {}

    def test_last_health_check_none_replaced(self):
        inst = ServiceInstance(id="s1", host="h", port=8080, last_health_check=None)
        assert inst.last_health_check is not None

    def test_explicit_metadata_preserved(self):
        inst = ServiceInstance(id="s1", host="h", port=8080, metadata={"region": "us-east"})
        assert inst.metadata["region"] == "us-east"

    def test_weight_default_one(self, inst):
        assert inst.weight == 1

    def test_status_default_healthy(self, inst):
        assert inst.status == ServiceStatus.HEALTHY

    def test_current_connections_default_zero(self, inst):
        assert inst.current_connections == 0

    def test_total_requests_default_zero(self, inst):
        assert inst.total_requests == 0

    def test_total_failures_default_zero(self, inst):
        assert inst.total_failures == 0

    def test_avg_response_time_default_zero(self, inst):
        assert inst.avg_response_time == 0.0


# ===========================================================================
# ServiceInstance.url property
# ===========================================================================


class TestServiceInstanceUrl:
    def test_url_format(self):
        inst = ServiceInstance(id="s1", host="10.0.0.5", port=9000)
        assert inst.url == "http://10.0.0.5:9000"

    def test_url_localhost(self):
        inst = ServiceInstance(id="s2", host="localhost", port=8080)
        assert inst.url == "http://localhost:8080"

    def test_url_uses_actual_port(self):
        inst = ServiceInstance(id="s3", host="example.com", port=443)
        assert "443" in inst.url


# ===========================================================================
# ServiceInstance.failure_rate property
# ===========================================================================


class TestServiceInstanceFailureRate:
    def test_zero_when_no_requests(self):
        inst = ServiceInstance(id="s", host="h", port=8)
        assert inst.failure_rate == 0.0

    def test_zero_when_all_succeed(self):
        inst = ServiceInstance(id="s", host="h", port=8, total_requests=100, total_failures=0)
        assert inst.failure_rate == 0.0

    def test_fifty_percent_failure_rate(self):
        inst = ServiceInstance(id="s", host="h", port=8, total_requests=50, total_failures=50)
        assert abs(inst.failure_rate - 50.0) < 1e-9

    def test_hundred_percent_failure_rate(self):
        inst = ServiceInstance(id="s", host="h", port=8, total_requests=0, total_failures=10)
        assert abs(inst.failure_rate - 100.0) < 1e-9

    def test_small_failure_rate(self):
        inst = ServiceInstance(id="s", host="h", port=8, total_requests=99, total_failures=1)
        assert abs(inst.failure_rate - 1.0) < 1e-6


# ===========================================================================
# ServiceInstance.load_score property
# ===========================================================================


class TestServiceInstanceLoadScore:
    def test_all_zero_gives_zero(self):
        inst = ServiceInstance(id="s", host="h", port=8)
        assert inst.load_score == 0.0

    def test_connection_component(self):
        # connections=5, response=0, failure_rate=0 → 5*10 = 50
        inst = ServiceInstance(id="s", host="h", port=8, current_connections=5)
        assert abs(inst.load_score - 50.0) < 1e-9

    def test_response_time_component(self):
        # connections=0, avg_response_time=200, failure=0 → 200/100 = 2.0
        inst = ServiceInstance(id="s", host="h", port=8, avg_response_time=200.0)
        assert abs(inst.load_score - 2.0) < 1e-9

    def test_failure_rate_component(self):
        # connections=0, response=0, 10 failures / 10 total = 100% → 100*2 = 200
        inst = ServiceInstance(id="s", host="h", port=8, total_requests=0, total_failures=10)
        assert abs(inst.load_score - 200.0) < 1e-9

    def test_combined_score(self):
        # connections=2 → 20, response=100ms → 1.0, failures=0 → 0 → total=21.0
        inst = ServiceInstance(
            id="s", host="h", port=8,
            current_connections=2,
            avg_response_time=100.0,
        )
        assert abs(inst.load_score - 21.0) < 1e-9


# ===========================================================================
# HealthCheckConfig defaults
# ===========================================================================


class TestHealthCheckConfigDefaults:
    @pytest.fixture
    def cfg(self):
        return HealthCheckConfig()

    def test_interval_default(self, cfg):
        assert cfg.interval == 30

    def test_timeout_default(self, cfg):
        assert cfg.timeout == 5

    def test_unhealthy_threshold_default(self, cfg):
        assert cfg.unhealthy_threshold == 3

    def test_healthy_threshold_default(self, cfg):
        assert cfg.healthy_threshold == 2

    def test_endpoint_default(self, cfg):
        assert cfg.endpoint == "/health"

    def test_expected_status_default(self, cfg):
        assert cfg.expected_status == 200


# ===========================================================================
# CircuitBreakerConfig defaults
# ===========================================================================


class TestCircuitBreakerConfigDefaults:
    @pytest.fixture
    def cfg(self):
        return CircuitBreakerConfig()

    def test_failure_threshold_default(self, cfg):
        assert cfg.failure_threshold == 5

    def test_recovery_timeout_default(self, cfg):
        assert cfg.recovery_timeout == 60

    def test_half_open_max_calls_default(self, cfg):
        assert cfg.half_open_max_calls == 3


# ===========================================================================
# CircuitBreaker — initial state
# ===========================================================================


class TestCircuitBreakerInit:
    @pytest.fixture
    def cb(self):
        return CircuitBreaker("svc-1", CircuitBreakerConfig())

    def test_state_starts_closed(self, cb):
        assert cb.state == "CLOSED"

    def test_failure_count_starts_zero(self, cb):
        assert cb.failure_count == 0

    def test_last_failure_time_starts_none(self, cb):
        assert cb.last_failure_time is None

    def test_half_open_calls_starts_zero(self, cb):
        assert cb.half_open_calls == 0

    def test_service_id_stored(self, cb):
        assert cb.service_id == "svc-1"


# ===========================================================================
# CircuitBreaker.can_execute
# ===========================================================================


class TestCircuitBreakerCanExecute:
    def test_closed_allows_execution(self):
        cb = CircuitBreaker("s", CircuitBreakerConfig())
        assert cb.can_execute() is True

    def test_open_blocks_within_timeout(self):
        cb = CircuitBreaker("s", CircuitBreakerConfig(recovery_timeout=9999))
        cb.state = "OPEN"
        cb.last_failure_time = time.time()
        assert cb.can_execute() is False

    def test_open_transitions_to_half_open_after_timeout(self):
        cb = CircuitBreaker("s", CircuitBreakerConfig(recovery_timeout=0))
        cb.state = "OPEN"
        cb.last_failure_time = time.time() - 10  # expired
        result = cb.can_execute()
        assert result is True
        assert cb.state == "HALF_OPEN"

    def test_half_open_allows_when_below_max_calls(self):
        cb = CircuitBreaker("s", CircuitBreakerConfig(half_open_max_calls=3))
        cb.state = "HALF_OPEN"
        cb.half_open_calls = 2
        assert cb.can_execute() is True

    def test_half_open_blocks_at_max_calls(self):
        cb = CircuitBreaker("s", CircuitBreakerConfig(half_open_max_calls=3))
        cb.state = "HALF_OPEN"
        cb.half_open_calls = 3
        assert cb.can_execute() is False


# ===========================================================================
# CircuitBreaker.record_success
# ===========================================================================


class TestCircuitBreakerRecordSuccess:
    def test_closed_decrements_failure_count(self):
        cb = CircuitBreaker("s", CircuitBreakerConfig())
        cb.failure_count = 3
        cb.record_success()
        assert cb.failure_count == 2

    def test_closed_failure_count_not_below_zero(self):
        cb = CircuitBreaker("s", CircuitBreakerConfig())
        cb.failure_count = 0
        cb.record_success()
        assert cb.failure_count == 0

    def test_half_open_increments_calls(self):
        cb = CircuitBreaker("s", CircuitBreakerConfig(half_open_max_calls=5))
        cb.state = "HALF_OPEN"
        cb.half_open_calls = 0
        cb.record_success()
        assert cb.half_open_calls == 1

    def test_half_open_closes_at_max_calls(self):
        cb = CircuitBreaker("s", CircuitBreakerConfig(half_open_max_calls=3))
        cb.state = "HALF_OPEN"
        cb.half_open_calls = 2
        cb.record_success()  # now equals max → should close
        assert cb.state == "CLOSED"
        assert cb.failure_count == 0

    def test_half_open_not_closed_below_max(self):
        cb = CircuitBreaker("s", CircuitBreakerConfig(half_open_max_calls=3))
        cb.state = "HALF_OPEN"
        cb.half_open_calls = 1
        cb.record_success()
        assert cb.state == "HALF_OPEN"


# ===========================================================================
# CircuitBreaker.record_failure
# ===========================================================================


class TestCircuitBreakerRecordFailure:
    def test_increments_failure_count(self):
        cb = CircuitBreaker("s", CircuitBreakerConfig())
        cb.record_failure()
        assert cb.failure_count == 1

    def test_sets_last_failure_time(self):
        cb = CircuitBreaker("s", CircuitBreakerConfig())
        assert cb.last_failure_time is None
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
