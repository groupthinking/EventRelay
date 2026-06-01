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
