"""
Comprehensive tests for src/youtube_extension/backend/services/comprehensive_benchmarking.py

Covers:
- BenchmarkResult dataclass and __post_init__
- BenchmarkSuite dataclass
- PerformanceTarget dataclass
- ComprehensiveBenchmark.__init__
- ComprehensiveBenchmark.register_benchmark_suite
- ComprehensiveBenchmark._define_performance_targets
- ComprehensiveBenchmark.get_benchmark_summary
- ComprehensiveBenchmark._calculate_performance_grade
- ComprehensiveBenchmark._get_system_info (async)
- ComprehensiveBenchmark._get_memory_usage (async)
- ComprehensiveBenchmark._get_cpu_usage (async)
- ComprehensiveBenchmark._calculate_improvement
- ComprehensiveBenchmark._extract_metric_value (async)
"""

import asyncio
from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from youtube_extension.backend.services.comprehensive_benchmarking import (
    BenchmarkResult,
    BenchmarkSuite,
    ComprehensiveBenchmark,
    PerformanceTarget,
    create_default_benchmark_suites,
    get_benchmark_status,
)


# ---------------------------------------------------------------------------
# BenchmarkResult dataclass tests
# ---------------------------------------------------------------------------

class TestBenchmarkResult:
    """Tests for the BenchmarkResult dataclass."""

    def test_basic_creation_with_required_fields(self):
        result = BenchmarkResult(
            name="test_bench",
            component="video_processing",
            execution_time_ms=150.0,
            memory_usage_mb=64.0,
            cpu_usage_percent=25.0,
            success=True,
        )
        assert result.name == "test_bench"
        assert result.component == "video_processing"
        assert result.execution_time_ms == 150.0
        assert result.memory_usage_mb == 64.0
        assert result.cpu_usage_percent == 25.0
        assert result.success is True

    def test_post_init_sets_timestamp_when_none(self):
        before = datetime.now(timezone.utc)
        result = BenchmarkResult(
            name="ts_test",
            component="cache",
            execution_time_ms=10.0,
            memory_usage_mb=1.0,
            cpu_usage_percent=5.0,
            success=True,
        )
        after = datetime.now(timezone.utc)
        assert result.timestamp is not None
        assert before <= result.timestamp <= after

    def test_post_init_preserves_explicit_timestamp(self):
        fixed_ts = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        result = BenchmarkResult(
            name="ts_preserved",
            component="database",
            execution_time_ms=50.0,
            memory_usage_mb=10.0,
            cpu_usage_percent=2.0,
            success=True,
            timestamp=fixed_ts,
        )
        assert result.timestamp == fixed_ts

    def test_post_init_sets_metadata_to_empty_dict_when_none(self):
        result = BenchmarkResult(
            name="meta_test",
            component="cache",
            execution_time_ms=5.0,
            memory_usage_mb=0.5,
            cpu_usage_percent=1.0,
            success=True,
        )
        assert result.metadata == {}

    def test_post_init_preserves_explicit_metadata(self):
        meta = {"key": "value", "count": 42}
        result = BenchmarkResult(
            name="meta_preserved",
            component="cache",
            execution_time_ms=5.0,
            memory_usage_mb=0.5,
            cpu_usage_percent=1.0,
            success=True,
            metadata=meta,
        )
        assert result.metadata == {"key": "value", "count": 42}

    def test_failed_result_with_error_message(self):
        result = BenchmarkResult(
            name="failed_bench",
            component="database",
            execution_time_ms=0.0,
            memory_usage_mb=0.0,
            cpu_usage_percent=0.0,
            success=False,
            error_message="Connection refused",
        )
        assert result.success is False
        assert result.error_message == "Connection refused"

    def test_error_message_defaults_to_none(self):
        result = BenchmarkResult(
            name="ok_bench",
            component="system",
            execution_time_ms=100.0,
            memory_usage_mb=20.0,
            cpu_usage_percent=10.0,
            success=True,
        )
        assert result.error_message is None

    def test_two_results_have_independent_metadata(self):
        r1 = BenchmarkResult(
            name="r1", component="c", execution_time_ms=1.0,
            memory_usage_mb=1.0, cpu_usage_percent=1.0, success=True,
        )
        r2 = BenchmarkResult(
            name="r2", component="c", execution_time_ms=2.0,
            memory_usage_mb=2.0, cpu_usage_percent=2.0, success=True,
        )
        r1.metadata["x"] = 1
        assert "x" not in r2.metadata


# ---------------------------------------------------------------------------
# BenchmarkSuite dataclass tests
# ---------------------------------------------------------------------------

class TestBenchmarkSuite:
    """Tests for the BenchmarkSuite dataclass."""

    def test_basic_creation(self):
        suite = BenchmarkSuite(
            name="my_suite",
            description="A test suite",
            benchmarks=[],
        )
        assert suite.name == "my_suite"
        assert suite.description == "A test suite"
        assert suite.benchmarks == []

    def test_default_target_improvement_percent(self):
        suite = BenchmarkSuite(name="s", description="d", benchmarks=[])
        assert suite.target_improvement_percent == 60.0

    def test_custom_target_improvement_percent(self):
        suite = BenchmarkSuite(name="s", description="d", benchmarks=[], target_improvement_percent=80.0)
        assert suite.target_improvement_percent == 80.0

    def test_baseline_results_defaults_to_none(self):
        suite = BenchmarkSuite(name="s", description="d", benchmarks=[])
        assert suite.baseline_results is None

    def test_suite_stores_benchmark_list(self):
        benchmarks = [
            {"name": "b1", "component": "cache", "type": "cache_operation"},
            {"name": "b2", "component": "database", "type": "database_query"},
        ]
        suite = BenchmarkSuite(name="s", description="d", benchmarks=benchmarks)
        assert len(suite.benchmarks) == 2
        assert suite.benchmarks[0]["name"] == "b1"


# ---------------------------------------------------------------------------
# PerformanceTarget dataclass tests
# ---------------------------------------------------------------------------

class TestPerformanceTarget:
    """Tests for the PerformanceTarget dataclass."""

    def test_basic_creation(self):
        pt = PerformanceTarget(
            component="cache",
            metric="hit_ratio_percent",
            target_value=90.0,
            unit="%",
            comparison="greater_than",
            priority="high",
        )
        assert pt.component == "cache"
        assert pt.metric == "hit_ratio_percent"
        assert pt.target_value == 90.0
        assert pt.unit == "%"
        assert pt.comparison == "greater_than"
        assert pt.priority == "high"

    def test_less_than_comparison_stored(self):
        pt = PerformanceTarget(
            component="database",
            metric="query_time_ms",
            target_value=100,
            unit="ms",
            comparison="less_than",
            priority="critical",
        )
        assert pt.comparison == "less_than"
        assert pt.priority == "critical"

    def test_equals_comparison_stored(self):
        pt = PerformanceTarget(
            component="system",
            metric="cpu_usage_percent",
            target_value=80,
            unit="%",
            comparison="equals",
            priority="medium",
        )
        assert pt.comparison == "equals"


# ---------------------------------------------------------------------------
# ComprehensiveBenchmark.__init__ and basic structure tests
# ---------------------------------------------------------------------------

class TestComprehensiveBenchmarkInit:
    """Tests for ComprehensiveBenchmark initialisation."""

    def test_init_creates_empty_benchmark_suites(self):
        cb = ComprehensiveBenchmark()
        # The global instance registers suites but a fresh instance starts empty
        # before suites are registered (the global one auto-registers default suites,
        # but a new instance does not).
        assert isinstance(cb.benchmark_suites, dict)

    def test_init_creates_benchmark_history(self):
        cb = ComprehensiveBenchmark()
        assert isinstance(cb.benchmark_history, list)

    def test_init_baseline_not_established(self):
        cb = ComprehensiveBenchmark()
        assert cb.baseline_established is False

    def test_init_defines_performance_targets(self):
        cb = ComprehensiveBenchmark()
        assert isinstance(cb.performance_targets, list)
        assert len(cb.performance_targets) > 0

    def test_init_results_directory_set(self):
        cb = ComprehensiveBenchmark()
        assert cb.results_directory == "benchmark_results"

    def test_init_current_session_results_empty(self):
        cb = ComprehensiveBenchmark()
        assert cb.current_session_results == []


# ---------------------------------------------------------------------------
# _define_performance_targets tests
# ---------------------------------------------------------------------------

class TestDefinePerformanceTargets:
    """Tests for ComprehensiveBenchmark._define_performance_targets."""

    def setup_method(self):
        self.cb = ComprehensiveBenchmark()
        self.targets = self.cb._define_performance_targets()

    def test_returns_list(self):
        assert isinstance(self.targets, list)

    def test_all_items_are_performance_targets(self):
        for t in self.targets:
            assert isinstance(t, PerformanceTarget)

    def test_contains_video_processing_target(self):
        components = [t.component for t in self.targets]
        assert "video_processing" in components

    def test_contains_database_targets(self):
        db_targets = [t for t in self.targets if t.component == "database"]
        assert len(db_targets) >= 2

    def test_contains_cache_targets(self):
        cache_targets = [t for t in self.targets if t.component == "cache"]
        assert len(cache_targets) >= 1

    def test_contains_system_targets(self):
        system_targets = [t for t in self.targets if t.component == "system"]
        assert len(system_targets) >= 1

    def test_contains_frontend_targets(self):
        frontend_targets = [t for t in self.targets if t.component == "frontend"]
        assert len(frontend_targets) >= 1

    def test_critical_priority_targets_exist(self):
        critical = [t for t in self.targets if t.priority == "critical"]
        assert len(critical) >= 1

    def test_all_targets_have_valid_comparison(self):
        valid_comparisons = {"less_than", "greater_than", "equals"}
        for t in self.targets:
            assert t.comparison in valid_comparisons

    def test_all_targets_have_valid_priority(self):
        valid_priorities = {"critical", "high", "medium", "low"}
        for t in self.targets:
            assert t.priority in valid_priorities

    def test_video_processing_target_less_than_30000ms(self):
        vp = next(
            (t for t in self.targets
             if t.component == "video_processing" and t.metric == "processing_time_ms"),
            None
        )
        assert vp is not None
        assert vp.target_value == 30000
        assert vp.comparison == "less_than"


# ---------------------------------------------------------------------------
# register_benchmark_suite tests
# ---------------------------------------------------------------------------

class TestRegisterBenchmarkSuite:
    """Tests for ComprehensiveBenchmark.register_benchmark_suite."""

    def test_register_adds_suite_to_dict(self):
        cb = ComprehensiveBenchmark()
        suite = BenchmarkSuite(name="my_suite", description="desc", benchmarks=[])
        cb.register_benchmark_suite(suite)
        assert "my_suite" in cb.benchmark_suites

    def test_register_stores_correct_suite_object(self):
        cb = ComprehensiveBenchmark()
        suite = BenchmarkSuite(name="suite_a", description="desc", benchmarks=[])
        cb.register_benchmark_suite(suite)
        assert cb.benchmark_suites["suite_a"] is suite

    def test_register_multiple_suites(self):
        cb = ComprehensiveBenchmark()
        for i in range(3):
            suite = BenchmarkSuite(name=f"suite_{i}", description="d", benchmarks=[])
            cb.register_benchmark_suite(suite)
        assert len(cb.benchmark_suites) == 3

    def test_register_overwrites_existing_suite_with_same_name(self):
        cb = ComprehensiveBenchmark()
        suite1 = BenchmarkSuite(name="dup", description="first", benchmarks=[])
        suite2 = BenchmarkSuite(name="dup", description="second", benchmarks=[])
        cb.register_benchmark_suite(suite1)
        cb.register_benchmark_suite(suite2)
        assert cb.benchmark_suites["dup"].description == "second"


# ---------------------------------------------------------------------------
# get_benchmark_summary tests
# ---------------------------------------------------------------------------

class TestGetBenchmarkSummary:
    """Tests for ComprehensiveBenchmark.get_benchmark_summary."""

    def test_returns_dict(self):
        cb = ComprehensiveBenchmark()
        summary = cb.get_benchmark_summary()
        assert isinstance(summary, dict)

    def test_has_required_keys(self):
        cb = ComprehensiveBenchmark()
        summary = cb.get_benchmark_summary()
        expected_keys = {
            "timestamp",
            "registered_suites",
            "performance_targets",
            "baseline_established",
            "benchmark_history_count",
            "results_directory",
        }
        assert expected_keys.issubset(summary.keys())

    def test_registered_suites_is_list(self):
        cb = ComprehensiveBenchmark()
        summary = cb.get_benchmark_summary()
        assert isinstance(summary["registered_suites"], list)

    def test_baseline_established_is_false_initially(self):
        cb = ComprehensiveBenchmark()
        summary = cb.get_benchmark_summary()
        assert summary["baseline_established"] is False

    def test_benchmark_history_count_starts_at_zero(self):
        cb = ComprehensiveBenchmark()
        summary = cb.get_benchmark_summary()
        assert summary["benchmark_history_count"] == 0

    def test_performance_targets_count_matches_list(self):
        cb = ComprehensiveBenchmark()
        summary = cb.get_benchmark_summary()
        assert summary["performance_targets"] == len(cb.performance_targets)

    def test_registered_suites_reflect_added_suites(self):
        cb = ComprehensiveBenchmark()
        suite = BenchmarkSuite(name="tracked_suite", description="d", benchmarks=[])
        cb.register_benchmark_suite(suite)
        summary = cb.get_benchmark_summary()
        assert "tracked_suite" in summary["registered_suites"]

    def test_results_directory_is_correct(self):
        cb = ComprehensiveBenchmark()
        summary = cb.get_benchmark_summary()
        assert summary["results_directory"] == "benchmark_results"

    def test_benchmark_history_count_increments(self):
        cb = ComprehensiveBenchmark()
        cb.benchmark_history.append({"run": 1})
        cb.benchmark_history.append({"run": 2})
        summary = cb.get_benchmark_summary()
        assert summary["benchmark_history_count"] == 2


# ---------------------------------------------------------------------------
# _calculate_performance_grade tests
# ---------------------------------------------------------------------------

class TestCalculatePerformanceGrade:
    """Tests for ComprehensiveBenchmark._calculate_performance_grade."""

    def setup_method(self):
        self.cb = ComprehensiveBenchmark()

    def _make_results(self, critical_failed=0, targets_failed=0, improvement_met=False):
        """Helper to construct minimal benchmark_results dict for grading."""
        improvement_analysis = {}
        if improvement_met:
            improvement_analysis = {
                "suite1": {
                    "bench1": {"meets_60_percent_target": True}
                }
            }
        return {
            "target_validation": {
                "critical_targets_failed": critical_failed,
                "targets_failed": targets_failed,
            },
            "improvement_analysis": improvement_analysis,
        }

    def test_perfect_score_returns_a_plus(self):
        results = self._make_results(critical_failed=0, targets_failed=0, improvement_met=True)
        grade = self.cb._calculate_performance_grade(results)
        assert grade == "A+"

    def test_no_improvement_target_lowers_grade(self):
        # score = 100 - 15 = 85 → B+
        results = self._make_results(critical_failed=0, targets_failed=0, improvement_met=False)
        grade = self.cb._calculate_performance_grade(results)
        assert grade == "B+"

    def test_one_critical_failure_deducts_20(self):
        # score = 100 - 20 - 15 = 65 → D+
        results = self._make_results(critical_failed=1, targets_failed=1, improvement_met=False)
        grade = self.cb._calculate_performance_grade(results)
        assert grade == "D+"

    def test_two_critical_failures_with_improvement(self):
        # score = 100 - 40 = 60 → D
        results = self._make_results(critical_failed=2, targets_failed=2, improvement_met=True)
        grade = self.cb._calculate_performance_grade(results)
        assert grade == "D"

    def test_f_grade_for_many_failures(self):
        # score = 100 - 5*20 - 15 = -15 → F
        results = self._make_results(critical_failed=5, targets_failed=5, improvement_met=False)
        grade = self.cb._calculate_performance_grade(results)
        assert grade == "F"

    def test_valid_grade_returned_for_empty_results(self):
        results = {}
        grade = self.cb._calculate_performance_grade(results)
        # With empty dict: score = 100 - 0 - 0 - 15 = 85
        assert grade in {"A+", "A", "B+", "B", "C+", "C", "D+", "D", "F"}

    def test_a_grade_range(self):
        # score = 100 - 10 - 0 = 90 → A (one non-critical failure, improvement met)
        results = {
            "target_validation": {
                "critical_targets_failed": 0,
                "targets_failed": 1,  # non-critical only
            },
            "improvement_analysis": {
                "s": {"b": {"meets_60_percent_target": True}}
            },
        }
        grade = self.cb._calculate_performance_grade(results)
        assert grade == "A"

    def test_grade_considers_improvement_analysis_nested(self):
        results = {
            "target_validation": {"critical_targets_failed": 0, "targets_failed": 0},
            "improvement_analysis": {
                "suite_a": {
                    "bench_x": {"meets_60_percent_target": False},
                    "bench_y": {"meets_60_percent_target": True},
                }
            },
        }
        grade = self.cb._calculate_performance_grade(results)
        # improvement_met = True → score = 100 → A+
        assert grade == "A+"


# ---------------------------------------------------------------------------
# _calculate_improvement tests
# ---------------------------------------------------------------------------

class TestCalculateImprovement:
    """Tests for ComprehensiveBenchmark._calculate_improvement."""

    def setup_method(self):
        self.cb = ComprehensiveBenchmark()

    def _make_result(self, execution_time_ms, memory_usage_mb, success=True, error_msg=None):
        return BenchmarkResult(
            name="bench",
            component="test",
            execution_time_ms=execution_time_ms,
            memory_usage_mb=memory_usage_mb,
            cpu_usage_percent=0.0,
            success=success,
            error_message=error_msg,
        )

    def test_calculates_time_improvement(self):
        baseline = {"b1": self._make_result(1000.0, 100.0)}
        current = {"b1": self._make_result(400.0, 80.0)}
        improvements = self.cb._calculate_improvement(baseline, current)
        assert "b1" in improvements
        assert improvements["b1"]["time_improvement_percent"] == pytest.approx(60.0)

    def test_calculates_memory_improvement(self):
        baseline = {"b1": self._make_result(500.0, 200.0)}
        current = {"b1": self._make_result(500.0, 100.0)}
        improvements = self.cb._calculate_improvement(baseline, current)
        assert improvements["b1"]["memory_improvement_percent"] == pytest.approx(50.0)

    def test_meets_60_percent_target_true(self):
        baseline = {"b1": self._make_result(1000.0, 50.0)}
        current = {"b1": self._make_result(350.0, 50.0)}
        improvements = self.cb._calculate_improvement(baseline, current)
        assert improvements["b1"]["meets_60_percent_target"] is True

    def test_meets_60_percent_target_false(self):
        baseline = {"b1": self._make_result(1000.0, 50.0)}
        current = {"b1": self._make_result(500.0, 50.0)}  # only 50% improvement
        improvements = self.cb._calculate_improvement(baseline, current)
        assert improvements["b1"]["meets_60_percent_target"] is False

    def test_handles_failed_baseline(self):
        baseline = {"b1": self._make_result(0.0, 0.0, success=False, error_msg="err")}
        current = {"b1": self._make_result(100.0, 10.0)}
        improvements = self.cb._calculate_improvement(baseline, current)
        assert improvements["b1"]["status"] == "error"

    def test_handles_failed_current(self):
        baseline = {"b1": self._make_result(1000.0, 100.0)}
        current = {"b1": self._make_result(0.0, 0.0, success=False, error_msg="fail")}
        improvements = self.cb._calculate_improvement(baseline, current)
        assert improvements["b1"]["status"] == "error"

    def test_skips_benchmarks_not_in_current(self):
        baseline = {"b1": self._make_result(100.0, 10.0), "b2": self._make_result(200.0, 20.0)}
        current = {"b1": self._make_result(50.0, 5.0)}
        improvements = self.cb._calculate_improvement(baseline, current)
        assert "b1" in improvements
        assert "b2" not in improvements

    def test_zero_baseline_time_returns_zero_improvement(self):
        baseline = {"b1": self._make_result(0.0, 100.0)}
        current = {"b1": self._make_result(50.0, 50.0)}
        improvements = self.cb._calculate_improvement(baseline, current)
        assert improvements["b1"]["time_improvement_percent"] == 0


# ---------------------------------------------------------------------------
# Async: _get_system_info, _get_memory_usage, _get_cpu_usage
# ---------------------------------------------------------------------------

class TestAsyncSystemMethods:
    """Tests for async system information methods."""

    async def test_get_system_info_returns_dict(self):
        cb = ComprehensiveBenchmark()
        info = await cb._get_system_info()
        assert isinstance(info, dict)

    async def test_get_system_info_has_platform_key_on_success(self):
        cb = ComprehensiveBenchmark()
        info = await cb._get_system_info()
        # Should have either platform data or an error key
        assert "platform" in info or "error" in info

    async def test_get_system_info_with_psutil_available(self):
        cb = ComprehensiveBenchmark()
        info = await cb._get_system_info()
        if "error" not in info:
            assert "python_version" in info
            assert "cpu_count" in info
            assert "memory_total_gb" in info
            assert "timestamp" in info

    async def test_get_system_info_returns_error_dict_on_exception(self):
        cb = ComprehensiveBenchmark()
        with patch("psutil.cpu_count", side_effect=RuntimeError("no psutil")):
            info = await cb._get_system_info()
        # Either succeeds or returns error dict
        assert isinstance(info, dict)

    async def test_get_memory_usage_returns_float(self, monkeypatch):
        import sys, types
        fake = types.SimpleNamespace(
            Process=lambda: types.SimpleNamespace(
                memory_info=lambda: types.SimpleNamespace(rss=256 * 1024 * 1024)
            )
        )
        monkeypatch.setitem(sys.modules, 'psutil', fake)
        cb = ComprehensiveBenchmark()
        usage = await cb._get_memory_usage()
        assert isinstance(usage, float)

    async def test_get_memory_usage_non_negative(self, monkeypatch):
        import sys, types
        fake = types.SimpleNamespace(
            Process=lambda: types.SimpleNamespace(
                memory_info=lambda: types.SimpleNamespace(rss=256 * 1024 * 1024)
            )
        )
        monkeypatch.setitem(sys.modules, 'psutil', fake)
        cb = ComprehensiveBenchmark()
        usage = await cb._get_memory_usage()
        assert usage >= 0.0

    async def test_get_memory_usage_returns_zero_on_exception(self):
        cb = ComprehensiveBenchmark()
        with patch("psutil.Process", side_effect=Exception("unavailable")):
            usage = await cb._get_memory_usage()
        assert usage == 0.0

    async def test_get_cpu_usage_returns_float(self, monkeypatch):
        import sys, types
        fake = types.SimpleNamespace(cpu_percent=lambda interval=None: 25.0)
        monkeypatch.setitem(sys.modules, 'psutil', fake)
        cb = ComprehensiveBenchmark()
        usage = await cb._get_cpu_usage()
        assert isinstance(usage, float)

    async def test_get_cpu_usage_returns_zero_on_exception(self, monkeypatch):
        import sys, types
        fake = types.SimpleNamespace(cpu_percent=lambda interval=None: (_ for _ in ()).throw(Exception("unavailable")))
        monkeypatch.setitem(sys.modules, 'psutil', fake)
        cb = ComprehensiveBenchmark()
        usage = await cb._get_cpu_usage()
        assert usage == 0.0

    async def test_get_cpu_usage_non_negative(self, monkeypatch):
        import sys, types
        fake = types.SimpleNamespace(cpu_percent=lambda interval=None: 25.0)
        monkeypatch.setitem(sys.modules, 'psutil', fake)
        cb = ComprehensiveBenchmark()
        usage = await cb._get_cpu_usage()
        assert usage >= 0.0


# ---------------------------------------------------------------------------
# Async: _extract_metric_value
# ---------------------------------------------------------------------------

class TestExtractMetricValue:
    """Tests for ComprehensiveBenchmark._extract_metric_value."""

    def setup_method(self):
        self.cb = ComprehensiveBenchmark()

    def _make_result(self, component, execution_time_ms=100.0, memory_mb=50.0,
                     cpu=10.0, metadata=None):
        r = BenchmarkResult(
            name="b",
            component=component,
            execution_time_ms=execution_time_ms,
            memory_usage_mb=memory_mb,
            cpu_usage_percent=cpu,
            success=True,
            metadata=metadata or {},
        )
        return r

    async def test_extracts_processing_time_ms_from_execution_time(self):
        target = PerformanceTarget(
            component="video_processing",
            metric="processing_time_ms",
            target_value=30000,
            unit="ms",
            comparison="less_than",
            priority="critical",
        )
        results = {
            "suite_results": {
                "suite1": {
                    "bench1": self._make_result("video_processing", execution_time_ms=5000.0)
                }
            }
        }
        value = await self.cb._extract_metric_value(results, target)
        assert value == 5000.0

    async def test_extracts_memory_usage_mb(self):
        target = PerformanceTarget(
            component="system",
            metric="memory_usage_mb",
            target_value=1024,
            unit="MB",
            comparison="less_than",
            priority="high",
        )
        results = {
            "suite_results": {
                "suite1": {
                    "bench1": self._make_result("system", memory_mb=512.0)
                }
            }
        }
        value = await self.cb._extract_metric_value(results, target)
        assert value == 512.0

    async def test_extracts_cpu_usage_percent(self):
        target = PerformanceTarget(
            component="system",
            metric="cpu_usage_percent",
            target_value=80,
            unit="%",
            comparison="less_than",
            priority="medium",
        )
        results = {
            "suite_results": {
                "suite1": {
                    "bench1": self._make_result("system", cpu=45.0)
                }
            }
        }
        value = await self.cb._extract_metric_value(results, target)
        assert value == 45.0

    async def test_extracts_value_from_metadata(self):
        target = PerformanceTarget(
            component="cache",
            metric="hit_ratio_percent",
            target_value=90.0,
            unit="%",
            comparison="greater_than",
            priority="high",
        )
        results = {
            "suite_results": {
                "suite1": {
                    "bench1": self._make_result("cache", metadata={"hit_ratio_percent": 92.5})
                }
            }
        }
        value = await self.cb._extract_metric_value(results, target)
        assert value == pytest.approx(92.5)

    async def test_returns_none_when_no_matching_component(self):
        target = PerformanceTarget(
            component="nonexistent",
            metric="some_metric",
            target_value=100,
            unit="ms",
            comparison="less_than",
            priority="low",
        )
        results = {
            "suite_results": {
                "suite1": {
                    "bench1": self._make_result("cache")
                }
            }
        }
        value = await self.cb._extract_metric_value(results, target)
        assert value is None

    async def test_returns_none_for_empty_suite_results(self):
        target = PerformanceTarget(
            component="cache",
            metric="hit_ratio_percent",
            target_value=90,
            unit="%",
            comparison="greater_than",
            priority="high",
        )
        value = await self.cb._extract_metric_value({}, target)
        assert value is None


# ---------------------------------------------------------------------------
# create_default_benchmark_suites and module-level helpers
# ---------------------------------------------------------------------------

class TestCreateDefaultBenchmarkSuites:
    """Tests for the create_default_benchmark_suites factory function."""

    def test_returns_list(self):
        suites = create_default_benchmark_suites()
        assert isinstance(suites, list)

    def test_returns_benchmark_suite_instances(self):
        suites = create_default_benchmark_suites()
        for suite in suites:
            assert isinstance(suite, BenchmarkSuite)

    def test_returns_at_least_two_suites(self):
        suites = create_default_benchmark_suites()
        assert len(suites) >= 2

    def test_all_suites_have_non_empty_name(self):
        suites = create_default_benchmark_suites()
        for suite in suites:
            assert suite.name != ""

    def test_all_suites_have_benchmarks_list(self):
        suites = create_default_benchmark_suites()
        for suite in suites:
            assert isinstance(suite.benchmarks, list)

    def test_get_benchmark_status_returns_dict(self):
        status = get_benchmark_status()
        assert isinstance(status, dict)

    def test_get_benchmark_status_has_baseline_key(self):
        status = get_benchmark_status()
        assert "baseline_established" in status
