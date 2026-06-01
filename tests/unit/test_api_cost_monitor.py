"""Unit tests for APICostMonitor — cost calculation, rate limiting, circuit breaker."""

from __future__ import annotations

import sys
import time
from collections import deque
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from youtube_extension.backend.services.api_cost_monitor import (
    APICostMonitor,
    APIUsageRecord,
    RateLimitTracker,
)


# ===========================================================================
# Fixtures
# ===========================================================================


@pytest.fixture
def monitor(tmp_path):
    """APICostMonitor backed by an in-memory SQLite database."""
    return APICostMonitor(db_path=":memory:")


# ===========================================================================
# RateLimitTracker
# ===========================================================================


class TestRateLimitTracker:
    def test_default_requests_deque_created(self):
        t = RateLimitTracker(max_requests=10, window_seconds=60)
        assert isinstance(t.requests, deque)

    def test_provided_requests_deque_preserved(self):
        d = deque([1.0, 2.0])
        t = RateLimitTracker(max_requests=10, window_seconds=60, requests=d)
        assert t.requests is d


# ===========================================================================
# APICostMonitor — calculate_cost
# ===========================================================================


class TestCalculateCost:
    def test_anthropic_opus_cost(self, monitor):
        cost = monitor.calculate_cost("anthropic", "claude-opus-4-8", input_tokens=1000, output_tokens=1000)
        # 1000 input @ $0.005/1K + 1000 output @ $0.025/1K
        assert pytest.approx(cost, rel=1e-6) == 0.005 + 0.025

    def test_anthropic_haiku_cost(self, monitor):
        cost = monitor.calculate_cost("anthropic", "claude-haiku-4-5", input_tokens=2000, output_tokens=500)
        expected = (2000 / 1000) * 0.001 + (500 / 1000) * 0.005
        assert pytest.approx(cost, rel=1e-6) == expected

    def test_anthropic_sonnet_cost(self, monitor):
        cost = monitor.calculate_cost("anthropic", "claude-sonnet-4-6", input_tokens=1000, output_tokens=0)
        assert pytest.approx(cost, rel=1e-6) == 0.003

    def test_openai_gpt4o_cost(self, monitor):
        cost = monitor.calculate_cost("openai", "gpt-4o", input_tokens=1000, output_tokens=1000)
        expected = (1000 / 1000) * 0.0025 + (1000 / 1000) * 0.01
        assert pytest.approx(cost, rel=1e-6) == expected

    def test_youtube_quota_cost(self, monitor):
        cost = monitor.calculate_cost("youtube", "search", input_tokens=100)
        assert pytest.approx(cost, rel=1e-6) == 100 * 0.0001

    def test_unknown_service_returns_zero(self, monitor):
        assert monitor.calculate_cost("nonexistent", "model", 1000) == 0.0

    def test_unknown_model_falls_back_to_first_model(self, monitor):
        cost = monitor.calculate_cost("anthropic", "unknown-model", input_tokens=1000, output_tokens=0)
        assert cost > 0.0

    def test_zero_tokens_returns_zero_cost(self, monitor):
        cost = monitor.calculate_cost("anthropic", "claude-opus-4-8", input_tokens=0, output_tokens=0)
        assert cost == 0.0

    def test_output_tokens_default_zero(self, monitor):
        cost_with_default = monitor.calculate_cost("anthropic", "claude-opus-4-8", input_tokens=1000)
        cost_explicit_zero = monitor.calculate_cost("anthropic", "claude-opus-4-8", input_tokens=1000, output_tokens=0)
        assert pytest.approx(cost_with_default) == cost_explicit_zero

    def test_historical_model_still_priced(self, monitor):
        cost = monitor.calculate_cost("anthropic", "claude-3-5-sonnet-20241022", input_tokens=1000, output_tokens=0)
        assert pytest.approx(cost, rel=1e-6) == 0.003


# ===========================================================================
# APICostMonitor — check_rate_limit
# ===========================================================================


class TestCheckRateLimit:
    def test_unknown_service_always_allowed(self, monitor):
        allowed, wait = monitor.check_rate_limit("unknown_service")
        assert allowed is True
        assert wait == 0

    def test_first_request_allowed(self, monitor):
        allowed, wait = monitor.check_rate_limit("anthropic")
        assert allowed is True
        assert wait == 0

    def test_requests_accumulate(self, monitor):
        for _ in range(5):
            allowed, _ = monitor.check_rate_limit("anthropic")
            assert allowed is True

    def test_limit_exceeded_returns_wait(self, monitor):
        limiter = monitor.rate_limiters["anthropic"]
        # Fill up the window with fake timestamps just within range
        now = time.time()
        limiter.requests = deque([now] * limiter.max_requests)
        allowed, wait = monitor.check_rate_limit("anthropic")
        assert allowed is False
        assert wait > 0

    def test_old_requests_expire(self, monitor):
        limiter = monitor.rate_limiters["anthropic"]
        # Fill with timestamps well outside the window
        old_time = time.time() - limiter.window_seconds - 10
        limiter.requests = deque([old_time] * limiter.max_requests)
        allowed, wait = monitor.check_rate_limit("anthropic")
        assert allowed is True
        assert wait == 0


# ===========================================================================
# APICostMonitor — check_circuit_breaker
# ===========================================================================


class TestCheckCircuitBreaker:
    def test_new_service_not_open(self, monitor):
        assert monitor.check_circuit_breaker("new_service") is False

    def test_open_breaker_blocks(self, monitor):
        monitor.circuit_breakers["anthropic"]["open"] = True
        monitor.circuit_breakers["anthropic"]["last_failure"] = time.time()
        assert monitor.check_circuit_breaker("anthropic") is True

    def test_breaker_resets_after_cooldown(self, monitor):
        monitor.circuit_breakers["anthropic"]["open"] = True
        # Set last_failure well beyond the 300s cooldown
        monitor.circuit_breakers["anthropic"]["last_failure"] = time.time() - 400
        result = monitor.check_circuit_breaker("anthropic")
        assert result is False
        assert monitor.circuit_breakers["anthropic"]["open"] is False
        assert monitor.circuit_breakers["anthropic"]["failures"] == 0

    def test_closed_breaker_returns_false(self, monitor):
        monitor.circuit_breakers["google"]["open"] = False
        assert monitor.check_circuit_breaker("google") is False


# ===========================================================================
# APICostMonitor — COST_MODELS structure
# ===========================================================================


class TestCostModelsStructure:
    def test_all_expected_providers_present(self, monitor):
        for provider in ("openai", "anthropic", "google", "youtube"):
            assert provider in monitor.COST_MODELS

    def test_current_anthropic_models_present(self, monitor):
        models = monitor.COST_MODELS["anthropic"]
        for model in ("claude-opus-4-8", "claude-opus-4-7", "claude-sonnet-4-6", "claude-haiku-4-5"):
            assert model in models, f"{model} missing from COST_MODELS"

    def test_anthropic_model_has_input_output_keys(self, monitor):
        for model, pricing in monitor.COST_MODELS["anthropic"].items():
            assert "input" in pricing, f"{model} missing 'input'"
            assert "output" in pricing, f"{model} missing 'output'"

    def test_output_cost_ge_input_cost_for_anthropic(self, monitor):
        for model, pricing in monitor.COST_MODELS["anthropic"].items():
            assert pricing["output"] >= pricing["input"], (
                f"{model}: output ${pricing['output']} < input ${pricing['input']}"
            )
