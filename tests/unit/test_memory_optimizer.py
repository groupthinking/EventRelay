"""Unit tests for MemorySnapshot, MemoryLeak, and MemoryProfiler."""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

# Remove any mock installed by test_index_analysis.py so we get real psutil
sys.modules.pop('psutil', None)
import psutil as _real_psutil
sys.modules['psutil'] = _real_psutil
# Force reimport of memory_optimizer so it gets real psutil
sys.modules.pop('youtube_extension.backend.services.memory_optimizer', None)

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from youtube_extension.backend.services.memory_optimizer import (
    MemoryLeak,
    MemoryProfiler,
    MemorySnapshot,
)


# ===========================================================================
# MemorySnapshot dataclass
# ===========================================================================


def _make_snapshot(**kwargs):
    defaults = dict(
        timestamp=datetime.now(timezone.utc),
        total_memory_mb=8192.0,
        available_memory_mb=4096.0,
        process_memory_mb=256.0,
        memory_percent=50.0,
        python_objects=50000,
        gc_generation_0=10,
        gc_generation_1=5,
        gc_generation_2=2,
    )
    defaults.update(kwargs)
    return MemorySnapshot(**defaults)


class TestMemorySnapshot:
    def test_fields_stored(self):
        s = _make_snapshot(process_memory_mb=512.0)
        assert s.process_memory_mb == 512.0

    def test_cache_memory_default_zero(self):
        assert _make_snapshot().cache_memory_mb == 0.0

    def test_leak_indicators_none_replaced_with_dict(self):
        s = _make_snapshot(leak_indicators=None)
        assert s.leak_indicators == {}

    def test_explicit_leak_indicators_preserved(self):
        s = _make_snapshot(leak_indicators={"dict": 5})
        assert s.leak_indicators["dict"] == 5

    def test_custom_cache_memory(self):
        s = _make_snapshot(cache_memory_mb=128.0)
        assert s.cache_memory_mb == 128.0


# ===========================================================================
# MemoryLeak dataclass
# ===========================================================================


class TestMemoryLeak:
    @pytest.fixture
    def leak(self):
        return MemoryLeak(
            object_type="dict",
            count=1000,
            growth_rate=50.0,
            first_detected=datetime.now(timezone.utc),
            last_seen=datetime.now(timezone.utc),
            severity="medium",
        )

    def test_object_type_stored(self, leak):
        assert leak.object_type == "dict"

    def test_count_stored(self, leak):
        assert leak.count == 1000

    def test_growth_rate_stored(self, leak):
        assert leak.growth_rate == 50.0

    def test_severity_stored(self, leak):
        assert leak.severity == "medium"

    def test_traceback_info_default_empty(self, leak):
        assert leak.traceback_info == ""

    def test_custom_traceback_info(self):
        leak = MemoryLeak(
            object_type="list",
            count=500,
            growth_rate=10.0,
            first_detected=datetime.now(timezone.utc),
            last_seen=datetime.now(timezone.utc),
            severity="low",
            traceback_info="File foo.py line 42",
        )
        assert "foo.py" in leak.traceback_info


# ===========================================================================
# MemoryProfiler initial state
# ===========================================================================


class TestMemoryProfilerInit:
    @pytest.fixture
    def profiler(self):
        return MemoryProfiler()

    def test_tracking_disabled_by_default(self, profiler):
        assert profiler.tracking_enabled is False

    def test_snapshots_starts_empty(self, profiler):
        assert len(profiler.snapshots) == 0

    def test_leak_detection_starts_empty(self, profiler):
        assert profiler.leak_detection == {}

    def test_cleanup_callbacks_starts_empty(self, profiler):
        assert profiler.cleanup_callbacks == []

    def test_memory_thresholds_has_warning(self, profiler):
        assert "warning_mb" in profiler.memory_thresholds

    def test_memory_thresholds_has_critical(self, profiler):
        assert "critical_mb" in profiler.memory_thresholds

    def test_memory_thresholds_has_cleanup(self, profiler):
        assert "cleanup_mb" in profiler.memory_thresholds

    def test_memory_thresholds_has_max_growth_rate(self, profiler):
        assert "max_growth_rate" in profiler.memory_thresholds

    def test_snapshots_maxsize(self, profiler):
        assert profiler.snapshots.maxlen == 1000

    def test_stop_tracking_is_noop_when_not_started(self, profiler):
        profiler.stop_tracking()  # should not raise
        assert profiler.tracking_enabled is False


# ===========================================================================
# MemoryProfiler.register_cleanup_callback / track_object / untrack_object
# ===========================================================================


class _Trackable:
    """Simple class that supports weak references (needed for WeakSet)."""
    pass


class TestMemoryProfilerCallbacks:
    @pytest.fixture
    def profiler(self):
        from youtube_extension.backend.services.memory_optimizer import MemoryProfiler
        return MemoryProfiler()

    def test_register_callback_appended(self, profiler):
        cb = lambda: None
        profiler.register_cleanup_callback(cb)
        assert cb in profiler.cleanup_callbacks

    def test_register_multiple_callbacks(self, profiler):
        cb1 = lambda: None
        cb2 = lambda: None
        profiler.register_cleanup_callback(cb1)
        profiler.register_cleanup_callback(cb2)
        assert len(profiler.cleanup_callbacks) == 2

    def test_track_object_increments_counter(self, profiler):
        obj = _Trackable()
        profiler.track_object(obj)
        assert profiler.object_counters["_Trackable"] == 1

    def test_track_multiple_objects_same_type(self, profiler):
        obj1 = _Trackable()
        obj2 = _Trackable()
        profiler.track_object(obj1)
        profiler.track_object(obj2)
        assert profiler.object_counters["_Trackable"] == 2

    def test_untrack_object_decrements_counter(self, profiler):
        obj = _Trackable()
        profiler.track_object(obj)
        profiler.untrack_object(obj)
        assert profiler.object_counters["_Trackable"] == 0

    def test_untrack_nontracked_object_does_not_raise(self, profiler):
        # Should not raise even if the object was never tracked
        profiler.untrack_object(_Trackable())


# ===========================================================================
# MemoryProfiler._calculate_growth_rate
# ===========================================================================


class TestCalculateGrowthRate:
    @pytest.fixture
    def profiler(self):
        from youtube_extension.backend.services.memory_optimizer import MemoryProfiler
        return MemoryProfiler()

    def test_empty_list_returns_zero(self, profiler):
        assert profiler._calculate_growth_rate([]) == 0.0

    def test_single_element_returns_zero(self, profiler):
        assert profiler._calculate_growth_rate([100]) == 0.0

    def test_positive_growth(self, profiler):
        rate = profiler._calculate_growth_rate([100, 200, 300])
        assert rate > 0

    def test_negative_growth(self, profiler):
        rate = profiler._calculate_growth_rate([300, 200, 100])
        assert rate < 0

    def test_flat_series_returns_zero(self, profiler):
        rate = profiler._calculate_growth_rate([100, 100, 100])
        assert rate == 0.0


# ===========================================================================
# MemoryProfiler._assess_leak_severity
# ===========================================================================


class TestAssessLeakSeverity:
    @pytest.fixture
    def profiler(self):
        from youtube_extension.backend.services.memory_optimizer import MemoryProfiler
        return MemoryProfiler()

    def test_critical_above_1000(self, profiler):
        assert profiler._assess_leak_severity(1500.0) == "critical"

    def test_high_above_500(self, profiler):
        assert profiler._assess_leak_severity(700.0) == "high"

    def test_medium_above_200(self, profiler):
        assert profiler._assess_leak_severity(300.0) == "medium"

    def test_low_below_200(self, profiler):
        assert profiler._assess_leak_severity(50.0) == "low"

    def test_boundary_exactly_1000_is_high(self, profiler):
        # growth_rate > 1000 is critical; == 1000 is not > 1000
        assert profiler._assess_leak_severity(1000.0) == "high"

    def test_boundary_exactly_500_is_medium(self, profiler):
        assert profiler._assess_leak_severity(500.0) == "medium"


# ===========================================================================
# MemoryProfiler.get_memory_report
# ===========================================================================


class TestGetMemoryReport:
    @pytest.fixture
    def profiler(self):
        from youtube_extension.backend.services.memory_optimizer import MemoryProfiler
        return MemoryProfiler()

    def test_report_has_timestamp(self, profiler):
        report = profiler.get_memory_report()
        assert "timestamp" in report

    def test_report_has_tracking_enabled(self, profiler):
        report = profiler.get_memory_report()
        assert "tracking_enabled" in report

    def test_report_tracking_enabled_false_initially(self, profiler):
        report = profiler.get_memory_report()
        assert report["tracking_enabled"] is False

    def test_report_has_snapshots_collected(self, profiler):
        report = profiler.get_memory_report()
        assert "snapshots_collected" in report

    def test_report_snapshots_zero_initially(self, profiler):
        report = profiler.get_memory_report()
        assert report["snapshots_collected"] == 0

    def test_report_has_active_leaks(self, profiler):
        report = profiler.get_memory_report()
        assert "active_leaks" in report

    def test_report_has_thresholds(self, profiler):
        report = profiler.get_memory_report()
        assert "thresholds" in report

    def test_report_has_memory_history(self, profiler):
        report = profiler.get_memory_report()
        assert "memory_history" in report

    def test_report_memory_history_empty_initially(self, profiler):
        report = profiler.get_memory_report()
        assert report["memory_history"] == []


# ===========================================================================
# MemoryOptimizer initialisation
# ===========================================================================


class TestMemoryOptimizerInit:
    def test_profiler_stored(self):
        from youtube_extension.backend.services.memory_optimizer import (
            MemoryOptimizer,
            MemoryProfiler,
        )
        p = MemoryProfiler()
        opt = MemoryOptimizer(p)
        assert opt.profiler is p

    def test_strategies_list_non_empty(self):
        from youtube_extension.backend.services.memory_optimizer import (
            MemoryOptimizer,
            MemoryProfiler,
        )
        opt = MemoryOptimizer(MemoryProfiler())
        assert len(opt.optimization_strategies) > 0

    def test_all_strategies_are_callable(self):
        from youtube_extension.backend.services.memory_optimizer import (
            MemoryOptimizer,
            MemoryProfiler,
        )
        opt = MemoryOptimizer(MemoryProfiler())
        for s in opt.optimization_strategies:
            assert callable(s)


# ===========================================================================
# MemoryOptimizer.optimize_memory_usage (async)
# ===========================================================================


class TestOptimizeMemoryUsage:
    async def test_optimize_returns_summary_dict(self):
        from youtube_extension.backend.services.memory_optimizer import (
            MemoryOptimizer,
            MemoryProfiler,
        )
        opt = MemoryOptimizer(MemoryProfiler())
        result = await opt.optimize_memory_usage()
        assert isinstance(result, dict)

    async def test_summary_has_required_keys(self):
        from youtube_extension.backend.services.memory_optimizer import (
            MemoryOptimizer,
            MemoryProfiler,
        )
        opt = MemoryOptimizer(MemoryProfiler())
        result = await opt.optimize_memory_usage()
        for key in ("initial_memory_mb", "final_memory_mb", "memory_saved_mb",
                    "objects_reduced", "optimization_results", "timestamp"):
            assert key in result

    async def test_summary_has_success_key(self):
        from youtube_extension.backend.services.memory_optimizer import (
            MemoryOptimizer,
            MemoryProfiler,
        )
        opt = MemoryOptimizer(MemoryProfiler())
        result = await opt.optimize_memory_usage()
        assert "success" in result

    async def test_optimization_results_has_strategy_entries(self):
        from youtube_extension.backend.services.memory_optimizer import (
            MemoryOptimizer,
            MemoryProfiler,
        )
        opt = MemoryOptimizer(MemoryProfiler())
        result = await opt.optimize_memory_usage()
        assert len(result["optimization_results"]) == len(opt.optimization_strategies)

    async def test_gc_optimize_returns_dict(self):
        from youtube_extension.backend.services.memory_optimizer import (
            MemoryOptimizer,
            MemoryProfiler,
        )
        opt = MemoryOptimizer(MemoryProfiler())
        result = await opt._optimize_garbage_collection()
        assert isinstance(result, dict)
        assert "objects_collected" in result

    async def test_object_pools_optimize_returns_dict(self):
        from youtube_extension.backend.services.memory_optimizer import (
            MemoryOptimizer,
            MemoryProfiler,
        )
        opt = MemoryOptimizer(MemoryProfiler())
        result = await opt._optimize_object_pools()
        assert isinstance(result, dict)
        assert "references_cleaned" in result

    async def test_data_structures_optimize_returns_dict(self):
        from youtube_extension.backend.services.memory_optimizer import (
            MemoryOptimizer,
            MemoryProfiler,
        )
        opt = MemoryOptimizer(MemoryProfiler())
        result = await opt._optimize_data_structures()
        assert isinstance(result, dict)

    async def test_caches_optimize_returns_dict(self):
        from youtube_extension.backend.services.memory_optimizer import (
            MemoryOptimizer,
            MemoryProfiler,
        )
        opt = MemoryOptimizer(MemoryProfiler())
        result = await opt._optimize_caches()
        assert isinstance(result, dict)
        assert "cache_memory_freed_mb" in result


# ===========================================================================
# MemoryProfiler.take_snapshot (async)
# ===========================================================================


class TestTakeSnapshot:
    async def test_snapshot_returns_memory_snapshot(self):
        from youtube_extension.backend.services.memory_optimizer import (
            MemoryProfiler,
            MemorySnapshot,
        )
        p = MemoryProfiler()
        snap = await p.take_snapshot()
        assert isinstance(snap, MemorySnapshot)

    async def test_snapshot_stored_in_deque(self):
        from youtube_extension.backend.services.memory_optimizer import MemoryProfiler
        p = MemoryProfiler()
        await p.take_snapshot()
        assert len(p.snapshots) == 1

    async def test_snapshot_process_memory_positive(self):
        from youtube_extension.backend.services.memory_optimizer import MemoryProfiler
        p = MemoryProfiler()
        snap = await p.take_snapshot()
        assert snap.process_memory_mb > 0

    async def test_snapshot_python_objects_positive(self):
        from youtube_extension.backend.services.memory_optimizer import MemoryProfiler
        p = MemoryProfiler()
        snap = await p.take_snapshot()
        assert snap.python_objects > 0
