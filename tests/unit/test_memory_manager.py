"""Unit tests for MemorySnapshot, MemoryAlert, ResourceLimit, and ResourcePool."""

from __future__ import annotations

import gc
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

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
