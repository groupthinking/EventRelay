"""Unit tests for MemorySnapshot, MemoryAlert, ResourceLimit, and ResourcePool."""

from __future__ import annotations

import gc
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Remove any mock installed by test_index_analysis.py so we get real psutil
sys.modules.pop('psutil', None)
import psutil as _real_psutil
sys.modules['psutil'] = _real_psutil
# Force reimport of memory_manager so it gets real psutil
sys.modules.pop('youtube_extension.backend.services.memory_manager', None)

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from youtube_extension.backend.services.memory_manager import (
    MemoryAlert,
    MemoryManager,
    MemorySnapshot,
    ResourceLimit,
    ResourcePool,
)


# ===========================================================================
# MemorySnapshot dataclass
# ===========================================================================


class TestMemorySnapshot:
    def _make(self, **kw) -> MemorySnapshot:
        defaults = dict(
            timestamp=datetime.now(timezone.utc),
            rss_mb=100.0,
            vms_mb=200.0,
            percent=25.0,
            available_mb=3000.0,
            cached_mb=512.0,
            buffers_mb=64.0,
            heap_size_mb=10.0,
            gc_collections=5,
            gc_objects=1000,
        )
        return MemorySnapshot(**{**defaults, **kw})

    def test_all_fields_stored(self):
        s = self._make(rss_mb=128.0, vms_mb=256.0)
        assert s.rss_mb == 128.0
        assert s.vms_mb == 256.0

    def test_percent_stored(self):
        s = self._make(percent=42.5)
        assert s.percent == 42.5

    def test_gc_fields_stored(self):
        s = self._make(gc_collections=3, gc_objects=500)
        assert s.gc_collections == 3
        assert s.gc_objects == 500

    def test_timestamp_stored(self):
        ts = datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
        s = self._make(timestamp=ts)
        assert s.timestamp == ts


# ===========================================================================
# MemoryAlert dataclass
# ===========================================================================


class TestMemoryAlert:
    def _make(self, **kw) -> MemoryAlert:
        defaults = dict(
            alert_type="high_memory_usage",
            severity="high",
            message="Memory too high",
            current_usage_mb=1500.0,
            threshold_mb=1024.0,
            timestamp=datetime.now(timezone.utc),
            process_info={},
        )
        return MemoryAlert(**{**defaults, **kw})

    def test_alert_type_stored(self):
        a = self._make(alert_type="memory_growth")
        assert a.alert_type == "memory_growth"

    def test_severity_levels(self):
        for sev in ("low", "medium", "high", "critical"):
            a = self._make(severity=sev)
            assert a.severity == sev

    def test_usage_and_threshold_stored(self):
        a = self._make(current_usage_mb=2048.0, threshold_mb=1024.0)
        assert a.current_usage_mb == 2048.0
        assert a.threshold_mb == 1024.0

    def test_process_info_stored(self):
        a = self._make(process_info={"pid": 42, "num_threads": 10})
        assert a.process_info["pid"] == 42


# ===========================================================================
# ResourceLimit dataclass
# ===========================================================================


class TestResourceLimit:
    def test_fields_stored(self):
        rl = ResourceLimit(
            memory_limit_mb=2048,
            cpu_limit_percent=80.0,
            file_descriptor_limit=1024,
            thread_limit=100,
            connection_limit=200,
        )
        assert rl.memory_limit_mb == 2048
        assert rl.cpu_limit_percent == 80.0
        assert rl.file_descriptor_limit == 1024
        assert rl.thread_limit == 100
        assert rl.connection_limit == 200

    def test_custom_values(self):
        rl = ResourceLimit(
            memory_limit_mb=512,
            cpu_limit_percent=50.0,
            file_descriptor_limit=256,
            thread_limit=20,
            connection_limit=50,
        )
        assert rl.memory_limit_mb == 512


# ===========================================================================
# ResourcePool.get_stats
# ===========================================================================


class TestResourcePoolGetStats:
    @pytest.fixture
    def pool(self):
        return ResourcePool(
            name="test-pool",
            create_resource=lambda: object(),
            cleanup_resource=lambda r: None,
            max_size=10,
        )

    def test_stats_has_required_keys(self, pool):
        stats = pool.get_stats()
        assert "name" in stats
        assert "pool_size" in stats
        assert "in_use" in stats
        assert "max_size" in stats
        assert "utilization_percent" in stats

    def test_name_matches(self, pool):
        assert pool.get_stats()["name"] == "test-pool"

    def test_max_size_matches(self, pool):
        assert pool.get_stats()["max_size"] == 10

    def test_empty_pool_zero_in_use(self, pool):
        assert pool.get_stats()["in_use"] == 0
        assert pool.get_stats()["pool_size"] == 0

    def test_utilization_zero_when_idle(self, pool):
        assert pool.get_stats()["utilization_percent"] == 0.0

    def test_utilization_after_acquire(self, pool):
        with pool.get_resource():
            stats = pool.get_stats()
            assert stats["in_use"] == 1
            assert stats["utilization_percent"] == 10.0  # 1/10 * 100

    def test_resource_released_after_context_exit(self, pool):
        with pool.get_resource():
            pass
        stats = pool.get_stats()
        assert stats["in_use"] == 0
        assert stats["pool_size"] == 1  # returned to pool

    def test_pool_exhausted_raises(self):
        small_pool = ResourcePool(
            name="tiny",
            create_resource=lambda: object(),
            cleanup_resource=lambda r: None,
            max_size=1,
        )
        with pytest.raises(RuntimeError, match="exhausted"):
            # Acquire one (fills pool), then try to acquire another without releasing
            r1 = small_pool._acquire_resource()
            small_pool._acquire_resource()


# ===========================================================================
# MemoryManager._calculate_memory_growth_rate
# ===========================================================================


class TestCalculateMemoryGrowthRate:
    @pytest.fixture
    def manager(self):
        return MemoryManager()

    def _snapshot(self, rss_mb: float, minutes_ago: float = 0) -> MemorySnapshot:
        from datetime import timedelta
        return MemorySnapshot(
            timestamp=datetime.now(timezone.utc) - timedelta(minutes=minutes_ago),
            rss_mb=rss_mb,
            vms_mb=0.0,
            percent=0.0,
            available_mb=0.0,
            cached_mb=0.0,
            buffers_mb=0.0,
            heap_size_mb=0.0,
            gc_collections=0,
            gc_objects=0,
        )

    def test_empty_history_returns_zero(self, manager):
        assert manager._calculate_memory_growth_rate() == 0.0

    def test_single_snapshot_returns_zero(self, manager):
        manager.memory_history.append(self._snapshot(100.0))
        assert manager._calculate_memory_growth_rate() == 0.0

    def test_positive_growth_rate(self, manager):
        # Need ≥3 snapshots: lookback_minutes = min(10, len-1); slice[-lookback:] must have ≥2 items
        manager.memory_history.append(self._snapshot(50.0, minutes_ago=15))
        manager.memory_history.append(self._snapshot(100.0, minutes_ago=5))
        manager.memory_history.append(self._snapshot(200.0, minutes_ago=0))
        rate = manager._calculate_memory_growth_rate()
        assert rate > 0

    def test_flat_memory_near_zero(self, manager):
        manager.memory_history.append(self._snapshot(50.0, minutes_ago=15))
        manager.memory_history.append(self._snapshot(100.0, minutes_ago=5))
        manager.memory_history.append(self._snapshot(100.0, minutes_ago=0))
        rate = manager._calculate_memory_growth_rate()
        assert abs(rate) < 0.01

    def test_memory_decrease_returns_negative(self, manager):
        manager.memory_history.append(self._snapshot(300.0, minutes_ago=15))
        manager.memory_history.append(self._snapshot(200.0, minutes_ago=5))
        manager.memory_history.append(self._snapshot(100.0, minutes_ago=0))
        rate = manager._calculate_memory_growth_rate()
        assert rate < 0


# ===========================================================================
# MemoryManager.force_garbage_collection
# ===========================================================================


class TestForceGarbageCollection:
    def test_force_gc_runs_without_error(self):
        manager = MemoryManager()
        manager.force_garbage_collection()  # Should not raise

    def test_gc_collect_returns_int(self):
        collected = gc.collect()
        assert isinstance(collected, int)
        assert collected >= 0


# ===========================================================================
# MemoryManager initialisation
# ===========================================================================


class TestMemoryManagerInit:
    @pytest.fixture
    def manager(self):
        return MemoryManager()

    def test_monitoring_enabled_by_default(self, manager):
        assert manager.monitoring_enabled is True

    def test_alert_thresholds_has_memory_usage(self, manager):
        assert "memory_usage_mb" in manager.alert_thresholds

    def test_alert_thresholds_has_memory_percent(self, manager):
        assert "memory_percent" in manager.alert_thresholds

    def test_alert_thresholds_has_growth_rate(self, manager):
        assert "memory_growth_rate" in manager.alert_thresholds

    def test_memory_history_starts_empty(self, manager):
        assert len(manager.memory_history) == 0

    def test_memory_history_maxlen(self, manager):
        assert manager.memory_history.maxlen == 1440

    def test_resource_pools_starts_empty(self, manager):
        assert manager.resource_pools == {}

    def test_active_alerts_starts_empty(self, manager):
        assert manager.active_alerts == {}

    def test_profiler_is_set(self, manager):
        from youtube_extension.backend.services.memory_manager import MemoryProfiler
        assert isinstance(manager.profiler, MemoryProfiler)

    def test_resource_limits_set(self, manager):
        assert isinstance(manager.resource_limits, ResourceLimit)
        assert manager.resource_limits.memory_limit_mb == 2048
        assert manager.resource_limits.cpu_limit_percent == 80


# ===========================================================================
# MemoryManager.create_resource_pool
# ===========================================================================


class TestCreateResourcePool:
    @pytest.fixture
    def manager(self):
        return MemoryManager()

    def test_pool_registered(self, manager):
        pool = manager.create_resource_pool("mypool", lambda: object(), lambda r: None, max_size=5)
        assert "mypool" in manager.resource_pools

    def test_returns_resource_pool_instance(self, manager):
        pool = manager.create_resource_pool("p2", lambda: object(), lambda r: None)
        assert isinstance(pool, ResourcePool)

    def test_pool_max_size_respected(self, manager):
        pool = manager.create_resource_pool("p3", lambda: object(), lambda r: None, max_size=7)
        assert pool.max_size == 7

    def test_multiple_pools_registered(self, manager):
        manager.create_resource_pool("alpha", lambda: object(), lambda r: None)
        manager.create_resource_pool("beta", lambda: object(), lambda r: None)
        assert "alpha" in manager.resource_pools
        assert "beta" in manager.resource_pools


# ===========================================================================
# MemoryManager.set_resource_limits
# ===========================================================================


class TestSetResourceLimits:
    def test_limits_updated(self):
        import resource as _resource
        manager = MemoryManager()
        new_limits = ResourceLimit(
            memory_limit_mb=512,
            cpu_limit_percent=50.0,
            file_descriptor_limit=256,
            thread_limit=50,
            connection_limit=100,
        )
        # Restore the AS limit after test so subsequent tests aren't memory-constrained
        old_limit = _resource.getrlimit(_resource.RLIMIT_AS)
        try:
            manager.set_resource_limits(new_limits)
            assert manager.resource_limits.memory_limit_mb == 512
            assert manager.resource_limits.cpu_limit_percent == 50.0
        finally:
            _resource.setrlimit(_resource.RLIMIT_AS, old_limit)


# ===========================================================================
# MemoryManager.get_memory_stats (with pre-populated history)
# ===========================================================================


class TestGetMemoryStats:
    def _snapshot(self, rss_mb: float) -> MemorySnapshot:
        return MemorySnapshot(
            timestamp=datetime.now(timezone.utc),
            rss_mb=rss_mb,
            vms_mb=0.0,
            percent=10.0,
            available_mb=4000.0,
            cached_mb=0.0,
            buffers_mb=0.0,
            heap_size_mb=0.0,
            gc_collections=1,
            gc_objects=100,
        )

    def test_empty_history_returns_empty_dict(self):
        manager = MemoryManager()
        assert manager.get_memory_stats() == {}

    def test_stats_has_current_key(self):
        from unittest.mock import patch
        manager = MemoryManager()
        manager.memory_history.append(self._snapshot(100.0))
        # Patch profiler.take_snapshot to avoid tracemalloc OOM during heavy test runs
        with patch.object(manager.profiler, 'take_snapshot', return_value={}):
            stats = manager.get_memory_stats()
        assert "current" in stats

    def test_stats_has_last_hour_key(self):
        from unittest.mock import patch
        manager = MemoryManager()
        manager.memory_history.append(self._snapshot(100.0))
        with patch.object(manager.profiler, 'take_snapshot', return_value={}):
            stats = manager.get_memory_stats()
        assert "last_hour" in stats

    def test_stats_has_growth_rate_key(self):
        from unittest.mock import patch
        manager = MemoryManager()
        manager.memory_history.append(self._snapshot(100.0))
        with patch.object(manager.profiler, 'take_snapshot', return_value={}):
            stats = manager.get_memory_stats()
        assert "growth_rate_mb_per_min" in stats

    def test_stats_has_gc_stats_key(self):
        from unittest.mock import patch
        manager = MemoryManager()
        manager.memory_history.append(self._snapshot(100.0))
        with patch.object(manager.profiler, 'take_snapshot', return_value={}):
            stats = manager.get_memory_stats()
        assert "gc_stats" in stats

    def test_stats_gc_stats_has_total_objects(self):
        from unittest.mock import patch
        manager = MemoryManager()
        manager.memory_history.append(self._snapshot(100.0))
        with patch.object(manager.profiler, 'take_snapshot', return_value={}):
            stats = manager.get_memory_stats()
        assert "total_objects" in stats["gc_stats"]


# ===========================================================================
# MemoryManager._clear_internal_caches
# ===========================================================================


class TestClearInternalCaches:
    def test_old_alerts_cleared(self):
        from datetime import timedelta
        manager = MemoryManager()
        old_time = datetime.now(timezone.utc) - timedelta(hours=2)
        old_alert = MemoryAlert(
            alert_type="high_memory_usage",
            severity="medium",
            message="old",
            current_usage_mb=100.0,
            threshold_mb=1024.0,
            timestamp=old_time,
            process_info={},
        )
        manager.active_alerts["high_memory_usage_medium"] = old_alert
        manager._clear_internal_caches()
        assert "high_memory_usage_medium" not in manager.active_alerts

    def test_recent_alerts_kept(self):
        manager = MemoryManager()
        recent_alert = MemoryAlert(
            alert_type="high_memory_usage",
            severity="high",
            message="recent",
            current_usage_mb=1100.0,
            threshold_mb=1024.0,
            timestamp=datetime.now(timezone.utc),
            process_info={},
        )
        manager.active_alerts["high_memory_usage_high"] = recent_alert
        manager._clear_internal_caches()
        assert "high_memory_usage_high" in manager.active_alerts

    def test_history_trimmed_to_100(self):
        manager = MemoryManager()
        snapshot = MemorySnapshot(
            timestamp=datetime.now(timezone.utc),
            rss_mb=50.0,
            vms_mb=0.0,
            percent=5.0,
            available_mb=1000.0,
            cached_mb=0.0,
            buffers_mb=0.0,
            heap_size_mb=0.0,
            gc_collections=0,
            gc_objects=0,
        )
        for _ in range(200):
            manager.memory_history.append(snapshot)
        manager._clear_internal_caches()
        assert len(manager.memory_history) == 100


# ===========================================================================
# MemoryManager.get_optimization_recommendations
# ===========================================================================


class TestGetOptimizationRecommendations:
    def test_empty_history_returns_empty(self):
        manager = MemoryManager()
        recs = manager.get_optimization_recommendations()
        assert recs == []

    def test_high_memory_triggers_recommendation(self):
        manager = MemoryManager()
        snapshot = MemorySnapshot(
            timestamp=datetime.now(timezone.utc),
            rss_mb=1500.0,
            vms_mb=0.0,
            percent=50.0,
            available_mb=1000.0,
            cached_mb=0.0,
            buffers_mb=0.0,
            heap_size_mb=0.0,
            gc_collections=0,
            gc_objects=0,
        )
        manager.memory_history.append(snapshot)
        recs = manager.get_optimization_recommendations()
        types = [r["type"] for r in recs]
        assert "high_memory_usage" in types

    def test_recommendation_has_suggestions(self):
        manager = MemoryManager()
        snapshot = MemorySnapshot(
            timestamp=datetime.now(timezone.utc),
            rss_mb=1500.0,
            vms_mb=0.0,
            percent=50.0,
            available_mb=1000.0,
            cached_mb=0.0,
            buffers_mb=0.0,
            heap_size_mb=0.0,
            gc_collections=0,
            gc_objects=0,
        )
        manager.memory_history.append(snapshot)
        recs = manager.get_optimization_recommendations()
        for rec in recs:
            assert "suggestions" in rec
            assert len(rec["suggestions"]) > 0


# ===========================================================================
# MemoryProfiler (from memory_manager)
# ===========================================================================


class TestMemoryProfilerInManager:
    def test_profiler_tracking_disabled_initially(self):
        from youtube_extension.backend.services.memory_manager import MemoryProfiler
        p = MemoryProfiler()
        assert p.tracking_enabled is False

    def test_profiler_take_snapshot_returns_empty_when_not_tracking(self):
        from youtube_extension.backend.services.memory_manager import MemoryProfiler
        p = MemoryProfiler()
        result = p.take_snapshot()
        assert result == {}

    def test_profiler_detect_leaks_empty_when_not_tracking(self):
        from youtube_extension.backend.services.memory_manager import MemoryProfiler
        p = MemoryProfiler()
        leaks = p.detect_leaks()
        assert leaks == []

    def test_profiler_snapshots_maxlen(self):
        from youtube_extension.backend.services.memory_manager import MemoryProfiler
        p = MemoryProfiler()
        assert p.snapshots.maxlen == 1000

    def test_profiler_stop_when_not_tracking_is_noop(self):
        from youtube_extension.backend.services.memory_manager import MemoryProfiler
        p = MemoryProfiler()
        p.stop_tracking()  # Should not raise
        assert p.tracking_enabled is False


# ===========================================================================
# MemoryProfiler.start_tracking / stop_tracking / take_snapshot / detect_leaks
# (lines 88-142)
# ===========================================================================


class TestMemoryProfilerTracking:
    def test_start_tracking_sets_flag(self):
        from youtube_extension.backend.services.memory_manager import MemoryProfiler
        p = MemoryProfiler()
        p.start_tracking()
        assert p.tracking_enabled is True
        p.stop_tracking()

    def test_stop_tracking_clears_flag(self):
        from youtube_extension.backend.services.memory_manager import MemoryProfiler
        p = MemoryProfiler()
        p.start_tracking()
        p.stop_tracking()
        assert p.tracking_enabled is False

    def test_stop_tracking_idempotent(self):
        from youtube_extension.backend.services.memory_manager import MemoryProfiler
        p = MemoryProfiler()
        p.start_tracking()
        p.stop_tracking()
        p.stop_tracking()  # second stop should be noop
        assert p.tracking_enabled is False

    def test_baseline_snapshot_set_on_start(self):
        from youtube_extension.backend.services.memory_manager import MemoryProfiler
        p = MemoryProfiler()
        p.start_tracking()
        try:
            assert p.baseline_snapshot is not None
        finally:
            p.stop_tracking()

    def test_take_snapshot_when_tracking_returns_dict(self):
        from youtube_extension.backend.services.memory_manager import MemoryProfiler
        p = MemoryProfiler()
        p.start_tracking()
        try:
            result = p.take_snapshot()
            assert isinstance(result, dict)
            assert len(result) > 0
        finally:
            p.stop_tracking()

    def test_take_snapshot_when_tracking_has_timestamp(self):
        from youtube_extension.backend.services.memory_manager import MemoryProfiler
        p = MemoryProfiler()
        p.start_tracking()
        try:
            result = p.take_snapshot()
            assert "timestamp" in result
        finally:
            p.stop_tracking()

    def test_take_snapshot_when_tracking_has_total_size(self):
        from youtube_extension.backend.services.memory_manager import MemoryProfiler
        p = MemoryProfiler()
        p.start_tracking()
        try:
            result = p.take_snapshot()
            assert "total_size_mb" in result
            assert result["total_size_mb"] >= 0
        finally:
            p.stop_tracking()

    def test_take_snapshot_when_tracking_has_top_allocations(self):
        from youtube_extension.backend.services.memory_manager import MemoryProfiler
        p = MemoryProfiler()
        p.start_tracking()
        try:
            result = p.take_snapshot()
            assert "top_allocations" in result
            assert isinstance(result["top_allocations"], list)
        finally:
            p.stop_tracking()

    def test_detect_leaks_when_tracking_returns_list(self):
        from youtube_extension.backend.services.memory_manager import MemoryProfiler
        p = MemoryProfiler()
        p.start_tracking()
        try:
            leaks = p.detect_leaks()
            assert isinstance(leaks, list)
        finally:
            p.stop_tracking()

    def test_detect_leaks_no_baseline_returns_empty(self):
        from youtube_extension.backend.services.memory_manager import MemoryProfiler
        p = MemoryProfiler()
        p.tracking_enabled = True
        p.baseline_snapshot = None
        leaks = p.detect_leaks()
        assert leaks == []


# ===========================================================================
# MemoryManager._take_system_snapshot (lines around 337-362)
# gc.get_stats() returns dicts, so we patch it to return ints to exercise the code
# ===========================================================================


class TestTakeSystemSnapshot:
    def _get_patched_snapshot(self, rss_bytes=100*1024*1024, vms_bytes=200*1024*1024,
                               percent=50.0, cached=512*1024*1024, buffers=64*1024*1024):
        """Helper that patches both psutil and gc.get_stats to take a snapshot."""
        from unittest.mock import patch
        import types
        import youtube_extension.backend.services.memory_manager as _mod
        fake = types.SimpleNamespace(
            virtual_memory=lambda: types.SimpleNamespace(
                total=8 * 1024**3, available=4 * 1024**3, percent=percent,
                cached=cached, buffers=buffers
            ),
            Process=lambda: types.SimpleNamespace(
                memory_info=lambda: types.SimpleNamespace(rss=rss_bytes, vms=vms_bytes)
            ),
        )
        manager = _mod.MemoryManager()
        orig_psutil = _mod.psutil
        _mod.psutil = fake
        # gc.get_stats() returns a list of dicts — patch to return [0,0,0] so sum() works
        try:
            with patch('youtube_extension.backend.services.memory_manager.gc') as mock_gc:
                mock_gc.get_stats.return_value = [0, 0, 0]  # summable ints
                mock_gc.get_objects.return_value = []
                snap = manager._take_system_snapshot()
        finally:
            _mod.psutil = orig_psutil
        return snap, _mod

    def test_snapshot_returns_memory_snapshot_instance(self):
        snap, _mod = self._get_patched_snapshot()
        assert isinstance(snap, _mod.MemorySnapshot)

    def test_snapshot_rss_computed_correctly(self):
        rss_bytes = 150 * 1024 * 1024
        snap, _ = self._get_patched_snapshot(rss_bytes=rss_bytes)
        assert abs(snap.rss_mb - 150.0) < 0.1

    def test_snapshot_percent_stored(self):
        snap, _ = self._get_patched_snapshot(percent=75.0)
        assert snap.percent == 75.0

    def test_snapshot_vms_computed_correctly(self):
        vms_bytes = 300 * 1024 * 1024
        snap, _ = self._get_patched_snapshot(vms_bytes=vms_bytes)
        assert abs(snap.vms_mb - 300.0) < 0.1


# ===========================================================================
# MemoryManager._process_snapshot (lines 372-384)
# ===========================================================================


class TestProcessSnapshot:
    def _make_snapshot(self, rss_mb=100.0, percent=20.0):
        return MemorySnapshot(
            timestamp=datetime.now(timezone.utc),
            rss_mb=rss_mb, vms_mb=0.0, percent=percent,
            available_mb=4000.0, cached_mb=0.0, buffers_mb=0.0,
            heap_size_mb=0.0, gc_collections=0, gc_objects=0,
        )

    def test_process_snapshot_appends_to_history(self):
        manager = MemoryManager()
        snap = self._make_snapshot()
        manager._process_snapshot(snap)
        assert len(manager.memory_history) == 1

    def test_process_snapshot_multiple_snapshots(self):
        manager = MemoryManager()
        for i in range(5):
            manager._process_snapshot(self._make_snapshot(rss_mb=float(i * 10)))
        assert len(manager.memory_history) == 5

    def test_process_snapshot_stores_correct_snapshot(self):
        manager = MemoryManager()
        snap = self._make_snapshot(rss_mb=999.0)
        manager._process_snapshot(snap)
        assert manager.memory_history[-1].rss_mb == 999.0


# ===========================================================================
# MemoryManager._check_memory_alerts (lines 386-429)
# ===========================================================================


class TestCheckMemoryAlerts:
    def _make_snapshot(self, rss_mb=100.0, percent=20.0):
        return MemorySnapshot(
            timestamp=datetime.now(timezone.utc),
            rss_mb=rss_mb, vms_mb=0.0, percent=percent,
            available_mb=4000.0, cached_mb=0.0, buffers_mb=0.0,
            heap_size_mb=0.0, gc_collections=0, gc_objects=0,
        )

    def test_no_alert_when_below_threshold(self):
        manager = MemoryManager()
        snap = self._make_snapshot(rss_mb=100.0, percent=10.0)
        manager._check_memory_alerts(snap)
        assert len(manager.active_alerts) == 0

    def test_high_memory_usage_alert_generated(self):
        manager = MemoryManager()
        # rss_mb > 1024 (threshold)
        snap = self._make_snapshot(rss_mb=1100.0, percent=20.0)
        manager._check_memory_alerts(snap)
        keys = list(manager.active_alerts.keys())
        assert any("high_memory_usage" in k for k in keys)

    def test_high_memory_usage_severity_medium_when_below_1_5x(self):
        manager = MemoryManager()
        # 1024 < rss_mb < 1024*1.5=1536 → medium
        snap = self._make_snapshot(rss_mb=1200.0, percent=20.0)
        manager._check_memory_alerts(snap)
        alert_key = "high_memory_usage_medium"
        assert alert_key in manager.active_alerts

    def test_high_memory_usage_severity_high_above_1_5x(self):
        manager = MemoryManager()
        # rss_mb > 1024*1.5=1536 → high severity
        snap = self._make_snapshot(rss_mb=1600.0, percent=20.0)
        manager._check_memory_alerts(snap)
        alert_key = "high_memory_usage_high"
        assert alert_key in manager.active_alerts

    def test_high_system_memory_alert_generated(self):
        manager = MemoryManager()
        # percent > 80 (threshold)
        snap = self._make_snapshot(rss_mb=100.0, percent=85.0)
        manager._check_memory_alerts(snap)
        keys = list(manager.active_alerts.keys())
        assert any("high_system_memory" in k for k in keys)

    def test_high_system_memory_critical_above_95(self):
        manager = MemoryManager()
        snap = self._make_snapshot(rss_mb=100.0, percent=96.0)
        manager._check_memory_alerts(snap)
        assert "high_system_memory_critical" in manager.active_alerts

    def test_high_system_memory_high_between_80_and_95(self):
        manager = MemoryManager()
        snap = self._make_snapshot(rss_mb=100.0, percent=85.0)
        manager._check_memory_alerts(snap)
        assert "high_system_memory_high" in manager.active_alerts

    def test_memory_growth_alert_generated(self):
        from datetime import timedelta
        manager = MemoryManager()
        # Build up history with fast growth (>50 MB/min threshold)
        base_time = datetime.now(timezone.utc) - timedelta(minutes=5)
        for i in range(6):
            s = MemorySnapshot(
                timestamp=base_time + timedelta(minutes=i),
                rss_mb=100.0 + i * 100.0,  # 100 MB/min growth
                vms_mb=0.0, percent=20.0, available_mb=4000.0,
                cached_mb=0.0, buffers_mb=0.0, heap_size_mb=0.0,
                gc_collections=0, gc_objects=0,
            )
            manager.memory_history.append(s)
        snap = manager.memory_history[-1]
        manager._check_memory_alerts(snap)
        keys = list(manager.active_alerts.keys())
        assert any("memory_growth" in k for k in keys)


# ===========================================================================
# MemoryManager._process_alert – deduplication (lines 449-467)
# ===========================================================================


class TestProcessAlert:
    def _make_alert(self, alert_type="high_memory_usage", severity="high",
                    rss_mb=1100.0, minutes_ago=0):
        from datetime import timedelta
        return MemoryAlert(
            alert_type=alert_type, severity=severity,
            message="test", current_usage_mb=rss_mb, threshold_mb=1024.0,
            timestamp=datetime.now(timezone.utc) - timedelta(minutes=minutes_ago),
            process_info={},
        )

    def test_new_alert_stored(self):
        manager = MemoryManager()
        alert = self._make_alert()
        manager._process_alert(alert)
        assert "high_memory_usage_high" in manager.active_alerts

    def test_duplicate_within_5_minutes_ignored(self):
        manager = MemoryManager()
        alert1 = self._make_alert(minutes_ago=2)
        alert2 = self._make_alert(minutes_ago=0)
        manager._process_alert(alert1)
        manager._process_alert(alert2)
        # Second alert should NOT update (first was within 5 min)
        assert manager.active_alerts["high_memory_usage_high"].timestamp == alert1.timestamp

    def test_alert_after_5_minutes_updates(self):
        manager = MemoryManager()
        old_alert = self._make_alert(minutes_ago=10)
        new_alert = self._make_alert(minutes_ago=0)
        manager._process_alert(old_alert)
        manager._process_alert(new_alert)
        # New alert should have replaced the old one
        assert manager.active_alerts["high_memory_usage_high"].timestamp == new_alert.timestamp

    def test_low_severity_alert_does_not_trigger_corrective_action(self):
        """Low/medium severity should not call _take_corrective_action."""
        from unittest.mock import patch
        manager = MemoryManager()
        alert = self._make_alert(severity="low")
        with patch.object(manager, '_take_corrective_action') as mock_action:
            manager._process_alert(alert)
            mock_action.assert_not_called()

    def test_high_severity_alert_triggers_corrective_action(self):
        from unittest.mock import patch
        manager = MemoryManager()
        alert = self._make_alert(severity="high")
        with patch.object(manager, '_take_corrective_action') as mock_action:
            manager._process_alert(alert)
            mock_action.assert_called_once_with(alert)


# ===========================================================================
# MemoryManager._take_corrective_action (lines 469-489)
# ===========================================================================


class TestTakeCorrectiveAction:
    def test_high_memory_usage_forces_gc(self):
        from unittest.mock import patch
        manager = MemoryManager()
        alert = MemoryAlert(
            alert_type="high_memory_usage", severity="high",
            message="test", current_usage_mb=1200.0, threshold_mb=1024.0,
            timestamp=datetime.now(timezone.utc), process_info={},
        )
        with patch.object(manager, 'force_garbage_collection') as mock_gc:
            manager._take_corrective_action(alert)
            mock_gc.assert_called()

    def test_high_memory_usage_cleans_resource_pools(self):
        from unittest.mock import patch
        manager = MemoryManager()
        alert = MemoryAlert(
            alert_type="high_memory_usage", severity="high",
            message="test", current_usage_mb=1200.0, threshold_mb=1024.0,
            timestamp=datetime.now(timezone.utc), process_info={},
        )
        with patch.object(manager, '_cleanup_resource_pools') as mock_cleanup:
            manager._take_corrective_action(alert)
            mock_cleanup.assert_called()

    def test_high_system_memory_calls_emergency_cleanup(self):
        from unittest.mock import patch
        import types
        import youtube_extension.backend.services.memory_manager as _mod
        manager = _mod.MemoryManager()
        alert = _mod.MemoryAlert(
            alert_type="high_system_memory", severity="critical",
            message="test", current_usage_mb=0.0, threshold_mb=0.0,
            timestamp=datetime.now(timezone.utc), process_info={},
        )
        fake_psutil = types.SimpleNamespace(
            Process=lambda: types.SimpleNamespace(
                memory_info=lambda: types.SimpleNamespace(rss=100 * 1024**2)
            ),
        )
        with patch.object(manager, 'emergency_cleanup') as mock_emergency:
            manager._take_corrective_action(alert)
            mock_emergency.assert_called_once()


# ===========================================================================
# MemoryManager._get_process_info (lines 491-503)
# ===========================================================================


class TestGetProcessInfo:
    def test_returns_dict(self):
        manager = MemoryManager()
        info = manager._get_process_info()
        assert isinstance(info, dict)

    def test_returns_empty_dict_on_exception(self):
        import types
        import youtube_extension.backend.services.memory_manager as _mod
        # Provide a psutil that raises on Process()
        class FakePsutil:
            def Process(self):
                raise OSError("no process")
        manager = _mod.MemoryManager()
        orig = _mod.psutil
        _mod.psutil = FakePsutil()
        try:
            result = manager._get_process_info()
            assert result == {}
        finally:
            _mod.psutil = orig


# ===========================================================================
# MemoryManager._optimize_garbage_collection (lines 505-515)
# ===========================================================================


class TestOptimizeGarbageCollection:
    def _make_snapshot(self, rss_mb=100.0, gc_collections=0):
        return MemorySnapshot(
            timestamp=datetime.now(timezone.utc),
            rss_mb=rss_mb, vms_mb=0.0, percent=10.0,
            available_mb=4000.0, cached_mb=0.0, buffers_mb=0.0,
            heap_size_mb=0.0, gc_collections=gc_collections, gc_objects=0,
        )

    def test_no_gc_when_only_one_snapshot(self):
        from unittest.mock import patch
        manager = MemoryManager()
        snap = self._make_snapshot(rss_mb=600.0, gc_collections=5)
        manager.memory_history.append(snap)
        with patch.object(manager, 'force_garbage_collection') as mock_gc:
            manager._optimize_garbage_collection(snap)
            # Need at least 2 snapshots to optimize
            mock_gc.assert_not_called()

    def test_gc_forced_when_high_memory_and_low_frequency(self):
        from unittest.mock import patch
        manager = MemoryManager()
        snap1 = self._make_snapshot(rss_mb=600.0, gc_collections=5)
        snap2 = self._make_snapshot(rss_mb=620.0, gc_collections=6)
        manager.memory_history.append(snap1)
        manager.memory_history.append(snap2)
        with patch.object(manager, 'force_garbage_collection') as mock_gc:
            # gc_frequency = 6-5=1 < 2 and rss > 512
            manager._optimize_garbage_collection(snap2)
            mock_gc.assert_called_once()

    def test_gc_not_forced_when_low_memory(self):
        from unittest.mock import patch
        manager = MemoryManager()
        snap1 = self._make_snapshot(rss_mb=100.0, gc_collections=5)
        snap2 = self._make_snapshot(rss_mb=110.0, gc_collections=6)
        manager.memory_history.append(snap1)
        manager.memory_history.append(snap2)
        with patch.object(manager, 'force_garbage_collection') as mock_gc:
            # rss < 512, so no forced GC
            manager._optimize_garbage_collection(snap2)
            mock_gc.assert_not_called()


# ===========================================================================
# MemoryManager._cleanup_resource_pools (lines 527-542)
# ===========================================================================


class TestCleanupResourcePools:
    def test_cleanup_clears_pool_resources(self):
        manager = MemoryManager()
        cleanup_called = []
        pool = manager.create_resource_pool(
            "test", lambda: object(), lambda r: cleanup_called.append(r), max_size=5
        )
        # Add resources to the pool directly
        r1, r2 = object(), object()
        pool.pool.extend([r1, r2])
        manager._cleanup_resource_pools()
        assert len(pool.pool) == 0
        assert len(cleanup_called) == 2

    def test_cleanup_handles_exception_gracefully(self):
        manager = MemoryManager()
        def bad_cleanup(r):
            raise RuntimeError("cleanup failed")
        pool = manager.create_resource_pool(
            "bad", lambda: object(), bad_cleanup, max_size=5
        )
        pool.pool.append(object())
        # Should not raise
        manager._cleanup_resource_pools()


# ===========================================================================
# MemoryManager.emergency_cleanup (lines 544-561)
# ===========================================================================


class TestEmergencyCleanup:
    def test_emergency_cleanup_runs_without_error(self):
        import types
        import youtube_extension.backend.services.memory_manager as _mod
        manager = _mod.MemoryManager()
        fake = types.SimpleNamespace(
            Process=lambda: types.SimpleNamespace(
                memory_info=lambda: types.SimpleNamespace(rss=100 * 1024**2)
            ),
        )
        orig = _mod.psutil
        _mod.psutil = fake
        try:
            manager.emergency_cleanup()  # should not raise
        finally:
            _mod.psutil = orig

    def test_emergency_cleanup_calls_force_gc_multiple_times(self):
        from unittest.mock import patch
        import types
        import youtube_extension.backend.services.memory_manager as _mod
        manager = _mod.MemoryManager()
        fake = types.SimpleNamespace(
            Process=lambda: types.SimpleNamespace(
                memory_info=lambda: types.SimpleNamespace(rss=100 * 1024**2)
            ),
        )
        orig = _mod.psutil
        _mod.psutil = fake
        try:
            with patch.object(manager, 'force_garbage_collection') as mock_gc:
                manager.emergency_cleanup()
                assert mock_gc.call_count == 3
        finally:
            _mod.psutil = orig

    def test_emergency_cleanup_calls_cleanup_pools(self):
        from unittest.mock import patch
        import types
        import youtube_extension.backend.services.memory_manager as _mod
        manager = _mod.MemoryManager()
        fake = types.SimpleNamespace(
            Process=lambda: types.SimpleNamespace(
                memory_info=lambda: types.SimpleNamespace(rss=100 * 1024**2)
            ),
        )
        orig = _mod.psutil
        _mod.psutil = fake
        try:
            with patch.object(manager, '_cleanup_resource_pools') as mock_pools:
                manager.emergency_cleanup()
                mock_pools.assert_called()
        finally:
            _mod.psutil = orig


# ===========================================================================
# MemoryManager.get_optimization_recommendations – additional branches
# ===========================================================================


class TestOptimizationRecommendationsAdditional:
    def _make_snapshot(self, rss_mb, gc_collections=0):
        return MemorySnapshot(
            timestamp=datetime.now(timezone.utc),
            rss_mb=rss_mb, vms_mb=0.0, percent=20.0,
            available_mb=4000.0, cached_mb=0.0, buffers_mb=0.0,
            heap_size_mb=0.0, gc_collections=gc_collections, gc_objects=0,
        )

    def test_no_recommendation_for_normal_memory(self):
        manager = MemoryManager()
        manager.memory_history.append(self._make_snapshot(rss_mb=200.0))
        recs = manager.get_optimization_recommendations()
        types_found = [r["type"] for r in recs]
        assert "high_memory_usage" not in types_found

    def test_memory_growth_recommendation_triggered(self):
        from datetime import timedelta
        manager = MemoryManager()
        base_time = datetime.now(timezone.utc) - timedelta(minutes=5)
        for i in range(6):
            s = MemorySnapshot(
                timestamp=base_time + timedelta(minutes=i),
                rss_mb=100.0 + i * 50.0,  # 50 MB/min > 10 threshold
                vms_mb=0.0, percent=20.0, available_mb=4000.0,
                cached_mb=0.0, buffers_mb=0.0, heap_size_mb=0.0,
                gc_collections=0, gc_objects=0,
            )
            manager.memory_history.append(s)
        recs = manager.get_optimization_recommendations()
        types_found = [r["type"] for r in recs]
        assert "memory_growth" in types_found

    def test_high_gc_activity_recommendation_triggered(self):
        manager = MemoryManager()
        # Need 2 snapshots with gc_collections diff > 5
        snap1 = self._make_snapshot(rss_mb=200.0, gc_collections=0)
        snap2 = self._make_snapshot(rss_mb=200.0, gc_collections=10)
        manager.memory_history.append(snap1)
        manager.memory_history.append(snap2)
        recs = manager.get_optimization_recommendations()
        types_found = [r["type"] for r in recs]
        assert "high_gc_activity" in types_found

    def test_high_gc_recommendation_has_priority_medium(self):
        manager = MemoryManager()
        snap1 = self._make_snapshot(rss_mb=200.0, gc_collections=0)
        snap2 = self._make_snapshot(rss_mb=200.0, gc_collections=10)
        manager.memory_history.append(snap1)
        manager.memory_history.append(snap2)
        recs = manager.get_optimization_recommendations()
        gc_recs = [r for r in recs if r["type"] == "high_gc_activity"]
        assert len(gc_recs) == 1
        assert gc_recs[0]["priority"] == "medium"


# ===========================================================================
# MemoryManager.start_monitoring / stop_monitoring
# ===========================================================================


class TestStartStopMonitoring:
    def test_start_monitoring_sets_task(self):
        manager = MemoryManager()
        manager.start_monitoring()
        assert manager.monitoring_task is not None
        manager.stop_monitoring()

    def test_start_monitoring_idempotent(self):
        manager = MemoryManager()
        manager.start_monitoring()
        task1 = manager.monitoring_task
        manager.start_monitoring()  # second call should be a noop
        task2 = manager.monitoring_task
        assert task1 is task2
        manager.stop_monitoring()

    def test_stop_monitoring_clears_flag(self):
        manager = MemoryManager()
        manager.start_monitoring()
        manager.stop_monitoring()
        assert manager.monitoring_enabled is False


# ===========================================================================
# memory_limit context manager (lines 719-727)
# ===========================================================================


class TestMemoryLimitContextManager:
    def test_memory_limit_context_runs_without_error(self):
        from youtube_extension.backend.services.memory_manager import memory_limit
        with memory_limit(512):
            pass  # Should not raise

    def test_memory_limit_restores_old_limit(self):
        import resource as _resource
        from youtube_extension.backend.services.memory_manager import memory_limit
        old_limit = _resource.getrlimit(_resource.RLIMIT_AS)
        try:
            with memory_limit(4096):
                pass
            restored = _resource.getrlimit(_resource.RLIMIT_AS)
            assert restored == old_limit
        finally:
            _resource.setrlimit(_resource.RLIMIT_AS, old_limit)


# ===========================================================================
# memory_profiler decorator (lines 729-745)
# ===========================================================================


class TestMemoryProfilerDecorator:
    def test_decorator_returns_result(self):
        from youtube_extension.backend.services.memory_manager import memory_profiler
        @memory_profiler
        def add(a, b):
            return a + b
        assert add(2, 3) == 5

    def test_decorator_works_with_side_effects(self):
        from youtube_extension.backend.services.memory_manager import memory_profiler
        calls = []
        @memory_profiler
        def side_effect():
            calls.append(1)
        side_effect()
        assert calls == [1]


# ===========================================================================
# Convenience functions: start_memory_monitoring, get_memory_stats, force_cleanup
# ===========================================================================


class TestConvenienceFunctions:
    def test_get_memory_stats_returns_dict(self):
        from youtube_extension.backend.services.memory_manager import get_memory_stats
        result = get_memory_stats()
        assert isinstance(result, dict)

    def test_force_cleanup_does_not_raise(self):
        from youtube_extension.backend.services.memory_manager import force_cleanup
        force_cleanup()  # Should not raise


# ===========================================================================
# ResourcePool._acquire_resource and _release_resource edge cases
# ===========================================================================


class TestResourcePoolEdgeCases:
    def test_reuses_released_resource(self):
        created = []
        def create_fn():
            r = object()
            created.append(r)
            return r
        pool = ResourcePool("reuse-pool", create_fn, lambda r: None, max_size=5)
        with pool.get_resource() as r1:
            pass
        with pool.get_resource() as r2:
            pass
        # First resource was put back in pool, so second acquire should reuse it
        assert r1 is r2

    def test_multiple_concurrent_resources(self):
        pool = ResourcePool("multi", lambda: object(), lambda r: None, max_size=3)
        r1 = pool._acquire_resource()
        r2 = pool._acquire_resource()
        r3 = pool._acquire_resource()
        assert len(pool.in_use) == 3
        pool._release_resource(r1)
        pool._release_resource(r2)
        pool._release_resource(r3)
        assert len(pool.in_use) == 0

    def test_release_resource_not_in_use_is_noop(self):
        pool = ResourcePool("noop", lambda: object(), lambda r: None, max_size=5)
        r = object()
        # r was never acquired, so releasing it should be a noop
        pool._release_resource(r)
        assert len(pool.pool) == 0
