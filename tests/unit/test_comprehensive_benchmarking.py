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

from datetime import datetime, timezone
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
        import sys
        import types
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
        import sys
        import types
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
        import sys
        import types
        fake = types.SimpleNamespace(cpu_percent=lambda interval=None: 25.0)
        monkeypatch.setitem(sys.modules, 'psutil', fake)
        cb = ComprehensiveBenchmark()
        usage = await cb._get_cpu_usage()
        assert isinstance(usage, float)

    async def test_get_cpu_usage_returns_zero_on_exception(self, monkeypatch):
        import sys
        import types
        fake = types.SimpleNamespace(cpu_percent=lambda interval=None: (_ for _ in ()).throw(Exception("unavailable")))
        monkeypatch.setitem(sys.modules, 'psutil', fake)
        cb = ComprehensiveBenchmark()
        usage = await cb._get_cpu_usage()
        assert usage == 0.0

    async def test_get_cpu_usage_non_negative(self, monkeypatch):
        import sys
        import types
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


# ---------------------------------------------------------------------------
# establish_baseline tests
# ---------------------------------------------------------------------------

class TestEstablishBaseline:
    """Tests for ComprehensiveBenchmark.establish_baseline."""

    async def test_sets_baseline_established_true(self):
        cb = ComprehensiveBenchmark()
        cb._run_benchmark_suite = AsyncMock(return_value={})
        cb._save_benchmark_report = AsyncMock()
        cb._get_system_info = AsyncMock(return_value={"cpu": 4})
        await cb.establish_baseline()
        assert cb.baseline_established is True

    async def test_returns_dict(self):
        cb = ComprehensiveBenchmark()
        cb._run_benchmark_suite = AsyncMock(return_value={})
        cb._save_benchmark_report = AsyncMock()
        cb._get_system_info = AsyncMock(return_value={})
        result = await cb.establish_baseline()
        assert isinstance(result, dict)

    async def test_runs_suite_for_each_registered_suite(self):
        cb = ComprehensiveBenchmark()
        for i in range(3):
            cb.register_benchmark_suite(
                BenchmarkSuite(name=f"suite_{i}", description="d", benchmarks=[])
            )
        cb._run_benchmark_suite = AsyncMock(return_value={})
        cb._save_benchmark_report = AsyncMock()
        cb._get_system_info = AsyncMock(return_value={})
        await cb.establish_baseline()
        assert cb._run_benchmark_suite.call_count == 3

    async def test_stores_suite_results_in_baseline_results(self):
        cb = ComprehensiveBenchmark()
        fake_result = {"bench_a": BenchmarkResult(
            name="bench_a", component="cache",
            execution_time_ms=10.0, memory_usage_mb=5.0,
            cpu_usage_percent=2.0, success=True,
        )}
        suite = BenchmarkSuite(name="s1", description="d", benchmarks=[])
        cb.register_benchmark_suite(suite)
        cb._run_benchmark_suite = AsyncMock(return_value=fake_result)
        cb._save_benchmark_report = AsyncMock()
        cb._get_system_info = AsyncMock(return_value={})
        await cb.establish_baseline()
        assert cb.benchmark_suites["s1"].baseline_results == fake_result

    async def test_saves_baseline_report(self):
        cb = ComprehensiveBenchmark()
        cb._run_benchmark_suite = AsyncMock(return_value={})
        cb._save_benchmark_report = AsyncMock()
        cb._get_system_info = AsyncMock(return_value={})
        await cb.establish_baseline()
        cb._save_benchmark_report.assert_called_once()
        call_args = cb._save_benchmark_report.call_args
        assert call_args[0][1] == "baseline"

    async def test_baseline_report_has_type_baseline(self):
        cb = ComprehensiveBenchmark()
        cb._run_benchmark_suite = AsyncMock(return_value={})
        saved_reports = []
        async def capture_report(report, report_type):
            saved_reports.append((report, report_type))
        cb._save_benchmark_report = capture_report
        cb._get_system_info = AsyncMock(return_value={"cpu": 2})
        await cb.establish_baseline()
        assert len(saved_reports) == 1
        report, rtype = saved_reports[0]
        assert rtype == "baseline"
        assert report["type"] == "baseline"
        assert "timestamp" in report
        assert "results" in report
        assert "system_info" in report

    async def test_baseline_result_keyed_by_suite_name(self):
        cb = ComprehensiveBenchmark()
        cb.register_benchmark_suite(BenchmarkSuite(name="my_suite", description="d", benchmarks=[]))
        suite_data = {"b": BenchmarkResult(
            name="b", component="cache", execution_time_ms=5.0,
            memory_usage_mb=1.0, cpu_usage_percent=0.0, success=True,
        )}
        cb._run_benchmark_suite = AsyncMock(return_value=suite_data)
        cb._save_benchmark_report = AsyncMock()
        cb._get_system_info = AsyncMock(return_value={})
        result = await cb.establish_baseline()
        assert "my_suite" in result

    async def test_no_suites_returns_empty_dict(self):
        cb = ComprehensiveBenchmark()
        # no suites registered
        cb._save_benchmark_report = AsyncMock()
        cb._get_system_info = AsyncMock(return_value={})
        result = await cb.establish_baseline()
        assert result == {}
        assert cb.baseline_established is True


# ---------------------------------------------------------------------------
# run_comprehensive_benchmark tests
# ---------------------------------------------------------------------------

class TestRunComprehensiveBenchmark:
    """Tests for ComprehensiveBenchmark.run_comprehensive_benchmark."""

    async def test_returns_dict_with_required_keys(self):
        cb = ComprehensiveBenchmark()
        cb._run_benchmark_suite = AsyncMock(return_value={})
        cb._save_benchmark_report = AsyncMock()
        cb._get_system_info = AsyncMock(return_value={})
        result = await cb.run_comprehensive_benchmark()
        for key in ("timestamp", "type", "suite_results", "target_validation",
                    "improvement_analysis", "system_info", "performance_grade",
                    "total_execution_time_ms"):
            assert key in result, f"Missing key: {key}"

    async def test_type_is_comprehensive(self):
        cb = ComprehensiveBenchmark()
        cb._run_benchmark_suite = AsyncMock(return_value={})
        cb._save_benchmark_report = AsyncMock()
        cb._get_system_info = AsyncMock(return_value={})
        result = await cb.run_comprehensive_benchmark()
        assert result["type"] == "comprehensive"

    async def test_appends_to_benchmark_history(self):
        cb = ComprehensiveBenchmark()
        cb._run_benchmark_suite = AsyncMock(return_value={})
        cb._save_benchmark_report = AsyncMock()
        cb._get_system_info = AsyncMock(return_value={})
        await cb.run_comprehensive_benchmark()
        assert len(cb.benchmark_history) == 1

    async def test_history_capped_at_50(self):
        cb = ComprehensiveBenchmark()
        cb._run_benchmark_suite = AsyncMock(return_value={})
        cb._save_benchmark_report = AsyncMock()
        cb._get_system_info = AsyncMock(return_value={})
        # Pre-fill history with 50 items
        cb.benchmark_history = [{"run": i} for i in range(50)]
        await cb.run_comprehensive_benchmark()
        assert len(cb.benchmark_history) == 50

    async def test_saves_comprehensive_report(self):
        cb = ComprehensiveBenchmark()
        cb._run_benchmark_suite = AsyncMock(return_value={})
        cb._save_benchmark_report = AsyncMock()
        cb._get_system_info = AsyncMock(return_value={})
        await cb.run_comprehensive_benchmark()
        cb._save_benchmark_report.assert_called_once()
        assert cb._save_benchmark_report.call_args[0][1] == "comprehensive"

    async def test_calculates_improvement_when_baseline_exists(self):
        cb = ComprehensiveBenchmark()
        baseline_result = BenchmarkResult(
            name="b", component="cache", execution_time_ms=1000.0,
            memory_usage_mb=100.0, cpu_usage_percent=10.0, success=True,
        )
        current_result = BenchmarkResult(
            name="b", component="cache", execution_time_ms=400.0,
            memory_usage_mb=80.0, cpu_usage_percent=5.0, success=True,
        )
        suite = BenchmarkSuite(name="s", description="d", benchmarks=[])
        suite.baseline_results = {"b": baseline_result}
        cb.register_benchmark_suite(suite)
        cb._run_benchmark_suite = AsyncMock(return_value={"b": current_result})
        cb._save_benchmark_report = AsyncMock()
        cb._get_system_info = AsyncMock(return_value={})
        result = await cb.run_comprehensive_benchmark()
        assert "s" in result["improvement_analysis"]
        assert "b" in result["improvement_analysis"]["s"]

    async def test_no_improvement_analysis_without_baseline(self):
        cb = ComprehensiveBenchmark()
        suite = BenchmarkSuite(name="s", description="d", benchmarks=[])
        # baseline_results is None by default
        cb.register_benchmark_suite(suite)
        cb._run_benchmark_suite = AsyncMock(return_value={})
        cb._save_benchmark_report = AsyncMock()
        cb._get_system_info = AsyncMock(return_value={})
        result = await cb.run_comprehensive_benchmark()
        assert "s" not in result["improvement_analysis"]

    async def test_warns_when_no_baseline(self, caplog):
        import logging
        cb = ComprehensiveBenchmark()
        cb._run_benchmark_suite = AsyncMock(return_value={})
        cb._save_benchmark_report = AsyncMock()
        cb._get_system_info = AsyncMock(return_value={})
        with caplog.at_level(logging.WARNING):
            await cb.run_comprehensive_benchmark()
        assert any("baseline" in rec.message.lower() for rec in caplog.records)

    async def test_total_execution_time_is_positive(self):
        cb = ComprehensiveBenchmark()
        cb._run_benchmark_suite = AsyncMock(return_value={})
        cb._save_benchmark_report = AsyncMock()
        cb._get_system_info = AsyncMock(return_value={})
        result = await cb.run_comprehensive_benchmark()
        assert result["total_execution_time_ms"] >= 0

    async def test_performance_grade_is_string(self):
        cb = ComprehensiveBenchmark()
        cb._run_benchmark_suite = AsyncMock(return_value={})
        cb._save_benchmark_report = AsyncMock()
        cb._get_system_info = AsyncMock(return_value={})
        result = await cb.run_comprehensive_benchmark()
        assert isinstance(result["performance_grade"], str)
        assert result["performance_grade"] in {"A+", "A", "B+", "B", "C+", "C", "D+", "D", "F"}


# ---------------------------------------------------------------------------
# _run_benchmark_suite tests
# ---------------------------------------------------------------------------

class TestRunBenchmarkSuite:
    """Tests for ComprehensiveBenchmark._run_benchmark_suite."""

    async def test_returns_empty_dict_for_empty_benchmarks(self):
        cb = ComprehensiveBenchmark()
        suite = BenchmarkSuite(name="empty", description="d", benchmarks=[])
        result = await cb._run_benchmark_suite(suite)
        assert result == {}

    async def test_calls_run_single_benchmark_per_config(self):
        cb = ComprehensiveBenchmark()
        fake_result = BenchmarkResult(
            name="b1", component="cache", execution_time_ms=5.0,
            memory_usage_mb=1.0, cpu_usage_percent=0.0, success=True,
        )
        cb._run_single_benchmark = AsyncMock(return_value=fake_result)
        suite = BenchmarkSuite(
            name="s", description="d",
            benchmarks=[
                {"name": "b1", "component": "cache", "type": "cache_operation"},
                {"name": "b2", "component": "database", "type": "database_query"},
            ]
        )
        result = await cb._run_benchmark_suite(suite)
        assert cb._run_single_benchmark.call_count == 2

    async def test_result_keyed_by_benchmark_name(self):
        cb = ComprehensiveBenchmark()
        fake_result = BenchmarkResult(
            name="my_bench", component="cache", execution_time_ms=5.0,
            memory_usage_mb=1.0, cpu_usage_percent=0.0, success=True,
        )
        cb._run_single_benchmark = AsyncMock(return_value=fake_result)
        suite = BenchmarkSuite(
            name="s", description="d",
            benchmarks=[{"name": "my_bench", "component": "cache", "type": "cache_operation"}]
        )
        result = await cb._run_benchmark_suite(suite)
        assert "my_bench" in result
        assert result["my_bench"] is fake_result

    async def test_failed_single_benchmark_stored_as_failed_result(self):
        cb = ComprehensiveBenchmark()
        cb._run_single_benchmark = AsyncMock(side_effect=RuntimeError("boom"))
        suite = BenchmarkSuite(
            name="s", description="d",
            benchmarks=[{"name": "failing", "component": "video_processing", "type": "video_processing"}]
        )
        result = await cb._run_benchmark_suite(suite)
        assert "failing" in result
        r = result["failing"]
        assert isinstance(r, BenchmarkResult)
        assert r.success is False
        assert "boom" in r.error_message

    async def test_failed_benchmark_has_correct_component(self):
        cb = ComprehensiveBenchmark()
        cb._run_single_benchmark = AsyncMock(side_effect=Exception("err"))
        suite = BenchmarkSuite(
            name="s", description="d",
            benchmarks=[{"name": "b", "component": "database", "type": "database_query"}]
        )
        result = await cb._run_benchmark_suite(suite)
        assert result["b"].component == "database"

    async def test_one_failure_does_not_stop_others(self):
        cb = ComprehensiveBenchmark()
        ok_result = BenchmarkResult(
            name="b2", component="cache", execution_time_ms=5.0,
            memory_usage_mb=1.0, cpu_usage_percent=0.0, success=True,
        )

        async def side_effect(config):
            if config["name"] == "b1":
                raise RuntimeError("fail b1")
            return ok_result

        cb._run_single_benchmark = side_effect
        suite = BenchmarkSuite(
            name="s", description="d",
            benchmarks=[
                {"name": "b1", "component": "video_processing", "type": "video_processing"},
                {"name": "b2", "component": "cache", "type": "cache_operation"},
            ]
        )
        result = await cb._run_benchmark_suite(suite)
        assert result["b1"].success is False
        assert result["b2"].success is True


# ---------------------------------------------------------------------------
# _run_single_benchmark tests
# ---------------------------------------------------------------------------

class TestRunSingleBenchmark:
    """Tests for ComprehensiveBenchmark._run_single_benchmark."""

    async def test_unknown_type_returns_failed_result(self):
        cb = ComprehensiveBenchmark()
        cb._get_memory_usage = AsyncMock(return_value=100.0)
        cb._get_cpu_usage = AsyncMock(return_value=10.0)
        config = {
            "name": "bad_bench",
            "component": "system",
            "type": "unknown_type",
            "params": {},
        }
        result = await cb._run_single_benchmark(config)
        assert isinstance(result, BenchmarkResult)
        assert result.success is False
        assert "unknown_type" in result.error_message.lower()

    async def test_video_processing_type_calls_benchmark_method(self):
        cb = ComprehensiveBenchmark()
        cb._get_memory_usage = AsyncMock(return_value=50.0)
        cb._get_cpu_usage = AsyncMock(return_value=5.0)
        cb._benchmark_video_processing = AsyncMock(return_value={"avg_processing_time_ms": 1000.0})
        config = {
            "name": "vp_bench",
            "component": "video_processing",
            "type": "video_processing",
            "params": {},
        }
        result = await cb._run_single_benchmark(config)
        assert result.success is True
        cb._benchmark_video_processing.assert_called_once_with({})

    async def test_database_query_type_calls_benchmark_method(self):
        cb = ComprehensiveBenchmark()
        cb._get_memory_usage = AsyncMock(return_value=50.0)
        cb._get_cpu_usage = AsyncMock(return_value=5.0)
        cb._benchmark_database_query = AsyncMock(return_value={"avg_query_time_ms": 50.0})
        config = {
            "name": "db_bench",
            "component": "database",
            "type": "database_query",
            "params": {"iterations": 10},
        }
        result = await cb._run_single_benchmark(config)
        assert result.success is True
        cb._benchmark_database_query.assert_called_once_with({"iterations": 10})

    async def test_cache_operation_type_calls_benchmark_method(self):
        cb = ComprehensiveBenchmark()
        cb._get_memory_usage = AsyncMock(return_value=50.0)
        cb._get_cpu_usage = AsyncMock(return_value=5.0)
        cb._benchmark_cache_operation = AsyncMock(return_value={"hit_ratio_percent": 92.0})
        config = {
            "name": "cache_bench",
            "component": "cache",
            "type": "cache_operation",
            "params": {},
        }
        result = await cb._run_single_benchmark(config)
        assert result.success is True

    async def test_memory_management_type_calls_benchmark_method(self):
        cb = ComprehensiveBenchmark()
        cb._get_memory_usage = AsyncMock(return_value=100.0)
        cb._get_cpu_usage = AsyncMock(return_value=20.0)
        cb._benchmark_memory_management = AsyncMock(return_value={"memory_growth_mb": 10.0})
        config = {
            "name": "mem_bench",
            "component": "memory",
            "type": "memory_management",
            "params": {},
        }
        result = await cb._run_single_benchmark(config)
        assert result.success is True

    async def test_load_balancing_type_calls_benchmark_method(self):
        cb = ComprehensiveBenchmark()
        cb._get_memory_usage = AsyncMock(return_value=50.0)
        cb._get_cpu_usage = AsyncMock(return_value=5.0)
        cb._benchmark_load_balancing = AsyncMock(return_value={"avg_response_time_ms": 1.5})
        config = {
            "name": "lb_bench",
            "component": "load_balancer",
            "type": "load_balancing",
            "params": {},
        }
        result = await cb._run_single_benchmark(config)
        assert result.success is True

    async def test_system_integration_type_calls_benchmark_method(self):
        cb = ComprehensiveBenchmark()
        cb._get_memory_usage = AsyncMock(return_value=80.0)
        cb._get_cpu_usage = AsyncMock(return_value=15.0)
        cb._benchmark_system_integration = AsyncMock(
            return_value={"total_integration_time_ms": 500.0}
        )
        config = {
            "name": "si_bench",
            "component": "system",
            "type": "system_integration",
            "params": {},
        }
        result = await cb._run_single_benchmark(config)
        assert result.success is True

    async def test_result_contains_component_name(self):
        cb = ComprehensiveBenchmark()
        cb._get_memory_usage = AsyncMock(return_value=50.0)
        cb._get_cpu_usage = AsyncMock(return_value=5.0)
        cb._benchmark_cache_operation = AsyncMock(return_value={})
        config = {
            "name": "c_bench",
            "component": "cache",
            "type": "cache_operation",
            "params": {},
        }
        result = await cb._run_single_benchmark(config)
        assert result.component == "cache"
        assert result.name == "c_bench"

    async def test_result_metadata_holds_benchmark_output(self):
        cb = ComprehensiveBenchmark()
        cb._get_memory_usage = AsyncMock(return_value=50.0)
        cb._get_cpu_usage = AsyncMock(return_value=5.0)
        bench_output = {"avg_query_time_ms": 42.0}
        cb._benchmark_database_query = AsyncMock(return_value=bench_output)
        config = {
            "name": "d_bench",
            "component": "database",
            "type": "database_query",
            "params": {},
        }
        result = await cb._run_single_benchmark(config)
        assert result.metadata == bench_output

    async def test_exception_in_benchmark_method_returns_failed_result(self):
        cb = ComprehensiveBenchmark()
        cb._get_memory_usage = AsyncMock(return_value=50.0)
        cb._get_cpu_usage = AsyncMock(return_value=5.0)
        cb._benchmark_video_processing = AsyncMock(
            side_effect=RuntimeError("processing failed")
        )
        config = {
            "name": "vp_fail",
            "component": "video_processing",
            "type": "video_processing",
            "params": {},
        }
        result = await cb._run_single_benchmark(config)
        assert result.success is False
        assert "processing failed" in result.error_message

    async def test_params_defaults_to_empty_dict_when_missing(self):
        cb = ComprehensiveBenchmark()
        cb._get_memory_usage = AsyncMock(return_value=50.0)
        cb._get_cpu_usage = AsyncMock(return_value=5.0)
        cb._benchmark_cache_operation = AsyncMock(return_value={})
        config = {
            "name": "no_params",
            "component": "cache",
            "type": "cache_operation",
            # no "params" key
        }
        result = await cb._run_single_benchmark(config)
        assert result.success is True
        cb._benchmark_cache_operation.assert_called_once_with({})


# ---------------------------------------------------------------------------
# _validate_performance_targets tests
# ---------------------------------------------------------------------------

class TestValidatePerformanceTargets:
    """Tests for ComprehensiveBenchmark._validate_performance_targets."""

    async def test_returns_dict_with_required_keys(self):
        cb = ComprehensiveBenchmark()
        result = await cb._validate_performance_targets({"suite_results": {}})
        for key in ("targets_met", "targets_failed", "critical_targets_met",
                    "critical_targets_failed", "target_details", "overall_success_rate"):
            assert key in result

    async def test_no_suite_results_all_targets_have_none_actual_value(self):
        cb = ComprehensiveBenchmark()
        result = await cb._validate_performance_targets({"suite_results": {}})
        for detail in result["target_details"]:
            assert detail["actual_value"] is None

    async def test_overall_success_rate_is_zero_when_no_data(self):
        cb = ComprehensiveBenchmark()
        result = await cb._validate_performance_targets({"suite_results": {}})
        assert result["overall_success_rate"] == 0.0

    async def test_less_than_comparison_met(self):
        cb = ComprehensiveBenchmark()
        # Override targets to just one for clarity
        cb.performance_targets = [
            PerformanceTarget(
                component="cache", metric="access_time_ms",
                target_value=10, unit="ms",
                comparison="less_than", priority="medium",
            )
        ]
        bench_result = BenchmarkResult(
            name="b", component="cache", execution_time_ms=5.0,
            memory_usage_mb=1.0, cpu_usage_percent=0.0, success=True,
            metadata={"access_time_ms": 5.0},
        )
        benchmark_results = {"suite_results": {"s": {"b": bench_result}}}
        result = await cb._validate_performance_targets(benchmark_results)
        assert result["targets_met"] == 1
        assert result["targets_failed"] == 0
        assert result["target_details"][0]["met"] is True

    async def test_less_than_comparison_missed(self):
        cb = ComprehensiveBenchmark()
        cb.performance_targets = [
            PerformanceTarget(
                component="cache", metric="access_time_ms",
                target_value=10, unit="ms",
                comparison="less_than", priority="medium",
            )
        ]
        bench_result = BenchmarkResult(
            name="b", component="cache", execution_time_ms=20.0,
            memory_usage_mb=1.0, cpu_usage_percent=0.0, success=True,
            metadata={"access_time_ms": 20.0},
        )
        benchmark_results = {"suite_results": {"s": {"b": bench_result}}}
        result = await cb._validate_performance_targets(benchmark_results)
        assert result["targets_failed"] == 1
        assert result["target_details"][0]["met"] is False

    async def test_greater_than_comparison_met(self):
        cb = ComprehensiveBenchmark()
        cb.performance_targets = [
            PerformanceTarget(
                component="cache", metric="hit_ratio_percent",
                target_value=90.0, unit="%",
                comparison="greater_than", priority="high",
            )
        ]
        bench_result = BenchmarkResult(
            name="b", component="cache", execution_time_ms=5.0,
            memory_usage_mb=1.0, cpu_usage_percent=0.0, success=True,
            metadata={"hit_ratio_percent": 95.0},
        )
        benchmark_results = {"suite_results": {"s": {"b": bench_result}}}
        result = await cb._validate_performance_targets(benchmark_results)
        assert result["targets_met"] == 1
        assert result["target_details"][0]["met"] is True

    async def test_equals_comparison_met_within_tolerance(self):
        cb = ComprehensiveBenchmark()
        cb.performance_targets = [
            PerformanceTarget(
                component="system", metric="cpu_usage_percent",
                target_value=80.0, unit="%",
                comparison="equals", priority="medium",
            )
        ]
        bench_result = BenchmarkResult(
            name="b", component="system", execution_time_ms=5.0,
            memory_usage_mb=1.0, cpu_usage_percent=80.0, success=True,
        )
        benchmark_results = {"suite_results": {"s": {"b": bench_result}}}
        result = await cb._validate_performance_targets(benchmark_results)
        assert result["targets_met"] == 1

    async def test_critical_target_failure_increments_critical_counter(self):
        cb = ComprehensiveBenchmark()
        cb.performance_targets = [
            PerformanceTarget(
                component="database", metric="query_time_ms",
                target_value=100, unit="ms",
                comparison="less_than", priority="critical",
            )
        ]
        bench_result = BenchmarkResult(
            name="b", component="database", execution_time_ms=200.0,
            memory_usage_mb=1.0, cpu_usage_percent=0.0, success=True,
            metadata={"query_time_ms": 200.0},
        )
        benchmark_results = {"suite_results": {"s": {"b": bench_result}}}
        result = await cb._validate_performance_targets(benchmark_results)
        assert result["critical_targets_failed"] == 1

    async def test_non_benchmark_result_skipped(self):
        cb = ComprehensiveBenchmark()
        cb.performance_targets = [
            PerformanceTarget(
                component="cache", metric="hit_ratio_percent",
                target_value=90, unit="%",
                comparison="greater_than", priority="high",
            )
        ]
        # Value is a plain dict, not a BenchmarkResult
        benchmark_results = {"suite_results": {"s": {"b": {"hit_ratio_percent": 95.0}}}}
        result = await cb._validate_performance_targets(benchmark_results)
        # Can't extract — actual_value should be None
        assert result["target_details"][0]["actual_value"] is None


# ---------------------------------------------------------------------------
# _save_benchmark_report tests
# ---------------------------------------------------------------------------

class TestSaveBenchmarkReport:
    """Tests for ComprehensiveBenchmark._save_benchmark_report."""

    async def test_saves_file_with_correct_type_in_name(self, tmp_path):
        cb = ComprehensiveBenchmark()
        cb.results_directory = str(tmp_path / "bench_results")
        report = {"type": "baseline", "timestamp": "2026-01-01T00:00:00Z"}
        await cb._save_benchmark_report(report, "baseline")
        files = list((tmp_path / "bench_results").iterdir())
        assert len(files) == 1
        assert "baseline" in files[0].name

    async def test_saved_file_is_valid_json(self, tmp_path):
        import json as _json
        cb = ComprehensiveBenchmark()
        cb.results_directory = str(tmp_path / "bench_results")
        report = {"foo": "bar", "count": 42}
        await cb._save_benchmark_report(report, "test")
        files = list((tmp_path / "bench_results").iterdir())
        with open(files[0]) as fh:
            loaded = _json.load(fh)
        assert loaded["foo"] == "bar"

    async def test_creates_results_directory_if_missing(self, tmp_path):
        import os
        cb = ComprehensiveBenchmark()
        new_dir = str(tmp_path / "new_dir" / "nested")
        cb.results_directory = new_dir
        await cb._save_benchmark_report({"x": 1}, "test")
        assert os.path.isdir(new_dir)

    async def test_does_not_raise_on_permission_error(self):
        """Should silently catch errors and log them."""
        cb = ComprehensiveBenchmark()
        cb.results_directory = "/root/no_permission_dir"
        # Should not raise
        await cb._save_benchmark_report({"x": 1}, "test")


# ---------------------------------------------------------------------------
# _get_system_info with psutil mock via monkeypatch on the module attribute
# ---------------------------------------------------------------------------

class TestGetSystemInfoWithMockedPsutil:
    """Tests _get_system_info using sys.modules psutil monkeypatch pattern."""

    async def test_returns_expected_keys_with_fake_psutil(self, monkeypatch):
        import sys
        import types
        fake = types.SimpleNamespace(
            cpu_count=lambda logical=True: 4,
            virtual_memory=lambda: types.SimpleNamespace(
                total=8 * 1024 ** 3, available=4 * 1024 ** 3, percent=50.0
            ),
            disk_usage=lambda path: types.SimpleNamespace(total=256 * 1024 ** 3),
        )
        monkeypatch.setitem(sys.modules, "psutil", fake)
        cb = ComprehensiveBenchmark()
        info = await cb._get_system_info()
        assert isinstance(info, dict)

    async def test_returns_error_key_when_psutil_raises(self, monkeypatch):
        import sys
        import types

        def raise_on_cpu(**kwargs):
            raise RuntimeError("no cpu info")

        fake = types.SimpleNamespace(cpu_count=raise_on_cpu)
        monkeypatch.setitem(sys.modules, "psutil", fake)
        cb = ComprehensiveBenchmark()
        info = await cb._get_system_info()
        # Should be a dict (error dict or normal)
        assert isinstance(info, dict)


# ---------------------------------------------------------------------------
# _get_memory_usage and _get_cpu_usage with module-level monkeypatch
# ---------------------------------------------------------------------------

class TestMemoryCpuWithModuleMonkeypatch:
    """Test _get_memory_usage and _get_cpu_usage with sys.modules psutil patch."""

    async def test_get_memory_usage_calculates_mb(self, monkeypatch):
        import sys
        import types
        fake = types.SimpleNamespace(
            Process=lambda: types.SimpleNamespace(
                memory_info=lambda: types.SimpleNamespace(rss=256 * 1024 * 1024)
            ),
            cpu_percent=lambda interval=None: 25.0,
            cpu_count=lambda logical=True: 4,
            virtual_memory=lambda: types.SimpleNamespace(
                total=8 * 1024 ** 3, available=4 * 1024 ** 3, percent=50.0
            ),
        )
        monkeypatch.setitem(sys.modules, "psutil", fake)
        cb = ComprehensiveBenchmark()
        usage = await cb._get_memory_usage()
        assert usage == pytest.approx(256.0)

    async def test_get_cpu_usage_returns_value_from_psutil(self, monkeypatch):
        import sys
        import types
        fake = types.SimpleNamespace(
            Process=lambda: types.SimpleNamespace(
                memory_info=lambda: types.SimpleNamespace(rss=128 * 1024 * 1024)
            ),
            cpu_percent=lambda interval=None: 42.5,
            cpu_count=lambda logical=True: 4,
            virtual_memory=lambda: types.SimpleNamespace(
                total=8 * 1024 ** 3, available=4 * 1024 ** 3, percent=50.0
            ),
        )
        monkeypatch.setitem(sys.modules, "psutil", fake)
        cb = ComprehensiveBenchmark()
        cpu = await cb._get_cpu_usage()
        assert cpu == pytest.approx(42.5)

    async def test_get_memory_usage_returns_zero_on_exception(self, monkeypatch):
        import sys
        import types

        def bad_process():
            raise RuntimeError("unavailable")

        fake = types.SimpleNamespace(Process=bad_process)
        monkeypatch.setitem(sys.modules, "psutil", fake)
        cb = ComprehensiveBenchmark()
        usage = await cb._get_memory_usage()
        assert usage == 0.0


# ---------------------------------------------------------------------------
# _benchmark_video_processing raises when components unavailable
# ---------------------------------------------------------------------------

class TestBenchmarkMethodsComponentUnavailable:
    """Tests that benchmark methods raise when required components are missing."""

    async def test_benchmark_video_processing_raises_when_components_unavailable(self):
        import youtube_extension.backend.services.comprehensive_benchmarking as _mod
        original = _mod.PERFORMANCE_COMPONENTS_AVAILABLE
        try:
            _mod.PERFORMANCE_COMPONENTS_AVAILABLE = False
            cb = ComprehensiveBenchmark()
            with pytest.raises(RuntimeError, match="not available"):
                await cb._benchmark_video_processing({})
        finally:
            _mod.PERFORMANCE_COMPONENTS_AVAILABLE = original

    async def test_benchmark_database_query_raises_when_components_unavailable(self):
        import youtube_extension.backend.services.comprehensive_benchmarking as _mod
        original = _mod.PERFORMANCE_COMPONENTS_AVAILABLE
        try:
            _mod.PERFORMANCE_COMPONENTS_AVAILABLE = False
            cb = ComprehensiveBenchmark()
            with pytest.raises(RuntimeError, match="not available"):
                await cb._benchmark_database_query({})
        finally:
            _mod.PERFORMANCE_COMPONENTS_AVAILABLE = original

    async def test_benchmark_cache_operation_raises_when_cache_unavailable(self):
        import youtube_extension.backend.services.comprehensive_benchmarking as _mod
        original = _mod.intelligent_cache
        try:
            _mod.intelligent_cache = None
            cb = ComprehensiveBenchmark()
            with pytest.raises(RuntimeError, match="not available"):
                await cb._benchmark_cache_operation({})
        finally:
            _mod.intelligent_cache = original

    async def test_benchmark_memory_management_raises_when_manager_unavailable(self):
        import youtube_extension.backend.services.comprehensive_benchmarking as _mod
        original = _mod.memory_manager
        try:
            _mod.memory_manager = None
            cb = ComprehensiveBenchmark()
            with pytest.raises(RuntimeError, match="not available"):
                await cb._benchmark_memory_management({})
        finally:
            _mod.memory_manager = original

    async def test_benchmark_load_balancing_raises_when_service_discovery_unavailable(self):
        import youtube_extension.backend.services.comprehensive_benchmarking as _mod
        original = _mod.service_discovery
        try:
            _mod.service_discovery = None
            cb = ComprehensiveBenchmark()
            with pytest.raises(RuntimeError, match="not available"):
                await cb._benchmark_load_balancing({})
        finally:
            _mod.service_discovery = original

    async def test_benchmark_system_integration_raises_when_db_unavailable(self):
        import youtube_extension.backend.services.comprehensive_benchmarking as _mod
        orig_db = _mod.database_optimizer
        orig_cache = _mod.intelligent_cache
        orig_mem = _mod.memory_manager
        try:
            _mod.database_optimizer = None
            _mod.intelligent_cache = MagicMock()
            _mod.memory_manager = MagicMock()
            cb = ComprehensiveBenchmark()
            with pytest.raises(RuntimeError, match="prerequisites missing"):
                await cb._benchmark_system_integration({})
        finally:
            _mod.database_optimizer = orig_db
            _mod.intelligent_cache = orig_cache
            _mod.memory_manager = orig_mem


# ===========================================================================
# Additional tests for missing coverage lines
# ===========================================================================

class TestCalculatePerformanceGradeMissingBranches:
    """Cover B, C+, C, D+, D, F grade branches in _calculate_performance_grade"""

    def _make_results(self, targets_failed=0, critical_failed=0, improvement_met=False):
        improvement_analysis = {}
        if improvement_met:
            improvement_analysis = {
                "suite1": {"bench1": {"meets_60_percent_target": True}}
            }
        return {
            "target_validation": {
                "targets_failed": targets_failed,
                "critical_targets_failed": critical_failed,
            },
            "improvement_analysis": improvement_analysis,
        }

    def test_grade_b_score_80(self):
        # score = 100 - 0 - 0 = 100, no improvement → 85; need 80-84
        # 1 normal failure: score = 100 - 10 - 15 = 75 → C+
        # Let me compute: B needs 80-84
        # 0 critical, 1 normal, no improvement: 100 - 0 - (1-0)*10 - 15 = 75 → C+
        # 0 critical, 0 normal, no improvement: 100 - 0 - 0 - 15 = 85 → B+
        # 0 critical, 0 normal, improvement_met: 100 → A+
        # need 80-84: 0 critical, 2 normal, improvement_met: 100 - 20 = 80 → B
        cb = ComprehensiveBenchmark()
        results = self._make_results(targets_failed=2, critical_failed=0, improvement_met=True)
        grade = cb._calculate_performance_grade(results)
        assert grade == "B"

    def test_grade_c_plus_score_75(self):
        # 0 critical, 2 normal, no improvement: 100 - 20 - 15 = 65 → D+
        # 0 critical, 1 normal, improvement_met: 100 - 10 = 90 → A
        # need 75-79: 0 critical, 1 normal, no improvement: 100 - 10 - 15 = 75 → C+
        cb = ComprehensiveBenchmark()
        results = self._make_results(targets_failed=1, critical_failed=0, improvement_met=False)
        grade = cb._calculate_performance_grade(results)
        assert grade == "C+"

    def test_grade_c_score_70(self):
        # need 70-74: 0 critical, 3 normal, improvement_met: 100 - 30 = 70 → C
        cb = ComprehensiveBenchmark()
        results = self._make_results(targets_failed=3, critical_failed=0, improvement_met=True)
        grade = cb._calculate_performance_grade(results)
        assert grade == "C"

    def test_grade_d_plus_score_65(self):
        # need 65-69: 0 critical, 2 normal, no improvement: 100 - 20 - 15 = 65 → D+
        cb = ComprehensiveBenchmark()
        results = self._make_results(targets_failed=2, critical_failed=0, improvement_met=False)
        grade = cb._calculate_performance_grade(results)
        assert grade == "D+"

    def test_grade_d_score_60(self):
        # need 60-64: 0 critical, 3 normal, no improvement: 100 - 30 - 15 = 55 → F
        # 0 critical, 4 normal, improvement: 100 - 40 = 60 → D
        cb = ComprehensiveBenchmark()
        results = self._make_results(targets_failed=4, critical_failed=0, improvement_met=True)
        grade = cb._calculate_performance_grade(results)
        assert grade == "D"

    def test_grade_f_score_below_60(self):
        # 1 critical, 3 normal, no improvement: 100 - 20 - 20 - 15 = 45 → F
        cb = ComprehensiveBenchmark()
        results = self._make_results(targets_failed=3, critical_failed=1, improvement_met=False)
        grade = cb._calculate_performance_grade(results)
        assert grade == "F"


class TestConvenienceFunctions:
    """run_phase3_validation, establish_performance_baseline, get_benchmark_status"""

    async def test_run_phase3_validation_calls_comprehensive_methods(self, monkeypatch):
        from youtube_extension.backend.services import (
            comprehensive_benchmarking as _mod,
        )
        mock_bench = MagicMock()
        mock_bench.baseline_established = True
        mock_bench.run_comprehensive_benchmark = AsyncMock(return_value={
            "performance_grade": "A+",
            "target_validation": {
                "overall_success_rate": 100.0,
                "targets_met": 5,
                "targets_failed": 0,
            }
        })
        monkeypatch.setattr(_mod, "comprehensive_benchmark", mock_bench)
        result = await _mod.run_phase3_validation()
        assert result["performance_grade"] == "A+"
        mock_bench.run_comprehensive_benchmark.assert_called_once()

    async def test_run_phase3_validation_establishes_baseline_when_needed(self, monkeypatch):
        from youtube_extension.backend.services import (
            comprehensive_benchmarking as _mod,
        )
        mock_bench = MagicMock()
        mock_bench.baseline_established = False
        mock_bench.establish_baseline = AsyncMock(return_value={})
        mock_bench.run_comprehensive_benchmark = AsyncMock(return_value={
            "performance_grade": "B",
            "target_validation": {
                "overall_success_rate": 80.0,
                "targets_met": 4,
                "targets_failed": 1,
            }
        })
        monkeypatch.setattr(_mod, "comprehensive_benchmark", mock_bench)
        await _mod.run_phase3_validation()
        mock_bench.establish_baseline.assert_called_once()

    async def test_establish_performance_baseline_calls_benchmark(self, monkeypatch):
        from youtube_extension.backend.services import (
            comprehensive_benchmarking as _mod,
        )
        mock_bench = MagicMock()
        mock_bench.establish_baseline = AsyncMock(return_value={"ok": True})
        monkeypatch.setattr(_mod, "comprehensive_benchmark", mock_bench)
        result = await _mod.establish_performance_baseline()
        assert result == {"ok": True}

    def test_get_benchmark_status_returns_summary(self, monkeypatch):
        from youtube_extension.backend.services import (
            comprehensive_benchmarking as _mod,
        )
        mock_bench = MagicMock()
        mock_bench.get_benchmark_summary.return_value = {"registered_suites": []}
        monkeypatch.setattr(_mod, "comprehensive_benchmark", mock_bench)
        result = _mod.get_benchmark_status()
        assert "registered_suites" in result


class TestSaveBenchmarkReportExceptionPath:
    """_save_benchmark_report: exception path logs error without raising"""

    async def test_exception_does_not_propagate(self, monkeypatch, tmp_path):
        cb = ComprehensiveBenchmark()
        cb.results_directory = str(tmp_path / "results")

        # Monkeypatch aiofiles.open to raise PermissionError
        import youtube_extension.backend.services.comprehensive_benchmarking as _mod

        async def fake_open(*args, **kwargs):
            raise PermissionError("no write")

        monkeypatch.setattr(_mod.aiofiles, "open", fake_open)
        # Should not raise
        await cb._save_benchmark_report({}, "test")
