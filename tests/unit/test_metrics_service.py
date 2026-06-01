"""Unit tests for MetricPoint and MetricSeries — pure dataclass logic."""

from __future__ import annotations

import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from youtube_extension.backend.services.metrics_service import MetricPoint, MetricSeries


# ===========================================================================
# MetricPoint
# ===========================================================================


class TestMetricPoint:
    def test_required_fields(self):
        now = datetime.utcnow()
        p = MetricPoint(name="cpu", value=42.5, timestamp=now)
        assert p.name == "cpu"
        assert p.value == 42.5
        assert p.timestamp == now

    def test_default_tags_empty(self):
        p = MetricPoint(name="mem", value=100)
        assert p.tags == {}

    def test_default_metadata_empty(self):
        p = MetricPoint(name="mem", value=100)
        assert p.metadata == {}

    def test_custom_tags(self):
        p = MetricPoint(name="req", value=1, tags={"host": "web-1"})
        assert p.tags["host"] == "web-1"

    def test_integer_value(self):
        p = MetricPoint(name="count", value=10)
        assert p.value == 10


# ===========================================================================
# MetricSeries
# ===========================================================================


class TestMetricSeriesAddPoint:
    def test_add_point_increments_length(self):
        s = MetricSeries(name="cpu")
        s.add_point(50.0)
        assert len(s.points) == 1

    def test_add_multiple_points(self):
        s = MetricSeries(name="cpu")
        for v in [10, 20, 30]:
            s.add_point(v)
        assert len(s.points) == 3

    def test_custom_timestamp_stored(self):
        s = MetricSeries(name="cpu")
        t = datetime(2024, 1, 1, 12, 0, 0)
        s.add_point(99.0, timestamp=t)
        assert s.points[-1].timestamp == t

    def test_point_name_matches_series_name(self):
        s = MetricSeries(name="latency")
        s.add_point(200)
        assert s.points[-1].name == "latency"

    def test_tags_passed_through(self):
        s = MetricSeries(name="req")
        s.add_point(1, tags={"env": "prod"})
        assert s.points[-1].tags["env"] == "prod"


class TestMetricSeriesGetRecentPoints:
    def test_returns_all_recent_points(self):
        s = MetricSeries(name="cpu")
        for v in [1, 2, 3]:
            s.add_point(v)
        recent = s.get_recent_points(seconds=300)
        assert len(recent) == 3

    def test_excludes_old_points(self):
        s = MetricSeries(name="cpu")
        old_time = datetime.utcnow() - timedelta(seconds=400)
        s.add_point(99, timestamp=old_time)
        s.add_point(1)  # recent
        recent = s.get_recent_points(seconds=300)
        assert len(recent) == 1
        assert recent[0].value == 1

    def test_empty_series_returns_empty(self):
        s = MetricSeries(name="cpu")
        assert s.get_recent_points() == []

    def test_all_old_points_excluded(self):
        s = MetricSeries(name="cpu")
        old = datetime.utcnow() - timedelta(seconds=600)
        s.add_point(50, timestamp=old)
        assert s.get_recent_points(seconds=300) == []


class TestMetricSeriesGetAggregatedStats:
    def test_empty_returns_zero_stats(self):
        s = MetricSeries(name="cpu")
        stats = s.get_aggregated_stats()
        assert stats == {"count": 0, "mean": 0, "min": 0, "max": 0}

    def test_single_point_stats(self):
        s = MetricSeries(name="cpu")
        s.add_point(50.0)
        stats = s.get_aggregated_stats()
        assert stats["count"] == 1
        assert stats["mean"] == 50.0
        assert stats["min"] == 50.0
        assert stats["max"] == 50.0
        assert stats["std_dev"] == 0

    def test_multiple_points_mean(self):
        s = MetricSeries(name="cpu")
        for v in [10, 20, 30]:
            s.add_point(v)
        stats = s.get_aggregated_stats()
        assert stats["mean"] == 20.0
        assert stats["min"] == 10
        assert stats["max"] == 30

    def test_std_dev_computed_for_multiple(self):
        s = MetricSeries(name="cpu")
        for v in [10, 20, 30]:
            s.add_point(v)
        stats = s.get_aggregated_stats()
        assert stats["std_dev"] > 0

    def test_latest_and_oldest_values(self):
        s = MetricSeries(name="cpu")
        s.add_point(5)
        s.add_point(15)
        s.add_point(25)
        stats = s.get_aggregated_stats()
        assert stats["oldest"] == 5
        assert stats["latest"] == 25

    def test_median_computed(self):
        s = MetricSeries(name="cpu")
        for v in [1, 2, 3, 4, 5]:
            s.add_point(v)
        stats = s.get_aggregated_stats()
        assert stats["median"] == 3
