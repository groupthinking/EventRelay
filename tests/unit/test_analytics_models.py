"""Unit tests for EventCategory, MetricType, AnalyticsEvent, PerformanceMetric, UsageStatistic."""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from youtube_extension.backend.models.analytics import (
    AnalyticsEvent,
    EventCategory,
    MetricType,
    PerformanceMetric,
    UsageStatistic,
)


def _ns(**attrs) -> SimpleNamespace:
    """Lightweight stand-in for an ORM instance — no SA mapper involved."""
    return SimpleNamespace(**attrs)


# ===========================================================================
# EventCategory enum
# ===========================================================================


class TestEventCategoryEnum:
    def test_user_behavior_value(self):
        assert EventCategory.USER_BEHAVIOR.value == "user_behavior"

    def test_system_performance_value(self):
        assert EventCategory.SYSTEM_PERFORMANCE.value == "system_performance"

    def test_business_metric_value(self):
        assert EventCategory.BUSINESS_METRIC.value == "business_metric"

    def test_error_tracking_value(self):
        assert EventCategory.ERROR_TRACKING.value == "error_tracking"

    def test_conversion_value(self):
        assert EventCategory.CONVERSION.value == "conversion"

    def test_engagement_value(self):
        assert EventCategory.ENGAGEMENT.value == "engagement"

    def test_has_six_members(self):
        assert len(EventCategory) == 6


# ===========================================================================
# MetricType enum
# ===========================================================================


class TestMetricTypeEnum:
    def test_latency_value(self):
        assert MetricType.LATENCY.value == "latency"

    def test_throughput_value(self):
        assert MetricType.THROUGHPUT.value == "throughput"

    def test_error_rate_value(self):
        assert MetricType.ERROR_RATE.value == "error_rate"

    def test_resource_usage_value(self):
        assert MetricType.RESOURCE_USAGE.value == "resource_usage"

    def test_availability_value(self):
        assert MetricType.AVAILABILITY.value == "availability"

    def test_capacity_value(self):
        assert MetricType.CAPACITY.value == "capacity"

    def test_has_six_members(self):
        assert len(MetricType) == 6


# ===========================================================================
# AnalyticsEvent.get_property / set_property
# ===========================================================================


class TestAnalyticsEventGetSetProperty:
    def test_get_existing_property(self):
        e = _ns(properties={"page": "/home"})
        assert AnalyticsEvent.get_property(e, "page") == "/home"

    def test_get_missing_property_returns_default_none(self):
        e = _ns(properties={})
        assert AnalyticsEvent.get_property(e, "absent") is None

    def test_get_missing_property_returns_custom_default(self):
        e = _ns(properties={})
        assert AnalyticsEvent.get_property(e, "absent", "fallback") == "fallback"

    def test_set_property_stores_value(self):
        e = _ns(properties={})
        AnalyticsEvent.set_property(e, "device", "mobile")
        assert e.properties["device"] == "mobile"

    def test_set_property_initializes_dict_when_none(self):
        e = _ns(properties=None)
        AnalyticsEvent.set_property(e, "k", "v")
        assert e.properties == {"k": "v"}

    def test_set_property_overwrites_existing(self):
        e = _ns(properties={"k": "old"})
        AnalyticsEvent.set_property(e, "k", "new")
        assert e.properties["k"] == "new"


# ===========================================================================
# AnalyticsEvent.is_conversion_event
# ===========================================================================


class TestAnalyticsEventIsConversion:
    def _is(self, name):
        return AnalyticsEvent.is_conversion_event(_ns(event_name=name))

    def test_user_signup_is_conversion(self):
        assert self._is("user_signup") is True

    def test_subscription_started_is_conversion(self):
        assert self._is("subscription_started") is True

    def test_payment_completed_is_conversion(self):
        assert self._is("payment_completed") is True

    def test_video_processed_is_conversion(self):
        assert self._is("video_processed") is True

    def test_learning_completed_is_conversion(self):
        assert self._is("learning_completed") is True

    def test_page_view_is_not_conversion(self):
        assert self._is("page_view") is False

    def test_unknown_event_is_not_conversion(self):
        assert self._is("unknown_event") is False


# ===========================================================================
# PerformanceMetric.is_above_threshold
# ===========================================================================


class TestPerformanceMetricIsAboveThreshold:
    def _m(self, value, warning=None, critical=None):
        return _ns(value=value, warning_threshold=warning, critical_threshold=critical)

    def test_above_warning_threshold(self):
        assert PerformanceMetric.is_above_threshold(self._m(90.0, warning=80.0), "warning") is True

    def test_below_warning_threshold(self):
        assert PerformanceMetric.is_above_threshold(self._m(70.0, warning=80.0), "warning") is False

    def test_above_critical_threshold(self):
        assert PerformanceMetric.is_above_threshold(self._m(1100.0, critical=1000.0), "critical") is True

    def test_below_critical_threshold(self):
        assert PerformanceMetric.is_above_threshold(self._m(900.0, critical=1000.0), "critical") is False

    def test_no_warning_threshold_returns_false(self):
        assert PerformanceMetric.is_above_threshold(self._m(100.0), "warning") is False

    def test_no_critical_threshold_returns_false(self):
        assert PerformanceMetric.is_above_threshold(self._m(100.0), "critical") is False


# ===========================================================================
# PerformanceMetric.get_health_status
# ===========================================================================


class TestPerformanceMetricGetHealthStatus:
    def _m(self, value, warning=None, critical=None):
        return _ns(value=value, warning_threshold=warning, critical_threshold=critical)

    def test_healthy_when_no_thresholds(self):
        assert PerformanceMetric.get_health_status(self._m(50.0)) == "healthy"

    def test_warning_when_above_warning_only(self):
        assert PerformanceMetric.get_health_status(self._m(85.0, warning=80.0)) == "warning"

    def test_critical_when_above_critical(self):
        assert PerformanceMetric.get_health_status(
            self._m(1050.0, warning=800.0, critical=1000.0)
        ) == "critical"

    def test_warning_when_between_thresholds(self):
        assert PerformanceMetric.get_health_status(
            self._m(900.0, warning=800.0, critical=1000.0)
        ) == "warning"

    def test_healthy_when_below_warning(self):
        assert PerformanceMetric.get_health_status(
            self._m(50.0, warning=80.0, critical=100.0)
        ) == "healthy"


# ===========================================================================
# UsageStatistic.calculate_growth_rate
# ===========================================================================


class TestUsageStatisticCalculateGrowthRate:
    def test_returns_none_when_no_previous_value(self):
        s = _ns(value=100.0, previous_value=None)
        assert UsageStatistic.calculate_growth_rate(s) is None

    def test_returns_none_when_previous_value_zero(self):
        s = _ns(value=100.0, previous_value=0)
        assert UsageStatistic.calculate_growth_rate(s) is None

    def test_positive_growth(self):
        s = _ns(value=120.0, previous_value=100.0)
        assert abs(UsageStatistic.calculate_growth_rate(s) - 20.0) < 1e-6

    def test_negative_growth(self):
        s = _ns(value=80.0, previous_value=100.0)
        assert abs(UsageStatistic.calculate_growth_rate(s) - (-20.0)) < 1e-6

    def test_zero_growth(self):
        s = _ns(value=100.0, previous_value=100.0)
        assert abs(UsageStatistic.calculate_growth_rate(s) - 0.0) < 1e-9


# ===========================================================================
# UsageStatistic.is_trending_up
# ===========================================================================


class TestUsageStatisticIsTrendingUp:
    def test_positive_change_trends_up(self):
        assert UsageStatistic.is_trending_up(_ns(change_value=10.0)) is True

    def test_negative_change_not_trending_up(self):
        assert UsageStatistic.is_trending_up(_ns(change_value=-5.0)) is False

    def test_zero_change_not_trending_up(self):
        assert UsageStatistic.is_trending_up(_ns(change_value=0.0)) is False

    def test_none_change_value_not_trending_up(self):
        assert UsageStatistic.is_trending_up(_ns(change_value=None)) is False


# ===========================================================================
# UsageStatistic.get_target_status
# ===========================================================================


class TestUsageStatisticGetTargetStatus:
    def _s(self, value, target):
        return _ns(value=value, target_value=target)

    def test_no_target_returns_no_target(self):
        assert UsageStatistic.get_target_status(self._s(100.0, None)) == "no_target"

    def test_exceeded_at_100_percent(self):
        assert UsageStatistic.get_target_status(self._s(100.0, 100.0)) == "exceeded"

    def test_exceeded_above_target(self):
        assert UsageStatistic.get_target_status(self._s(110.0, 100.0)) == "exceeded"

    def test_on_track_at_90_percent(self):
        assert UsageStatistic.get_target_status(self._s(90.0, 100.0)) == "on_track"

    def test_on_track_at_95_percent(self):
        assert UsageStatistic.get_target_status(self._s(95.0, 100.0)) == "on_track"

    def test_behind_at_70_percent(self):
        assert UsageStatistic.get_target_status(self._s(70.0, 100.0)) == "behind"

    def test_behind_at_80_percent(self):
        assert UsageStatistic.get_target_status(self._s(80.0, 100.0)) == "behind"

    def test_at_risk_below_70_percent(self):
        assert UsageStatistic.get_target_status(self._s(60.0, 100.0)) == "at_risk"
