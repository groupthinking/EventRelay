"""
Comprehensive pytest tests for performance_benchmark_system.py
"""

import asyncio
import threading
from collections import deque
from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from youtube_extension.backend.services.performance_benchmark_system import (
    BenchmarkResult,
    PerformanceBenchmarkSystem,
    PerformanceTarget,
    get_benchmark_report,
)


# ---------------------------------------------------------------------------
# BenchmarkResult dataclass tests
# ---------------------------------------------------------------------------

class TestBenchmarkResult:
    def test_required_fields(self):
        br = BenchmarkResult(
            benchmark_name="test_bench",
            component="video_processing",
            execution_time_ms=500.0,
            success=True,
            iterations=3,
        )
        assert br.benchmark_name == "test_bench"
        assert br.component == "video_processing"
        assert br.execution_time_ms == 500.0
        assert br.success is True
        assert br.iterations == 3

    def test_timestamp_auto_set_when_none(self):
        br = BenchmarkResult(
            benchmark_name="x",
            component="cache",
            execution_time_ms=10.0,
            success=True,
            iterations=1,
        )
        assert br.timestamp is not None
        assert isinstance(br.timestamp, datetime)

    def test_timestamp_timezone_utc(self):
        br = BenchmarkResult(
            benchmark_name="x",
            component="cache",
            execution_time_ms=10.0,
            success=True,
            iterations=1,
        )
        assert br.timestamp.tzinfo is not None

    def test_timestamp_preserved_when_provided(self):
        fixed_ts = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        br = BenchmarkResult(
            benchmark_name="x",
            component="cache",
            execution_time_ms=10.0,
            success=True,
            iterations=1,
            timestamp=fixed_ts,
        )
        assert br.timestamp == fixed_ts

    def test_metadata_defaults_to_empty_dict(self):
        br = BenchmarkResult(
            benchmark_name="x",
            component="database",
            execution_time_ms=50.0,
            success=True,
            iterations=1,
        )
        assert br.metadata == {}

    def test_metadata_preserved_when_provided(self):
        meta = {"query": "SELECT 1", "rows": 42}
        br = BenchmarkResult(
            benchmark_name="x",
            component="database",
            execution_time_ms=50.0,
            success=True,
            iterations=1,
            metadata=meta,
        )
        assert br.metadata == meta

    def test_improvement_percent_calculated_from_baseline(self):
        # baseline=100, execution=40 => improvement = (100-40)/100 * 100 = 60%
        br = BenchmarkResult(
            benchmark_name="x",
            component="video_processing",
            execution_time_ms=40.0,
            success=True,
            iterations=1,
            baseline_time_ms=100.0,
        )
        assert abs(br.improvement_percent - 60.0) < 1e-9

    def test_improvement_percent_zero_when_no_baseline(self):
        br = BenchmarkResult(
            benchmark_name="x",
            component="video_processing",
            execution_time_ms=40.0,
            success=True,
            iterations=1,
        )
        assert br.improvement_percent == 0.0

    def test_improvement_percent_zero_when_baseline_is_zero(self):
        br = BenchmarkResult(
            benchmark_name="x",
            component="video_processing",
            execution_time_ms=40.0,
            success=True,
            iterations=1,
            baseline_time_ms=0.0,
        )
        # baseline_time_ms=0 is falsy, so the condition is skipped
        assert br.improvement_percent == 0.0

    def test_negative_improvement_when_slower_than_baseline(self):
        # execution > baseline => negative improvement
        br = BenchmarkResult(
            benchmark_name="x",
            component="video_processing",
            execution_time_ms=120.0,
            success=True,
            iterations=1,
            baseline_time_ms=100.0,
        )
        assert br.improvement_percent < 0.0

    def test_optional_baseline_defaults_to_none(self):
        br = BenchmarkResult(
            benchmark_name="x",
            component="cache",
            execution_time_ms=5.0,
            success=False,
            iterations=2,
        )
        assert br.baseline_time_ms is None


# ---------------------------------------------------------------------------
# PerformanceTarget dataclass tests
# ---------------------------------------------------------------------------

class TestPerformanceTarget:
    def test_required_fields(self):
        pt = PerformanceTarget(
            component="video_processing",
            metric="processing_time_ms",
            target_value=24000.0,
            unit="ms",
            comparison="less_than",
        )
        assert pt.component == "video_processing"
        assert pt.metric == "processing_time_ms"
        assert pt.target_value == 24000.0
        assert pt.unit == "ms"
        assert pt.comparison == "less_than"

    def test_optional_fields_default_to_none(self):
        pt = PerformanceTarget(
            component="cache",
            metric="hit_rate_percent",
            target_value=80.0,
            unit="%",
            comparison="greater_than",
        )
        assert pt.baseline_value is None
        assert pt.improvement_target_percent is None

    def test_priority_default_is_medium(self):
        pt = PerformanceTarget(
            component="frontend",
            metric="load_time_ms",
            target_value=2000.0,
            unit="ms",
            comparison="less_than",
        )
        assert pt.priority == "medium"

    def test_priority_can_be_set(self):
        pt = PerformanceTarget(
            component="database",
            metric="query_response_time_ms",
            target_value=100.0,
            unit="ms",
            comparison="less_than",
            priority="critical",
        )
        assert pt.priority == "critical"


# ---------------------------------------------------------------------------
# PerformanceBenchmarkSystem.__init__ tests
# ---------------------------------------------------------------------------

class TestPerformanceBenchmarkSystemInit:
    def test_creates_instance(self):
        system = PerformanceBenchmarkSystem()
        assert system is not None

    def test_benchmark_history_is_deque(self):
        system = PerformanceBenchmarkSystem()
        assert isinstance(system.benchmark_history, deque)

    def test_benchmark_history_starts_empty(self):
        system = PerformanceBenchmarkSystem()
        assert len(system.benchmark_history) == 0

    def test_benchmark_history_max_len_1000(self):
        system = PerformanceBenchmarkSystem()
        assert system.benchmark_history.maxlen == 1000

    def test_performance_targets_is_list(self):
        system = PerformanceBenchmarkSystem()
        assert isinstance(system.performance_targets, list)

    def test_performance_targets_non_empty(self):
        system = PerformanceBenchmarkSystem()
        assert len(system.performance_targets) > 0

    def test_performance_targets_are_performance_target_instances(self):
        system = PerformanceBenchmarkSystem()
        for target in system.performance_targets:
            assert isinstance(target, PerformanceTarget)

    def test_baseline_results_dict(self):
        system = PerformanceBenchmarkSystem()
        assert isinstance(system.baseline_results, dict)
        assert len(system.baseline_results) == 0

    def test_current_results_dict(self):
        system = PerformanceBenchmarkSystem()
        assert isinstance(system.current_results, dict)

    def test_monitoring_enabled_true(self):
        system = PerformanceBenchmarkSystem()
        assert system.monitoring_enabled is True

    def test_benchmark_lock_is_threading_lock(self):
        system = PerformanceBenchmarkSystem()
        assert isinstance(system.benchmark_lock, type(threading.Lock()))

    def test_test_video_urls_is_list(self):
        system = PerformanceBenchmarkSystem()
        assert isinstance(system.test_video_urls, list)
        assert len(system.test_video_urls) > 0

    def test_test_queries_is_list_of_tuples(self):
        system = PerformanceBenchmarkSystem()
        assert isinstance(system.test_queries, list)
        for item in system.test_queries:
            assert isinstance(item, tuple)
            assert len(item) == 2


# ---------------------------------------------------------------------------
# PerformanceBenchmarkSystem.get_benchmark_history_summary tests
# ---------------------------------------------------------------------------

class TestGetBenchmarkHistorySummary:
    def test_returns_dict(self):
        system = PerformanceBenchmarkSystem()
        result = system.get_benchmark_history_summary()
        assert isinstance(result, dict)

    def test_empty_history_returns_message(self):
        system = PerformanceBenchmarkSystem()
        result = system.get_benchmark_history_summary()
        assert "message" in result

    def test_with_history_has_total_benchmarks_key(self):
        system = PerformanceBenchmarkSystem()
        # Inject a fake benchmark into history
        system.benchmark_history.append({
            "timestamp": "2025-01-01T00:00:00+00:00",
            "overall_assessment": {"overall_grade": "A", "targets_met": 3},
        })
        result = system.get_benchmark_history_summary()
        assert "total_benchmarks" in result

    def test_with_history_has_recent_benchmarks_key(self):
        system = PerformanceBenchmarkSystem()
        system.benchmark_history.append({
            "timestamp": "2025-01-01T00:00:00+00:00",
            "overall_assessment": {"overall_grade": "B", "targets_met": 2},
        })
        result = system.get_benchmark_history_summary()
        assert "recent_benchmarks" in result

    def test_with_history_total_count_matches(self):
        system = PerformanceBenchmarkSystem()
        for i in range(5):
            system.benchmark_history.append({
                "timestamp": f"2025-01-0{i+1}T00:00:00+00:00",
                "overall_assessment": {"overall_grade": "A", "targets_met": 4},
            })
        result = system.get_benchmark_history_summary()
        assert result["total_benchmarks"] == 5

    def test_with_history_latest_benchmark_key(self):
        system = PerformanceBenchmarkSystem()
        entry = {
            "timestamp": "2025-06-01T00:00:00+00:00",
            "overall_assessment": {"overall_grade": "A+", "targets_met": 5},
        }
        system.benchmark_history.append(entry)
        result = system.get_benchmark_history_summary()
        assert result["latest_benchmark"] == entry

    def test_recent_benchmarks_capped_at_10(self):
        system = PerformanceBenchmarkSystem()
        for i in range(15):
            system.benchmark_history.append({
                "timestamp": f"2025-01-{i+1:02d}T00:00:00+00:00",
                "overall_assessment": {"overall_grade": "A", "targets_met": 3},
            })
        result = system.get_benchmark_history_summary()
        assert result["recent_benchmarks"] <= 10

    def test_trends_key_present_with_history(self):
        system = PerformanceBenchmarkSystem()
        system.benchmark_history.append({
            "timestamp": "2025-01-01T00:00:00+00:00",
            "overall_assessment": {"overall_grade": "B", "targets_met": 2},
        })
        result = system.get_benchmark_history_summary()
        assert "trends" in result


# ---------------------------------------------------------------------------
# PerformanceBenchmarkSystem._generate_overall_assessment tests
# ---------------------------------------------------------------------------

class TestGenerateOverallAssessment:
    def setup_method(self):
        self.system = PerformanceBenchmarkSystem()

    def _make_results(self, target_met: bool) -> dict:
        return {
            "performance_summary": {"target_met": target_met}
        }

    def test_returns_dict(self):
        result = self.system._generate_overall_assessment({})
        assert isinstance(result, dict)

    def test_empty_components_score_zero(self):
        result = self.system._generate_overall_assessment({})
        assert result["overall_score"] == 0
        assert result["overall_grade"] == "F"

    def test_all_targets_met_score_100(self):
        components = {
            "video_processing": self._make_results(True),
            "database": self._make_results(True),
            "frontend": self._make_results(True),
            "memory": self._make_results(True),
            "cache": self._make_results(True),
        }
        result = self.system._generate_overall_assessment(components)
        assert result["overall_score"] == 100.0

    def test_all_targets_met_grade_A_plus(self):
        components = {f"c{i}": self._make_results(True) for i in range(5)}
        result = self.system._generate_overall_assessment(components)
        assert result["overall_grade"] == "A+"

    def test_no_targets_met_grade_F(self):
        components = {f"c{i}": self._make_results(False) for i in range(5)}
        result = self.system._generate_overall_assessment(components)
        assert result["overall_grade"] == "F"

    def test_mixed_targets_met(self):
        components = {
            "video_processing": self._make_results(True),
            "database": self._make_results(True),
            "frontend": self._make_results(False),
            "memory": self._make_results(False),
            "cache": self._make_results(False),
        }
        result = self.system._generate_overall_assessment(components)
        assert result["targets_met"] == 2
        assert result["total_targets"] == 5

    def test_component_with_error_counts_as_not_met(self):
        components = {
            "video_processing": {"error": "something broke"},
            "database": self._make_results(True),
        }
        result = self.system._generate_overall_assessment(components)
        assert result["targets_met"] == 1

    def test_phase_3_readiness_true_when_score_gte_80(self):
        # 4/5 = 80%
        components = {
            "video_processing": self._make_results(True),
            "database": self._make_results(True),
            "frontend": self._make_results(True),
            "memory": self._make_results(True),
            "cache": self._make_results(False),
        }
        result = self.system._generate_overall_assessment(components)
        assert result["phase_3_readiness"] is True

    def test_phase_3_readiness_false_when_score_lt_80(self):
        # 3/5 = 60%
        components = {
            "video_processing": self._make_results(True),
            "database": self._make_results(True),
            "frontend": self._make_results(True),
            "memory": self._make_results(False),
            "cache": self._make_results(False),
        }
        result = self.system._generate_overall_assessment(components)
        assert result["phase_3_readiness"] is False

    def test_summary_string_present(self):
        components = {"video_processing": self._make_results(True)}
        result = self.system._generate_overall_assessment(components)
        assert "summary" in result

    def test_component_grades_keys_match_input(self):
        components = {
            "video_processing": self._make_results(True),
            "database": self._make_results(False),
        }
        result = self.system._generate_overall_assessment(components)
        assert set(result["component_grades"].keys()) == {"video_processing", "database"}

    def test_component_grades_A_for_met_C_for_unmet(self):
        components = {
            "video_processing": self._make_results(True),
            "database": self._make_results(False),
        }
        result = self.system._generate_overall_assessment(components)
        assert result["component_grades"]["video_processing"] == "A"
        assert result["component_grades"]["database"] == "C"

    def test_component_grade_F_for_error(self):
        components = {
            "video_processing": {"error": "boom"},
        }
        result = self.system._generate_overall_assessment(components)
        assert result["component_grades"]["video_processing"] == "F"

    def test_grade_B_at_60_percent(self):
        # 3/5 = 60%
        components = {
            "a": self._make_results(True),
            "b": self._make_results(True),
            "c": self._make_results(True),
            "d": self._make_results(False),
            "e": self._make_results(False),
        }
        result = self.system._generate_overall_assessment(components)
        assert result["overall_grade"] == "B"

    def test_grade_A_at_80_percent(self):
        # 4/5 = 80%
        components = {
            "a": self._make_results(True),
            "b": self._make_results(True),
            "c": self._make_results(True),
            "d": self._make_results(True),
            "e": self._make_results(False),
        }
        result = self.system._generate_overall_assessment(components)
        assert result["overall_grade"] == "A"


# ---------------------------------------------------------------------------
# PerformanceBenchmarkSystem._validate_performance_targets tests
# ---------------------------------------------------------------------------

class TestValidatePerformanceTargets:
    def setup_method(self):
        self.system = PerformanceBenchmarkSystem()

    def test_returns_dict(self):
        result = self.system._validate_performance_targets({})
        assert isinstance(result, dict)

    def test_keys_use_component_metric_pattern(self):
        result = self.system._validate_performance_targets({})
        for key in result:
            assert "_" in key

    def test_error_component_sets_met_false(self):
        components = {
            "video_processing": {"error": "broken"},
        }
        result = self.system._validate_performance_targets(components)
        assert result["video_processing_processing_time_ms"]["met"] is False

    def test_video_processing_target_met_when_below_24000ms(self):
        components = {
            "video_processing": {
                "performance_summary": {"avg_processing_time_ms": 20000.0, "target_met": True}
            }
        }
        result = self.system._validate_performance_targets(components)
        key = "video_processing_processing_time_ms"
        assert result[key]["met"] is True

    def test_video_processing_target_not_met_when_above_24000ms(self):
        components = {
            "video_processing": {
                "performance_summary": {"avg_processing_time_ms": 50000.0, "target_met": False}
            }
        }
        result = self.system._validate_performance_targets(components)
        assert result["video_processing_processing_time_ms"]["met"] is False

    def test_cache_target_met_when_above_80_percent(self):
        components = {
            "cache": {
                "performance_summary": {"cache_hit_rate_percent": 90.0, "target_met": True}
            }
        }
        result = self.system._validate_performance_targets(components)
        assert result["cache_hit_rate_percent"]["met"] is True

    def test_cache_target_not_met_when_below_80_percent(self):
        components = {
            "cache": {
                "performance_summary": {"cache_hit_rate_percent": 70.0, "target_met": False}
            }
        }
        result = self.system._validate_performance_targets(components)
        assert result["cache_hit_rate_percent"]["met"] is False

    def test_database_target_met_when_below_100ms(self):
        components = {
            "database": {
                "performance_summary": {"avg_query_time_ms": 50.0, "target_met": True}
            }
        }
        result = self.system._validate_performance_targets(components)
        assert result["database_query_response_time_ms"]["met"] is True

    def test_database_target_not_met_when_above_100ms(self):
        components = {
            "database": {
                "performance_summary": {"avg_query_time_ms": 200.0, "target_met": False}
            }
        }
        result = self.system._validate_performance_targets(components)
        assert result["database_query_response_time_ms"]["met"] is False

    def test_validation_includes_target_value(self):
        result = self.system._validate_performance_targets({})
        for key, val in result.items():
            assert "target_value" in val

    def test_validation_includes_priority(self):
        result = self.system._validate_performance_targets({})
        for key, val in result.items():
            if "error" not in val:
                assert "priority" in val

    def test_improvement_percent_calculated_for_video_processing(self):
        # baseline=60000, actual=24000 => 60% improvement
        components = {
            "video_processing": {
                "performance_summary": {"avg_processing_time_ms": 24000.0, "target_met": True}
            }
        }
        result = self.system._validate_performance_targets(components)
        key = "video_processing_processing_time_ms"
        assert result[key].get("improvement_percent") is not None
        assert abs(result[key]["improvement_percent"] - 60.0) < 1e-6

    def test_missing_component_sets_met_false(self):
        # If no component data provided at all, actual_value will be None
        result = self.system._validate_performance_targets({})
        assert result["video_processing_processing_time_ms"]["met"] is False

    def test_memory_target_met_when_below_2048mb(self):
        components = {
            "memory": {
                "performance_summary": {"max_memory_usage_mb": 1024.0, "target_met": True}
            }
        }
        result = self.system._validate_performance_targets(components)
        assert result["memory_usage_mb"]["met"] is True

    def test_frontend_target_met_when_below_2000ms(self):
        components = {
            "frontend": {
                "performance_summary": {"avg_load_time_ms": 1500.0, "target_met": True}
            }
        }
        result = self.system._validate_performance_targets(components)
        assert result["frontend_load_time_ms"]["met"] is True


# ---------------------------------------------------------------------------
# PerformanceBenchmarkSystem._generate_benchmark_recommendations tests
# ---------------------------------------------------------------------------

class TestGenerateBenchmarkRecommendations:
    def setup_method(self):
        self.system = PerformanceBenchmarkSystem()

    def test_returns_list(self):
        result = self.system._generate_benchmark_recommendations({}, {})
        assert isinstance(result, list)

    def test_empty_inputs_return_empty_list(self):
        result = self.system._generate_benchmark_recommendations({}, {})
        assert result == []

    def test_error_component_generates_critical_recommendation(self):
        components = {
            "video_processing": {"error": "failed to connect"}
        }
        result = self.system._generate_benchmark_recommendations(components, {})
        assert len(result) > 0
        rec = result[0]
        assert rec["priority"] == "critical"
        assert rec["component"] == "video_processing"

    def test_recommendation_has_required_keys(self):
        components = {
            "database": {"error": "timeout"}
        }
        result = self.system._generate_benchmark_recommendations(components, {})
        for rec in result:
            assert "component" in rec
            assert "priority" in rec
            assert "issue" in rec
            assert "recommendation" in rec

    def test_no_recommendation_when_all_targets_met(self):
        components = {
            "video_processing": {"performance_summary": {"target_met": True}},
            "database": {"performance_summary": {"target_met": True}},
            "cache": {"performance_summary": {"target_met": True}},
        }
        result = self.system._generate_benchmark_recommendations(components, {})
        assert result == []

    def test_slow_video_processing_triggers_critical(self):
        components = {
            "video_processing": {
                "performance_summary": {
                    "target_met": False,
                    "avg_processing_time_ms": 35000,  # > 30s
                }
            }
        }
        result = self.system._generate_benchmark_recommendations(components, {})
        assert any(r["priority"] == "critical" for r in result)

    def test_video_processing_near_target_triggers_high(self):
        components = {
            "video_processing": {
                "performance_summary": {
                    "target_met": False,
                    "avg_processing_time_ms": 26000,  # > 24s but <= 30s
                }
            }
        }
        result = self.system._generate_benchmark_recommendations(components, {})
        assert any(r["priority"] == "high" for r in result)

    def test_low_cache_hit_rate_triggers_recommendation(self):
        components = {
            "cache": {
                "performance_summary": {
                    "target_met": False,
                    "cache_hit_rate_percent": 60.0,
                }
            }
        }
        result = self.system._generate_benchmark_recommendations(components, {})
        assert any(r["component"] == "cache" for r in result)

    def test_db_sub_100ms_below_90_triggers_critical(self):
        components = {
            "database": {
                "performance_summary": {
                    "target_met": False,
                    "sub_100ms_percent": 80.0,
                }
            }
        }
        result = self.system._generate_benchmark_recommendations(components, {})
        assert any(r["component"] == "database" and r["priority"] == "critical" for r in result)

    def test_high_memory_usage_triggers_recommendation(self):
        components = {
            "memory": {
                "performance_summary": {
                    "target_met": False,
                    "max_memory_usage_mb": 3000.0,
                }
            }
        }
        result = self.system._generate_benchmark_recommendations(components, {})
        assert any(r["component"] == "memory" for r in result)

    def test_video_improvement_target_miss_adds_overall_recommendation(self):
        target_validation = {
            "video_processing_processing_time_ms": {
                "met": False,
                "improvement_percent": 30.0,
                "meets_improvement_target": False,
            }
        }
        result = self.system._generate_benchmark_recommendations({}, target_validation)
        assert any(r["component"] == "overall" for r in result)

    def test_multiple_issues_generate_multiple_recommendations(self):
        components = {
            "video_processing": {"error": "broken"},
            "database": {"error": "timed out"},
            "cache": {"error": "redis down"},
        }
        result = self.system._generate_benchmark_recommendations(components, {})
        assert len(result) >= 3

    def test_frontend_slow_load_triggers_recommendation(self):
        components = {
            "frontend": {
                "performance_summary": {
                    "target_met": False,
                    "avg_load_time_ms": 3000.0,
                }
            }
        }
        result = self.system._generate_benchmark_recommendations(components, {})
        assert any(r["component"] == "frontend" for r in result)


# ---------------------------------------------------------------------------
# Module-level convenience function tests
# ---------------------------------------------------------------------------

class TestModuleLevelFunctions:
    def test_get_benchmark_report_returns_dict(self):
        result = get_benchmark_report()
        assert isinstance(result, dict)

    def test_get_benchmark_report_empty_message_on_fresh_system(self):
        # The module-level benchmark_system is a fresh instance (no history yet)
        result = get_benchmark_report()
        # Either "message" key (empty) or "total_benchmarks" key
        assert "message" in result or "total_benchmarks" in result


# ---------------------------------------------------------------------------
# Async benchmark component tests (fast paths / error paths only)
# ---------------------------------------------------------------------------

class TestBenchmarkMemoryEfficiency:
    async def test_memory_benchmark_returns_dict(self):
        system = PerformanceBenchmarkSystem()
        result = await system._benchmark_memory_efficiency(iterations=1)
        assert isinstance(result, dict)

    async def test_memory_benchmark_has_component_key(self):
        system = PerformanceBenchmarkSystem()
        result = await system._benchmark_memory_efficiency(iterations=1)
        assert result.get("component") == "memory"

    async def test_memory_benchmark_has_performance_summary(self, monkeypatch):
        import types
        import youtube_extension.backend.services.performance_benchmark_system as _mod
        fake = types.SimpleNamespace(
            Process=lambda: types.SimpleNamespace(
                memory_info=lambda: types.SimpleNamespace(rss=256 * 1024 * 1024)
            )
        )
        monkeypatch.setattr(_mod, 'psutil', fake)
        system = PerformanceBenchmarkSystem()
        result = await system._benchmark_memory_efficiency(iterations=1)
        assert "performance_summary" in result

    async def test_memory_benchmark_target_usage_mb(self, monkeypatch):
        import types
        import youtube_extension.backend.services.performance_benchmark_system as _mod
        fake = types.SimpleNamespace(
            Process=lambda: types.SimpleNamespace(
                memory_info=lambda: types.SimpleNamespace(rss=256 * 1024 * 1024)
            )
        )
        monkeypatch.setattr(_mod, 'psutil', fake)
        system = PerformanceBenchmarkSystem()
        result = await system._benchmark_memory_efficiency(iterations=1)
        assert result.get("target_usage_mb") == 2048


class TestBenchmarkFrontendPerformance:
    async def test_frontend_benchmark_returns_dict(self):
        system = PerformanceBenchmarkSystem()
        result = await system._benchmark_frontend_performance(iterations=1)
        assert isinstance(result, dict)

    async def test_frontend_benchmark_has_error_key(self):
        # Frontend metrics not available without integration
        system = PerformanceBenchmarkSystem()
        result = await system._benchmark_frontend_performance(iterations=1)
        assert "error" in result

    async def test_frontend_benchmark_target_met_false(self):
        system = PerformanceBenchmarkSystem()
        result = await system._benchmark_frontend_performance(iterations=1)
        assert result.get("target_met") is False
