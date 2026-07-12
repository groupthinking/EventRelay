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
    """APICostMonitor backed by a temporary file-based SQLite database."""
    return APICostMonitor(db_path=str(tmp_path / "test_monitor.db"))


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


# ===========================================================================
# APICostMonitor — record_api_failure / circuit breaker opening
# ===========================================================================


class TestRecordApiFailure:
    def test_failure_increments_count(self, monitor):
        monitor.record_api_failure("openai", "timeout")
        assert monitor.circuit_breakers["openai"]["failures"] == 1

    def test_multiple_failures_accumulate(self, monitor):
        for _ in range(3):
            monitor.record_api_failure("anthropic", "error")
        assert monitor.circuit_breakers["anthropic"]["failures"] == 3

    def test_breaker_opens_after_max_failures(self, monitor):
        for _ in range(monitor.max_failures):
            monitor.record_api_failure("google", "error")
        assert monitor.circuit_breakers["google"]["open"] is True

    def test_breaker_not_open_before_max_failures(self, monitor):
        for _ in range(monitor.max_failures - 1):
            monitor.record_api_failure("youtube", "error")
        assert monitor.circuit_breakers["youtube"]["open"] is False

    def test_last_failure_time_recorded(self, monitor):
        before = time.time()
        monitor.record_api_failure("openai", "error")
        assert monitor.circuit_breakers["openai"]["last_failure"] >= before


# ===========================================================================
# APICostMonitor — record_usage (async)
# ===========================================================================


class TestRecordUsage:
    async def test_returns_usage_record(self, monitor):
        record = await monitor.record_usage(
            service="anthropic",
            endpoint="/messages",
            tokens_used=500,
            model="claude-opus-4-8",
            output_tokens=100,
        )
        assert record is not None
        assert isinstance(record, __import__("youtube_extension.backend.services.api_cost_monitor", fromlist=["APIUsageRecord"]).APIUsageRecord)

    async def test_record_has_correct_service(self, monitor):
        record = await monitor.record_usage(service="openai", endpoint="/chat", tokens_used=100)
        assert record.service == "openai"

    async def test_record_cost_is_positive(self, monitor):
        record = await monitor.record_usage(
            service="anthropic", endpoint="/messages", tokens_used=1000,
            model="claude-opus-4-8", output_tokens=500
        )
        assert record.cost > 0

    async def test_session_costs_updated(self, monitor):
        await monitor.record_usage(service="google", endpoint="/generate", tokens_used=1000, model="gemini-1.5-pro")
        assert monitor.session_costs["google"] > 0

    async def test_session_requests_updated(self, monitor):
        await monitor.record_usage(service="anthropic", endpoint="/messages", tokens_used=100)
        assert monitor.session_requests["anthropic"] == 1

    async def test_disabled_tracking_returns_none(self, monitor):
        monitor.cost_tracking_enabled = False
        record = await monitor.record_usage(service="anthropic", endpoint="/messages", tokens_used=100)
        assert record is None

    async def test_usage_stored_in_db(self, monitor):
        await monitor.record_usage(
            service="openai", endpoint="/chat", tokens_used=200,
            model="gpt-4o", request_type="chat"
        )
        daily = await monitor.get_daily_cost()
        assert daily >= 0

    async def test_record_with_user_video_id(self, monitor):
        record = await monitor.record_usage(
            service="anthropic", endpoint="/messages", tokens_used=100,
            user_id="user123", video_id="vid456"
        )
        assert record.user_id == "user123"
        assert record.video_id == "vid456"

    async def test_record_failure_usage(self, monitor):
        record = await monitor.record_usage(
            service="openai", endpoint="/chat", tokens_used=0,
            success=False, error_message="rate limited"
        )
        assert record.success is False
        assert record.error_message == "rate limited"


# ===========================================================================
# APICostMonitor — get_daily_cost
# ===========================================================================


class TestGetDailyCost:
    async def test_returns_zero_for_empty_db(self, monitor):
        cost = await monitor.get_daily_cost()
        assert cost == 0.0

    async def test_returns_float(self, monitor):
        cost = await monitor.get_daily_cost()
        assert isinstance(cost, float)

    async def test_specific_date_returns_zero(self, monitor):
        cost = await monitor.get_daily_cost("2020-01-01")
        assert cost == 0.0

    async def test_after_record_usage_nonzero(self, monitor):
        await monitor.record_usage(
            service="anthropic", endpoint="/messages", tokens_used=10000,
            model="claude-opus-4-8", output_tokens=10000
        )
        cost = await monitor.get_daily_cost()
        assert cost > 0


# ===========================================================================
# APICostMonitor — get_usage_analytics
# ===========================================================================


class TestGetUsageAnalytics:
    async def test_returns_dict(self, monitor):
        result = await monitor.get_usage_analytics()
        assert isinstance(result, dict)

    async def test_has_period_key(self, monitor):
        result = await monitor.get_usage_analytics()
        assert "period" in result

    async def test_has_service_breakdown(self, monitor):
        result = await monitor.get_usage_analytics(days=7)
        assert "service_breakdown" in result

    async def test_has_daily_breakdown(self, monitor):
        result = await monitor.get_usage_analytics(days=7)
        assert "daily_breakdown" in result

    async def test_has_current_session(self, monitor):
        result = await monitor.get_usage_analytics()
        assert "current_session" in result

    async def test_has_budget_status(self, monitor):
        result = await monitor.get_usage_analytics()
        assert "budget_status" in result

    async def test_period_has_correct_days(self, monitor):
        result = await monitor.get_usage_analytics(days=14)
        assert result["period"]["days"] == 14

    async def test_session_reflects_usage(self, monitor):
        await monitor.record_usage(
            service="openai", endpoint="/chat", tokens_used=500,
            model="gpt-4o"
        )
        result = await monitor.get_usage_analytics()
        assert result["current_session"]["requests"].get("openai", 0) >= 1


# ===========================================================================
# APICostMonitor — optimize_api_usage
# ===========================================================================


class TestOptimizeApiUsage:
    async def test_returns_dict(self, monitor):
        result = await monitor.optimize_api_usage()
        assert isinstance(result, dict)

    async def test_has_recommendations_key(self, monitor):
        result = await monitor.optimize_api_usage()
        assert "recommendations" in result

    async def test_recommendations_is_list(self, monitor):
        result = await monitor.optimize_api_usage()
        assert isinstance(result["recommendations"], list)

    async def test_has_budget_utilization(self, monitor):
        result = await monitor.optimize_api_usage()
        assert "budget_utilization" in result

    async def test_has_top_cost_services(self, monitor):
        result = await monitor.optimize_api_usage()
        assert "top_cost_services" in result

    async def test_budget_utilization_is_string(self, monitor):
        result = await monitor.optimize_api_usage()
        assert isinstance(result["budget_utilization"], str)
        assert "%" in result["budget_utilization"]


# ===========================================================================
# APICostMonitor — get_current_quota_usage
# ===========================================================================


class TestGetCurrentQuotaUsage:
    def test_returns_dict_with_all_services(self, monitor):
        usage = monitor.get_current_quota_usage()
        assert isinstance(usage, dict)
        for service in ("openai", "anthropic", "google", "youtube"):
            assert service in usage

    def test_initial_usage_is_zero(self, monitor):
        usage = monitor.get_current_quota_usage()
        for count in usage.values():
            assert count == 0

    def test_after_rate_limit_check_increments(self, monitor):
        monitor.check_rate_limit("openai")
        usage = monitor.get_current_quota_usage()
        assert usage["openai"] == 1


# ===========================================================================
# APICostMonitor — get_cost_dashboard
# ===========================================================================


class TestGetCostDashboard:
    async def test_returns_dict(self, monitor):
        result = await monitor.get_cost_dashboard()
        assert isinstance(result, dict)

    async def test_has_timestamp(self, monitor):
        result = await monitor.get_cost_dashboard()
        assert "timestamp" in result

    async def test_has_today_summary(self, monitor):
        result = await monitor.get_cost_dashboard()
        assert "today_summary" in result

    async def test_has_rate_limit_status(self, monitor):
        result = await monitor.get_cost_dashboard()
        assert "rate_limit_status" in result

    async def test_has_optimization(self, monitor):
        result = await monitor.get_cost_dashboard()
        assert "optimization" in result

    async def test_rate_limit_status_has_all_services(self, monitor):
        result = await monitor.get_cost_dashboard()
        for service in ("openai", "anthropic", "google", "youtube"):
            assert service in result["rate_limit_status"]

    async def test_today_summary_has_total_cost(self, monitor):
        result = await monitor.get_cost_dashboard()
        assert "total_cost" in result["today_summary"]

    async def test_today_summary_has_budget_remaining(self, monitor):
        result = await monitor.get_cost_dashboard()
        assert "budget_remaining" in result["today_summary"]


# ===========================================================================
# APICostMonitor — _send_budget_alert / _check_budget_alerts
# ===========================================================================


class TestBudgetAlerts:
    async def test_send_budget_alert_threshold(self, monitor):
        # Should not raise
        await monitor._send_budget_alert(8.50, "threshold")

    async def test_send_budget_alert_exceeded(self, monitor):
        await monitor._send_budget_alert(11.00, "exceeded")

    async def test_check_budget_alerts_no_exception(self, monitor):
        await monitor._check_budget_alerts()

    async def test_check_budget_alerts_with_high_cost(self, monitor, monkeypatch):
        monkeypatch.setattr(monitor, "get_daily_cost", lambda date=None: __import__("asyncio").coroutine(lambda: 9.5)())

        async def fake_get_daily_cost(date=None):
            return 9.5

        monkeypatch.setattr(monitor, "get_daily_cost", fake_get_daily_cost)
        await monitor._check_budget_alerts()


# ===========================================================================
# APICostMonitor — init and misc
# ===========================================================================


class TestAPICostMonitorInit:
    def test_db_path_set(self, monitor):
        assert monitor.db_path.endswith("test_monitor.db")

    def test_daily_budget_positive(self, monitor):
        assert monitor.daily_budget > 0

    def test_rate_limiters_initialized(self, monitor):
        assert len(monitor.rate_limiters) >= 4

    def test_circuit_breakers_initially_empty(self, monitor):
        assert len(monitor.circuit_breakers) == 0

    def test_session_costs_initially_empty(self, monitor):
        assert len(monitor.session_costs) == 0

    def test_cost_tracking_enabled_by_default(self, monitor):
        assert monitor.cost_tracking_enabled is True

@pytest.mark.asyncio
class TestBudgetAlertWebhook:
    async def test_webhook_alert_success(self, monitor, monkeypatch, mocker):
        # Set the webhook URL
        monkeypatch.setenv("BUDGET_ALERT_WEBHOOK_URL", "http://example.com/webhook")

        # Mock urllib.request.urlopen
        mock_urlopen = mocker.patch("urllib.request.urlopen")

        # Trigger an alert
        await monitor._send_budget_alert(15.0, "exceeded")

        # Verify urlopen was called once
        mock_urlopen.assert_called_once()
        req = mock_urlopen.call_args[0][0]
        assert req.full_url == "http://example.com/webhook"
        assert req.headers.get('Content-type') == 'application/json'

    async def test_webhook_alert_failure_does_not_throw(self, monitor, monkeypatch, mocker, caplog):
        # Set the webhook URL
        monkeypatch.setenv("BUDGET_ALERT_WEBHOOK_URL", "http://example.com/webhook")

        # Mock urllib.request.urlopen to raise an exception
        mock_urlopen = mocker.patch("urllib.request.urlopen")
        mock_urlopen.side_effect = Exception("Webhook failed")

        # Trigger an alert - should not raise exception
        await monitor._send_budget_alert(15.0, "exceeded")

        # Verify the failure was logged
        assert "Failed to send budget alert notification: Webhook failed" in caplog.text

    async def test_no_webhook_url(self, monitor, monkeypatch, mocker):
        # Ensure webhook URL is not set
        monkeypatch.delenv("BUDGET_ALERT_WEBHOOK_URL", raising=False)

        # Mock urllib.request.urlopen
        mock_urlopen = mocker.patch("urllib.request.urlopen")

        # Trigger an alert
        await monitor._send_budget_alert(15.0, "exceeded")

        # Verify urlopen was NOT called
        mock_urlopen.assert_not_called()
