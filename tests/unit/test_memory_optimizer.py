"""Unit tests for MemorySnapshot, MemoryLeak, and MemoryProfiler."""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

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
