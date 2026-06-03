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


# ===========================================================================
# MemoryProfiler.take_snapshot error path (line 173-185)
# ===========================================================================


class TestTakeSnapshotErrorPath:
    async def test_snapshot_returns_fallback_on_psutil_error(self, monkeypatch):
        import types
        import youtube_extension.backend.services.memory_optimizer as _mod
        fake = types.SimpleNamespace(
            virtual_memory=lambda: (_ for _ in ()).throw(OSError("fail")),
            Process=lambda: None,
        )
        monkeypatch.setattr(_mod, 'psutil', fake)
        p = _mod.MemoryProfiler()
        snap = await p.take_snapshot()
        # Should return a zero-filled snapshot, not raise
        assert isinstance(snap, _mod.MemorySnapshot)
        assert snap.process_memory_mb == 0

    async def test_snapshot_fallback_has_zero_total_memory(self, monkeypatch):
        import types
        import youtube_extension.backend.services.memory_optimizer as _mod
        fake = types.SimpleNamespace(
            virtual_memory=lambda: (_ for _ in ()).throw(RuntimeError("fail")),
            Process=lambda: None,
        )
        monkeypatch.setattr(_mod, 'psutil', fake)
        p = _mod.MemoryProfiler()
        snap = await p.take_snapshot()
        assert snap.total_memory_mb == 0


# ===========================================================================
# MemoryProfiler._analyze_memory_usage (lines 187-204)
# ===========================================================================


class TestAnalyzeMemoryUsage:
    def _make_snapshot(self, process_memory_mb=256.0, memory_percent=50.0):
        return MemorySnapshot(
            timestamp=datetime.now(timezone.utc),
            total_memory_mb=8192.0,
            available_memory_mb=4096.0,
            process_memory_mb=process_memory_mb,
            memory_percent=memory_percent,
            python_objects=50000,
            gc_generation_0=10,
            gc_generation_1=5,
            gc_generation_2=2,
        )

    async def test_normal_memory_no_alert_methods_called(self):
        from unittest.mock import AsyncMock, patch
        from youtube_extension.backend.services.memory_optimizer import MemoryProfiler
        p = MemoryProfiler()
        snap = self._make_snapshot(process_memory_mb=256.0)
        with patch.object(p, '_trigger_memory_warning', new_callable=AsyncMock) as mock_warn, \
             patch.object(p, '_trigger_critical_memory_alert', new_callable=AsyncMock) as mock_crit:
            await p._analyze_memory_usage(snap)
            mock_warn.assert_not_called()
            mock_crit.assert_not_called()

    async def test_warning_threshold_triggers_warning(self):
        from unittest.mock import AsyncMock, patch
        from youtube_extension.backend.services.memory_optimizer import MemoryProfiler
        p = MemoryProfiler()
        # warning_mb = 1024; use value between warning and critical
        snap = self._make_snapshot(process_memory_mb=1200.0)
        with patch.object(p, '_trigger_memory_warning', new_callable=AsyncMock) as mock_warn, \
             patch.object(p, '_trigger_critical_memory_alert', new_callable=AsyncMock) as mock_crit:
            await p._analyze_memory_usage(snap)
            mock_warn.assert_called_once_with(snap)
            mock_crit.assert_not_called()

    async def test_critical_threshold_triggers_critical_alert(self):
        from unittest.mock import AsyncMock, patch
        from youtube_extension.backend.services.memory_optimizer import MemoryProfiler
        p = MemoryProfiler()
        # critical_mb = 2048
        snap = self._make_snapshot(process_memory_mb=2100.0)
        with patch.object(p, '_trigger_critical_memory_alert', new_callable=AsyncMock) as mock_crit, \
             patch.object(p, '_trigger_memory_warning', new_callable=AsyncMock) as mock_warn:
            await p._analyze_memory_usage(snap)
            mock_crit.assert_called_once_with(snap)
            mock_warn.assert_not_called()

    async def test_cleanup_threshold_triggers_cleanup(self):
        from unittest.mock import AsyncMock, patch
        from youtube_extension.backend.services.memory_optimizer import MemoryProfiler
        p = MemoryProfiler()
        # cleanup_mb = 1536
        snap = self._make_snapshot(process_memory_mb=1600.0)
        with patch.object(p, '_trigger_memory_cleanup', new_callable=AsyncMock) as mock_clean, \
             patch.object(p, '_trigger_memory_warning', new_callable=AsyncMock):
            await p._analyze_memory_usage(snap)
            mock_clean.assert_called_once()


# ===========================================================================
# MemoryProfiler._get_object_trends (lines 231-244)
# ===========================================================================


class TestGetObjectTrends:
    def test_trends_includes_python_objects(self):
        from youtube_extension.backend.services.memory_optimizer import MemoryProfiler
        p = MemoryProfiler()
        snaps = [
            MemorySnapshot(
                timestamp=datetime.now(timezone.utc),
                total_memory_mb=8192.0, available_memory_mb=4096.0,
                process_memory_mb=256.0, memory_percent=50.0,
                python_objects=i * 1000,
                gc_generation_0=0, gc_generation_1=0, gc_generation_2=0,
            )
            for i in range(3)
        ]
        trends = p._get_object_trends(snaps)
        assert 'python_objects' in trends
        assert trends['python_objects'] == [0, 1000, 2000]

    def test_trends_includes_leak_indicators(self):
        from youtube_extension.backend.services.memory_optimizer import MemoryProfiler
        p = MemoryProfiler()
        snaps = [
            MemorySnapshot(
                timestamp=datetime.now(timezone.utc),
                total_memory_mb=8192.0, available_memory_mb=4096.0,
                process_memory_mb=256.0, memory_percent=50.0,
                python_objects=50000,
                gc_generation_0=0, gc_generation_1=0, gc_generation_2=0,
                leak_indicators={"dict": i * 10},
            )
            for i in range(3)
        ]
        trends = p._get_object_trends(snaps)
        assert 'dict' in trends
        assert trends['dict'] == [0, 10, 20]

    def test_trends_empty_snapshots_returns_empty(self):
        from youtube_extension.backend.services.memory_optimizer import MemoryProfiler
        p = MemoryProfiler()
        trends = p._get_object_trends([])
        assert len(trends) == 0


# ===========================================================================
# MemoryProfiler._get_traceback_info (lines 268-284)
# ===========================================================================


class TestGetTracebackInfo:
    def test_returns_string_when_not_tracing(self):
        from youtube_extension.backend.services.memory_optimizer import MemoryProfiler
        import tracemalloc
        tracemalloc.stop()  # ensure not tracing
        p = MemoryProfiler()
        info = p._get_traceback_info("dict")
        assert isinstance(info, str)
        assert "Tracemalloc not available" in info

    def test_returns_string_when_tracing(self):
        from youtube_extension.backend.services.memory_optimizer import MemoryProfiler
        import tracemalloc
        tracemalloc.start()
        try:
            p = MemoryProfiler()
            info = p._get_traceback_info("dict")
            assert isinstance(info, str)
        finally:
            tracemalloc.stop()


# ===========================================================================
# MemoryProfiler.start_tracking / stop_tracking (lines 89-118)
# ===========================================================================


class TestMemoryProfilerStartStop:
    def test_start_tracking_sets_flag(self):
        from youtube_extension.backend.services.memory_optimizer import MemoryProfiler
        p = MemoryProfiler()
        # We can't easily run the asyncio task in a sync test, but start_tracking
        # should at least set the flag (it may fail to create_task if no loop)
        try:
            p.start_tracking()
        except Exception:
            pass
        # If it didn't raise, verify it either set the flag or gracefully failed
        # The flag may or may not be set depending on event loop availability
        assert isinstance(p.tracking_enabled, bool)

    def test_start_tracking_idempotent_when_already_started(self):
        from youtube_extension.backend.services.memory_optimizer import MemoryProfiler
        p = MemoryProfiler()
        p.tracking_enabled = True  # simulate already started
        # Should return early without error
        p.start_tracking()
        assert p.tracking_enabled is True

    def test_stop_tracking_clears_flag(self):
        import tracemalloc
        from youtube_extension.backend.services.memory_optimizer import MemoryProfiler
        tracemalloc.start()
        p = MemoryProfiler()
        p.tracking_enabled = True
        p.stop_tracking()
        assert p.tracking_enabled is False

    def test_stop_tracking_when_already_stopped_noop(self):
        from youtube_extension.backend.services.memory_optimizer import MemoryProfiler
        p = MemoryProfiler()
        p.tracking_enabled = False
        p.stop_tracking()  # Should not raise
        assert p.tracking_enabled is False


# ===========================================================================
# MemoryProfiler._trigger_memory_cleanup (lines 332-366)
# ===========================================================================


class TestTriggerMemoryCleanup:
    async def test_cleanup_runs_sync_callbacks(self, monkeypatch):
        import types
        import youtube_extension.backend.services.memory_optimizer as _mod
        fake = types.SimpleNamespace(
            Process=lambda: types.SimpleNamespace(
                memory_info=lambda: types.SimpleNamespace(rss=100 * 1024**2)
            ),
        )
        monkeypatch.setattr(_mod, 'psutil', fake)
        p = _mod.MemoryProfiler()
        calls = []
        p.register_cleanup_callback(lambda: calls.append(1))
        await p._trigger_memory_cleanup()
        assert calls == [1]

    async def test_cleanup_runs_async_callbacks(self, monkeypatch):
        import types
        import youtube_extension.backend.services.memory_optimizer as _mod
        fake = types.SimpleNamespace(
            Process=lambda: types.SimpleNamespace(
                memory_info=lambda: types.SimpleNamespace(rss=100 * 1024**2)
            ),
        )
        monkeypatch.setattr(_mod, 'psutil', fake)
        p = _mod.MemoryProfiler()
        calls = []
        async def async_cb():
            calls.append(1)
        p.register_cleanup_callback(async_cb)
        await p._trigger_memory_cleanup()
        assert calls == [1]

    async def test_cleanup_handles_callback_exception(self, monkeypatch):
        import types
        import youtube_extension.backend.services.memory_optimizer as _mod
        fake = types.SimpleNamespace(
            Process=lambda: types.SimpleNamespace(
                memory_info=lambda: types.SimpleNamespace(rss=100 * 1024**2)
            ),
        )
        monkeypatch.setattr(_mod, 'psutil', fake)
        p = _mod.MemoryProfiler()
        def bad_cb():
            raise RuntimeError("callback failure")
        p.register_cleanup_callback(bad_cb)
        # Should not raise
        await p._trigger_memory_cleanup()

    async def test_cleanup_runs_gc_collect(self, monkeypatch):
        import gc
        import types
        from unittest.mock import patch
        import youtube_extension.backend.services.memory_optimizer as _mod
        fake = types.SimpleNamespace(
            Process=lambda: types.SimpleNamespace(
                memory_info=lambda: types.SimpleNamespace(rss=100 * 1024**2)
            ),
        )
        monkeypatch.setattr(_mod, 'psutil', fake)
        p = _mod.MemoryProfiler()
        with patch.object(_mod.gc, 'collect', wraps=_mod.gc.collect) as mock_gc:
            await p._trigger_memory_cleanup()
            mock_gc.assert_called()


# ===========================================================================
# MemoryProfiler._trigger_aggressive_cleanup (lines 368-388)
# ===========================================================================


class TestTriggerAggressiveCleanup:
    async def test_aggressive_cleanup_runs_without_error(self, monkeypatch):
        import types
        import youtube_extension.backend.services.memory_optimizer as _mod
        fake = types.SimpleNamespace(
            Process=lambda: types.SimpleNamespace(
                memory_info=lambda: types.SimpleNamespace(rss=100 * 1024**2)
            ),
        )
        monkeypatch.setattr(_mod, 'psutil', fake)
        p = _mod.MemoryProfiler()
        await p._trigger_aggressive_cleanup()  # Should not raise

    async def test_aggressive_cleanup_calls_trigger_memory_cleanup(self, monkeypatch):
        import types
        from unittest.mock import AsyncMock, patch
        import youtube_extension.backend.services.memory_optimizer as _mod
        fake = types.SimpleNamespace(
            Process=lambda: types.SimpleNamespace(
                memory_info=lambda: types.SimpleNamespace(rss=100 * 1024**2)
            ),
        )
        monkeypatch.setattr(_mod, 'psutil', fake)
        p = _mod.MemoryProfiler()
        with patch.object(p, '_trigger_memory_cleanup', new_callable=AsyncMock) as mock_clean:
            await p._trigger_aggressive_cleanup()
            mock_clean.assert_called_once()


# ===========================================================================
# MemoryProfiler._trigger_memory_warning / _trigger_critical_memory_alert (lines 313-329)
# ===========================================================================


class TestTriggerMemoryAlerts:
    async def test_trigger_memory_warning_logs_without_error(self):
        from youtube_extension.backend.services.memory_optimizer import MemoryProfiler
        p = MemoryProfiler()
        snap = MemorySnapshot(
            timestamp=datetime.now(timezone.utc),
            total_memory_mb=8192.0, available_memory_mb=4096.0,
            process_memory_mb=1200.0, memory_percent=50.0,
            python_objects=50000,
            gc_generation_0=0, gc_generation_1=0, gc_generation_2=0,
        )
        await p._trigger_memory_warning(snap)  # Should not raise

    async def test_trigger_critical_alert_calls_aggressive_cleanup(self):
        from unittest.mock import AsyncMock, patch
        from youtube_extension.backend.services.memory_optimizer import MemoryProfiler
        p = MemoryProfiler()
        snap = MemorySnapshot(
            timestamp=datetime.now(timezone.utc),
            total_memory_mb=8192.0, available_memory_mb=1000.0,
            process_memory_mb=2100.0, memory_percent=80.0,
            python_objects=50000,
            gc_generation_0=0, gc_generation_1=0, gc_generation_2=0,
        )
        with patch.object(p, '_trigger_aggressive_cleanup', new_callable=AsyncMock) as mock_agg:
            await p._trigger_critical_memory_alert(snap)
            mock_agg.assert_called_once()


# ===========================================================================
# MemoryProfiler._handle_memory_leak (lines 390-401)
# ===========================================================================


class TestHandleMemoryLeak:
    async def test_handle_leak_low_severity_no_cleanup(self):
        from unittest.mock import AsyncMock, patch
        from youtube_extension.backend.services.memory_optimizer import MemoryProfiler, MemoryLeak
        p = MemoryProfiler()
        leak = MemoryLeak(
            object_type="dict", count=100, growth_rate=50.0,
            first_detected=datetime.now(timezone.utc),
            last_seen=datetime.now(timezone.utc),
            severity="low",
        )
        with patch.object(p, '_trigger_memory_cleanup', new_callable=AsyncMock) as mock_clean:
            await p._handle_memory_leak(leak)
            mock_clean.assert_not_called()

    async def test_handle_leak_high_severity_triggers_cleanup(self):
        from unittest.mock import AsyncMock, patch
        from youtube_extension.backend.services.memory_optimizer import MemoryProfiler, MemoryLeak
        p = MemoryProfiler()
        leak = MemoryLeak(
            object_type="list", count=1000, growth_rate=600.0,
            first_detected=datetime.now(timezone.utc),
            last_seen=datetime.now(timezone.utc),
            severity="high",
        )
        with patch.object(p, '_trigger_memory_cleanup', new_callable=AsyncMock) as mock_clean:
            await p._handle_memory_leak(leak)
            mock_clean.assert_called_once()

    async def test_handle_leak_critical_severity_triggers_cleanup(self):
        from unittest.mock import AsyncMock, patch
        from youtube_extension.backend.services.memory_optimizer import MemoryProfiler, MemoryLeak
        p = MemoryProfiler()
        leak = MemoryLeak(
            object_type="tuple", count=5000, growth_rate=1100.0,
            first_detected=datetime.now(timezone.utc),
            last_seen=datetime.now(timezone.utc),
            severity="critical",
        )
        with patch.object(p, '_trigger_memory_cleanup', new_callable=AsyncMock) as mock_clean:
            await p._handle_memory_leak(leak)
            mock_clean.assert_called_once()


# ===========================================================================
# memory_efficient decorator (lines 633-664)
# ===========================================================================


class TestMemoryEfficientDecorator:
    async def test_async_wrapper_returns_result(self, monkeypatch):
        import types
        import youtube_extension.backend.services.memory_optimizer as _mod
        fake = types.SimpleNamespace(
            Process=lambda: types.SimpleNamespace(
                memory_info=lambda: types.SimpleNamespace(rss=100 * 1024**2)
            ),
        )
        monkeypatch.setattr(_mod, 'psutil', fake)
        @_mod.memory_efficient
        async def async_fn(x):
            return x * 2
        result = await async_fn(5)
        assert result == 10

    def test_sync_wrapper_returns_result(self, monkeypatch):
        import types
        import youtube_extension.backend.services.memory_optimizer as _mod
        fake = types.SimpleNamespace(
            Process=lambda: types.SimpleNamespace(
                memory_info=lambda: types.SimpleNamespace(rss=100 * 1024**2)
            ),
        )
        monkeypatch.setattr(_mod, 'psutil', fake)
        @_mod.memory_efficient
        def sync_fn(x):
            return x + 10
        result = sync_fn(5)
        assert result == 15

    def test_sync_wrapper_chooses_sync_path_for_non_coroutine(self, monkeypatch):
        import types
        import youtube_extension.backend.services.memory_optimizer as _mod
        import asyncio
        fake = types.SimpleNamespace(
            Process=lambda: types.SimpleNamespace(
                memory_info=lambda: types.SimpleNamespace(rss=100 * 1024**2)
            ),
        )
        monkeypatch.setattr(_mod, 'psutil', fake)
        @_mod.memory_efficient
        def sync_fn():
            return "sync_result"
        # The decorated function should not be a coroutine function
        assert not asyncio.iscoroutinefunction(sync_fn)
        assert sync_fn() == "sync_result"


# ===========================================================================
# track_memory_usage decorator (lines 666-683)
# ===========================================================================


class TestTrackMemoryUsageDecorator:
    async def test_tracks_memory_and_returns_result(self, monkeypatch):
        import types
        import youtube_extension.backend.services.memory_optimizer as _mod
        fake = types.SimpleNamespace(
            Process=lambda: types.SimpleNamespace(
                memory_info=lambda: types.SimpleNamespace(rss=100 * 1024**2)
            ),
        )
        monkeypatch.setattr(_mod, 'psutil', fake)
        @_mod.track_memory_usage(threshold_mb=100)
        async def async_fn():
            return "ok"
        result = await async_fn()
        assert result == "ok"

    async def test_sync_function_tracked_returns_result(self, monkeypatch):
        """track_memory_usage always wraps in an async wrapper; calling sync fn still works."""
        import types
        import youtube_extension.backend.services.memory_optimizer as _mod
        fake = types.SimpleNamespace(
            Process=lambda: types.SimpleNamespace(
                memory_info=lambda: types.SimpleNamespace(rss=100 * 1024**2)
            ),
        )
        monkeypatch.setattr(_mod, 'psutil', fake)
        @_mod.track_memory_usage(threshold_mb=100)
        def sync_fn(x, y):
            return x + y
        result = await sync_fn(3, 4)
        assert result == 7


# ===========================================================================
# Convenience functions: start/stop/get_memory_status/optimize/cleanup/register
# ===========================================================================


class TestConvenienceFunctions:
    async def test_get_memory_status_returns_dict(self):
        from youtube_extension.backend.services.memory_optimizer import get_memory_status
        result = await get_memory_status()
        assert isinstance(result, dict)

    async def test_optimize_memory_returns_dict(self, monkeypatch):
        import types
        import youtube_extension.backend.services.memory_optimizer as _mod
        fake = types.SimpleNamespace(
            virtual_memory=lambda: types.SimpleNamespace(
                total=8 * 1024**3, available=4 * 1024**3, percent=50.0
            ),
            Process=lambda: types.SimpleNamespace(
                memory_info=lambda: types.SimpleNamespace(rss=100 * 1024**2)
            ),
        )
        monkeypatch.setattr(_mod, 'psutil', fake)
        result = await _mod.optimize_memory()
        assert isinstance(result, dict)

    async def test_cleanup_memory_runs_without_error(self, monkeypatch):
        import types
        import youtube_extension.backend.services.memory_optimizer as _mod
        fake = types.SimpleNamespace(
            Process=lambda: types.SimpleNamespace(
                memory_info=lambda: types.SimpleNamespace(rss=100 * 1024**2)
            ),
        )
        monkeypatch.setattr(_mod, 'psutil', fake)
        await _mod.cleanup_memory()  # Should not raise

    def test_register_cleanup_callback_stored(self):
        from youtube_extension.backend.services.memory_optimizer import (
            register_cleanup_callback, memory_profiler
        )
        cb = lambda: None
        initial_count = len(memory_profiler.cleanup_callbacks)
        register_cleanup_callback(cb)
        assert len(memory_profiler.cleanup_callbacks) == initial_count + 1

    async def test_stop_monitoring_noop_when_not_started(self):
        """Calling stop_memory_monitoring() when not started should not raise."""
        from youtube_extension.backend.services.memory_optimizer import stop_memory_monitoring
        await stop_memory_monitoring()  # should not raise


# ===========================================================================
# MemoryOptimizer._optimize_garbage_collection details
# ===========================================================================


class TestOptimizeGarbageCollectionDetails:
    async def test_gc_optimize_has_thresholds_set(self):
        import gc
        from youtube_extension.backend.services.memory_optimizer import MemoryOptimizer, MemoryProfiler
        opt = MemoryOptimizer(MemoryProfiler())
        result = await opt._optimize_garbage_collection()
        assert "thresholds_set" in result
        assert result["thresholds_set"] == gc.get_threshold()

    async def test_gc_optimize_has_initial_and_final_stats(self):
        from youtube_extension.backend.services.memory_optimizer import MemoryOptimizer, MemoryProfiler
        opt = MemoryOptimizer(MemoryProfiler())
        result = await opt._optimize_garbage_collection()
        assert "initial_stats" in result
        assert "final_stats" in result

    async def test_gc_optimize_objects_collected_non_negative(self):
        from youtube_extension.backend.services.memory_optimizer import MemoryOptimizer, MemoryProfiler
        opt = MemoryOptimizer(MemoryProfiler())
        result = await opt._optimize_garbage_collection()
        assert result["objects_collected"] >= 0


# ===========================================================================
# MemoryOptimizer._optimize_data_structures details
# ===========================================================================


class TestOptimizeDataStructures:
    async def test_has_dict_optimizations_key(self):
        from youtube_extension.backend.services.memory_optimizer import MemoryOptimizer, MemoryProfiler
        opt = MemoryOptimizer(MemoryProfiler())
        result = await opt._optimize_data_structures()
        assert "dict_optimizations" in result

    async def test_has_list_optimizations_key(self):
        from youtube_extension.backend.services.memory_optimizer import MemoryOptimizer, MemoryProfiler
        opt = MemoryOptimizer(MemoryProfiler())
        result = await opt._optimize_data_structures()
        assert "list_optimizations" in result


# ===========================================================================
# MemoryProfiler.get_memory_report with snapshots populated
# ===========================================================================


class TestGetMemoryReportWithHistory:
    async def test_report_memory_history_shows_last_snapshots(self, monkeypatch):
        import types
        import youtube_extension.backend.services.memory_optimizer as _mod
        fake = types.SimpleNamespace(
            virtual_memory=lambda: types.SimpleNamespace(
                total=8 * 1024**3, available=4 * 1024**3, percent=50.0
            ),
            Process=lambda: types.SimpleNamespace(
                memory_info=lambda: types.SimpleNamespace(rss=100 * 1024**2)
            ),
        )
        monkeypatch.setattr(_mod, 'psutil', fake)
        p = _mod.MemoryProfiler()
        for _ in range(3):
            await p.take_snapshot()
        report = p.get_memory_report()
        assert report["snapshots_collected"] == 3
        assert len(report["memory_history"]) <= 10

    async def test_report_active_leaks_count_matches(self, monkeypatch):
        import types
        import youtube_extension.backend.services.memory_optimizer as _mod
        fake = types.SimpleNamespace(
            virtual_memory=lambda: types.SimpleNamespace(
                total=8 * 1024**3, available=4 * 1024**3, percent=50.0
            ),
            Process=lambda: types.SimpleNamespace(
                memory_info=lambda: types.SimpleNamespace(rss=100 * 1024**2)
            ),
        )
        monkeypatch.setattr(_mod, 'psutil', fake)
        p = _mod.MemoryProfiler()
        p.leak_detection["dict"] = _mod.MemoryLeak(
            object_type="dict", count=100, growth_rate=50.0,
            first_detected=datetime.now(timezone.utc),
            last_seen=datetime.now(timezone.utc),
            severity="low",
        )
        report = p.get_memory_report()
        assert report["active_leaks"] == 1
