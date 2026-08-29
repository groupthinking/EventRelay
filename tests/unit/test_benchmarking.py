"""Unit tests for BenchmarkResult, BenchmarkSuite, PerformanceTarget, and benchmarking systems."""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

# ---------------------------------------------------------------------------
# comprehensive_benchmarking imports
# ---------------------------------------------------------------------------
from youtube_extension.backend.services.comprehensive_benchmarking import (
    BenchmarkResult as CBBenchmarkResult,
)
from youtube_extension.backend.services.comprehensive_benchmarking import (
    BenchmarkSuite,
    ComprehensiveBenchmark,
)
from youtube_extension.backend.services.comprehensive_benchmarking import (
    PerformanceTarget as CBPerformanceTarget,
)

# ---------------------------------------------------------------------------
# performance_benchmark_system imports
# ---------------------------------------------------------------------------
from youtube_extension.backend.services.performance_benchmark_system import (
    BenchmarkResult as PBSBenchmarkResult,
)
from youtube_extension.backend.services.performance_benchmark_system import (
    PerformanceBenchmarkSystem,
)
from youtube_extension.backend.services.performance_benchmark_system import (
    PerformanceTarget as PBSPerformanceTarget,
)

# ===========================================================================
# comprehensive_benchmarking — BenchmarkResult
# ===========================================================================


class TestCBBenchmarkResult:
    def _make(self, **kwargs):
        defaults = dict(
            name="test_bench",
            component="cache",
            execution_time_ms=100.0,
            memory_usage_mb=50.0,
            cpu_usage_percent=25.0,
            success=True,
        )
        defaults.update(kwargs)
        return CBBenchmarkResult(**defaults)

    def test_fields_stored(self):
        r = self._make(name="my_bench")
        assert r.name == "my_bench"

    def test_timestamp_auto_set(self):
        before = datetime.now(timezone.utc)
        r = self._make()
        assert r.timestamp >= before

    def test_explicit_timestamp_preserved(self):
        ts = datetime(2024, 1, 1, tzinfo=timezone.utc)
        r = self._make(timestamp=ts)
        assert r.timestamp == ts

    def test_metadata_none_replaced_with_dict(self):
        r = self._make(metadata=None)
        assert r.metadata == {}

    def test_explicit_metadata_preserved(self):
        r = self._make(metadata={"key": "val"})
        assert r.metadata["key"] == "val"

    def test_error_message_default_none(self):
        assert self._make().error_message is None

    def test_success_stored(self):
        assert self._make(success=False).success is False


# ===========================================================================
# comprehensive_benchmarking — BenchmarkSuite
# ===========================================================================


class TestBenchmarkSuite:
    @pytest.fixture
    def suite(self):
        return BenchmarkSuite(
            name="cache_suite",
            description="Cache performance tests",
            benchmarks=[{"name": "hit_rate"}],
        )

    def test_name_stored(self, suite):
        assert suite.name == "cache_suite"

    def test_description_stored(self, suite):
        assert "Cache" in suite.description

    def test_benchmarks_stored(self, suite):
        assert len(suite.benchmarks) == 1

    def test_target_improvement_default(self, suite):
        assert suite.target_improvement_percent == 60.0

    def test_baseline_results_default_none(self, suite):
        assert suite.baseline_results is None


# ===========================================================================
# comprehensive_benchmarking — PerformanceTarget
# ===========================================================================


class TestCBPerformanceTarget:
    @pytest.fixture
    def target(self):
        return CBPerformanceTarget(
            component="video_processing",
            metric="processing_time_ms",
            target_value=30000,
            unit="ms",
            comparison="less_than",
            priority="critical",
        )

    def test_component_stored(self, target):
        assert target.component == "video_processing"

    def test_metric_stored(self, target):
        assert target.metric == "processing_time_ms"

    def test_target_value_stored(self, target):
        assert target.target_value == 30000

    def test_comparison_stored(self, target):
        assert target.comparison == "less_than"

    def test_priority_stored(self, target):
        assert target.priority == "critical"


# ===========================================================================
# comprehensive_benchmarking — ComprehensiveBenchmark init
# ===========================================================================


class TestComprehensiveBenchmarkInit:
    @pytest.fixture
    def cb(self):
        return ComprehensiveBenchmark()

    def test_benchmark_suites_starts_empty(self, cb):
        assert cb.benchmark_suites == {}

    def test_performance_targets_is_list(self, cb):
        assert isinstance(cb.performance_targets, list)

    def test_performance_targets_not_empty(self, cb):
        assert len(cb.performance_targets) > 0

    def test_benchmark_history_starts_empty(self, cb):
        assert cb.benchmark_history == []

    def test_baseline_not_established(self, cb):
        assert cb.baseline_established is False

    def test_current_session_results_starts_empty(self, cb):
        assert cb.current_session_results == []

    def test_each_target_has_component(self, cb):
        for t in cb.performance_targets:
            assert hasattr(t, "component")

    def test_each_target_has_metric(self, cb):
        for t in cb.performance_targets:
            assert hasattr(t, "metric")


# ===========================================================================
# performance_benchmark_system — BenchmarkResult
# ===========================================================================


class TestPBSBenchmarkResult:
    def _make(self, **kwargs):
        defaults = dict(
            benchmark_name="db_query_bench",
            component="database",
            execution_time_ms=80.0,
            success=True,
            iterations=100,
        )
        defaults.update(kwargs)
        return PBSBenchmarkResult(**defaults)

    def test_fields_stored(self):
        r = self._make(benchmark_name="x")
        assert r.benchmark_name == "x"

    def test_timestamp_auto_set(self):
        before = datetime.now(timezone.utc)
        r = self._make()
        assert r.timestamp >= before

    def test_metadata_none_replaced_with_dict(self):
        assert self._make(metadata=None).metadata == {}

    def test_improvement_percent_default_zero(self):
        r = self._make(baseline_time_ms=None)
        assert r.improvement_percent == 0.0

    def test_improvement_percent_calculated(self):
        # (100 - 60) / 100 * 100 = 40%
        r = self._make(execution_time_ms=60.0, baseline_time_ms=100.0)
        assert abs(r.improvement_percent - 40.0) < 1e-6

    def test_no_improvement_when_same(self):
        r = self._make(execution_time_ms=100.0, baseline_time_ms=100.0)
        assert abs(r.improvement_percent - 0.0) < 1e-6

    def test_iterations_stored(self):
        assert self._make(iterations=50).iterations == 50


# ===========================================================================
# performance_benchmark_system — PerformanceTarget
# ===========================================================================


class TestPBSPerformanceTarget:
    def test_priority_default_medium(self):
        t = PBSPerformanceTarget(
            component="cache",
            metric="hit_rate",
            target_value=80.0,
            unit="%",
            comparison="greater_than",
        )
        assert t.priority == "medium"

    def test_baseline_value_default_none(self):
        t = PBSPerformanceTarget(
            component="cache",
            metric="hit_rate",
            target_value=80.0,
            unit="%",
            comparison="greater_than",
        )
        assert t.baseline_value is None

    def test_improvement_target_default_none(self):
        t = PBSPerformanceTarget(
            component="cache",
            metric="hit_rate",
            target_value=80.0,
            unit="%",
            comparison="greater_than",
        )
        assert t.improvement_target_percent is None

    def test_fields_stored(self):
        t = PBSPerformanceTarget(
            component="db",
            metric="query_ms",
            target_value=100.0,
            unit="ms",
            comparison="less_than",
            priority="critical",
        )
        assert t.component == "db"
        assert t.priority == "critical"


# ===========================================================================
# performance_benchmark_system — PerformanceBenchmarkSystem init
# ===========================================================================


class TestPerformanceBenchmarkSystemInit:
    @pytest.fixture
    def pbs(self):
        return PerformanceBenchmarkSystem()

    def test_performance_targets_not_empty(self, pbs):
        assert len(pbs.performance_targets) > 0

    def test_has_five_targets(self, pbs):
        assert len(pbs.performance_targets) == 5

    def test_benchmark_history_starts_empty(self, pbs):
        assert len(pbs.benchmark_history) == 0

    def test_baseline_results_starts_empty(self, pbs):
        assert pbs.baseline_results == {}

    def test_current_results_starts_empty(self, pbs):
        assert pbs.current_results == {}

    def test_target_components_include_video_processing(self, pbs):
        components = [t.component for t in pbs.performance_targets]
        assert "video_processing" in components

    def test_target_components_include_database(self, pbs):
        components = [t.component for t in pbs.performance_targets]
        assert "database" in components

    def test_target_components_include_cache(self, pbs):
        components = [t.component for t in pbs.performance_targets]
        assert "cache" in components
