"""Unit tests for MetricPoint and MetricSeries — pure dataclass logic."""

from __future__ import annotations

import asyncio
import contextlib
import json
import sys
import time
import types
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

# Stub psutil so the import succeeds without the native library
_psutil_stub = types.ModuleType("psutil")
_psutil_stub.cpu_percent = MagicMock(return_value=10.0)
_psutil_stub.cpu_count = MagicMock(return_value=4)
_psutil_stub.cpu_freq = MagicMock(return_value=MagicMock(current=2400.0))
_mem = MagicMock()
_mem.percent = 50.0
_mem.used = 4 * 1024 ** 3
_mem.total = 8 * 1024 ** 3
_psutil_stub.virtual_memory = MagicMock(return_value=_mem)
_disk = MagicMock()
_disk.percent = 30.0
_disk.used = 50 * 1024 ** 3
_disk.total = 200 * 1024 ** 3
_psutil_stub.disk_usage = MagicMock(return_value=_disk)
_net = MagicMock()
_net.bytes_sent = 1000
_net.bytes_recv = 2000
_psutil_stub.net_io_counters = MagicMock(return_value=_net)
sys.modules.setdefault("psutil", _psutil_stub)

from youtube_extension.backend.services.metrics_service import MetricPoint, MetricSeries

# ===========================================================================
# MetricPoint
# ===========================================================================


class TestMetricPoint:
    def test_required_fields(self):
        now = datetime.utcnow()
        p = MetricPoint(name="cpu", value=42.5, timestamp=now)
        assert p.name == "cpu"
        assert p.value == 42.5
        assert p.timestamp == now

    def test_default_tags_empty(self):
        p = MetricPoint(name="mem", value=100)
        assert p.tags == {}

    def test_default_metadata_empty(self):
        p = MetricPoint(name="mem", value=100)
        assert p.metadata == {}

    def test_custom_tags(self):
        p = MetricPoint(name="req", value=1, tags={"host": "web-1"})
        assert p.tags["host"] == "web-1"

    def test_integer_value(self):
        p = MetricPoint(name="count", value=10)
        assert p.value == 10


# ===========================================================================
# MetricSeries
# ===========================================================================


class TestMetricSeriesAddPoint:
    def test_add_point_increments_length(self):
        s = MetricSeries(name="cpu")
        s.add_point(50.0)
        assert len(s.points) == 1

    def test_add_multiple_points(self):
        s = MetricSeries(name="cpu")
        for v in [10, 20, 30]:
            s.add_point(v)
        assert len(s.points) == 3

    def test_custom_timestamp_stored(self):
        s = MetricSeries(name="cpu")
        t = datetime(2024, 1, 1, 12, 0, 0)
        s.add_point(99.0, timestamp=t)
        assert s.points[-1].timestamp == t

    def test_point_name_matches_series_name(self):
        s = MetricSeries(name="latency")
        s.add_point(200)
        assert s.points[-1].name == "latency"

    def test_tags_passed_through(self):
        s = MetricSeries(name="req")
        s.add_point(1, tags={"env": "prod"})
        assert s.points[-1].tags["env"] == "prod"


class TestMetricSeriesGetRecentPoints:
    def test_returns_all_recent_points(self):
        s = MetricSeries(name="cpu")
        for v in [1, 2, 3]:
            s.add_point(v)
        recent = s.get_recent_points(seconds=300)
        assert len(recent) == 3

    def test_excludes_old_points(self):
        s = MetricSeries(name="cpu")
        old_time = datetime.utcnow() - timedelta(seconds=400)
        s.add_point(99, timestamp=old_time)
        s.add_point(1)  # recent
        recent = s.get_recent_points(seconds=300)
        assert len(recent) == 1
        assert recent[0].value == 1

    def test_empty_series_returns_empty(self):
        s = MetricSeries(name="cpu")
        assert s.get_recent_points() == []

    def test_all_old_points_excluded(self):
        s = MetricSeries(name="cpu")
        old = datetime.utcnow() - timedelta(seconds=600)
        s.add_point(50, timestamp=old)
        assert s.get_recent_points(seconds=300) == []


class TestMetricSeriesGetAggregatedStats:
    def test_empty_returns_zero_stats(self):
        s = MetricSeries(name="cpu")
        stats = s.get_aggregated_stats()
        assert stats == {"count": 0, "mean": 0, "min": 0, "max": 0}

    def test_single_point_stats(self):
        s = MetricSeries(name="cpu")
        s.add_point(50.0)
        stats = s.get_aggregated_stats()
        assert stats["count"] == 1
        assert stats["mean"] == 50.0
        assert stats["min"] == 50.0
        assert stats["max"] == 50.0
        assert stats["std_dev"] == 0

    def test_multiple_points_mean(self):
        s = MetricSeries(name="cpu")
        for v in [10, 20, 30]:
            s.add_point(v)
        stats = s.get_aggregated_stats()
        assert stats["mean"] == 20.0
        assert stats["min"] == 10
        assert stats["max"] == 30

    def test_std_dev_computed_for_multiple(self):
        s = MetricSeries(name="cpu")
        for v in [10, 20, 30]:
            s.add_point(v)
        stats = s.get_aggregated_stats()
        assert stats["std_dev"] > 0

    def test_latest_and_oldest_values(self):
        s = MetricSeries(name="cpu")
        s.add_point(5)
        s.add_point(15)
        s.add_point(25)
        stats = s.get_aggregated_stats()
        assert stats["oldest"] == 5
        assert stats["latest"] == 25

    def test_median_computed(self):
        s = MetricSeries(name="cpu")
        for v in [1, 2, 3, 4, 5]:
            s.add_point(v)
        stats = s.get_aggregated_stats()
        assert stats["median"] == 3


# ===========================================================================
# MetricsService init
# ===========================================================================


from youtube_extension.backend.services.metrics_service import (
    MetricsService,  # noqa: E402
)


class TestMetricsServiceInit:
    def test_metrics_dict_empty(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        svc = MetricsService()
        assert svc.metrics == {}

    def test_collection_interval_default(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        svc = MetricsService()
        assert svc.collection_interval == 60

    def test_retention_period_default(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        svc = MetricsService()
        assert svc.retention_period == 3600

    def test_not_running_initially(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        svc = MetricsService()
        assert svc._running is False

    def test_collection_task_initially_none(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        svc = MetricsService()
        assert svc._collection_task is None

    def test_custom_collection_interval(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        svc = MetricsService(config={"collection_interval": 30})
        assert svc.collection_interval == 30


class TestMetricsServicePersistMetrics:
    @pytest.mark.asyncio
    async def test_persist_metrics_writes_metrics_file(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        svc = MetricsService()
        await svc.record_metric("audit.active_sample", 1.0)

        await svc.persist_metrics()

        assert svc.metrics_file.exists()
        assert "audit.active_sample" in svc.metrics_file.read_text()

    def test_custom_retention_period(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        svc = MetricsService(config={"retention_period": 7200})
        assert svc.retention_period == 7200


# ===========================================================================
# MetricsService.record_metric
# ===========================================================================


@pytest.mark.asyncio
class TestRecordMetric:
    async def test_creates_new_series_on_first_record(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        svc = MetricsService()
        await svc.record_metric("my.metric", 42.0)
        assert "my.metric" in svc.metrics
        assert len(svc.metrics["my.metric"].points) == 1

    async def test_appends_to_existing_series(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        svc = MetricsService()
        await svc.record_metric("my.metric", 1.0)
        await svc.record_metric("my.metric", 2.0)
        assert len(svc.metrics["my.metric"].points) == 2

    async def test_tags_are_stored(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        svc = MetricsService()
        await svc.record_metric("req.count", 10, tags={"env": "prod"})
        assert svc.metrics["req.count"].points[-1].tags == {"env": "prod"}

    async def test_multiple_different_metrics(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        svc = MetricsService()
        await svc.record_metric("cpu", 50.0)
        await svc.record_metric("mem", 80.0)
        assert "cpu" in svc.metrics
        assert "mem" in svc.metrics

    async def test_persist_called_on_tenth_point(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        svc = MetricsService()
        # Force maxlen large enough not to lose points
        svc.metrics["x"] = MetricSeries(name="x")
        persist_calls = []
        svc._persist_metrics = AsyncMock(side_effect=lambda: persist_calls.append(1))
        for i in range(10):
            await svc.record_metric("x", float(i))
        assert len(persist_calls) == 1


# ===========================================================================
# MetricsService.get_metric_stats
# ===========================================================================


@pytest.mark.asyncio
class TestGetMetricStats:
    async def test_unknown_metric_returns_error(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        svc = MetricsService()
        result = await svc.get_metric_stats("nonexistent")
        assert "error" in result
        assert "nonexistent" in result["error"]

    async def test_returns_stats_for_known_metric(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        svc = MetricsService()
        await svc.record_metric("latency", 100.0)
        await svc.record_metric("latency", 200.0)
        result = await svc.get_metric_stats("latency")
        assert result["metric_name"] == "latency"
        assert result["stats"]["count"] == 2
        assert result["point_count"] == 2

    async def test_custom_time_window_respected(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        svc = MetricsService()
        old_ts = datetime.utcnow() - timedelta(seconds=400)
        svc.metrics["x"] = MetricSeries(name="x")
        svc.metrics["x"].add_point(99, timestamp=old_ts)
        svc.metrics["x"].add_point(1)
        result = await svc.get_metric_stats("x", time_window=300)
        # Only the recent point should be counted
        assert result["stats"]["count"] == 1


# ===========================================================================
# MetricsService.get_all_metrics
# ===========================================================================


@pytest.mark.asyncio
class TestGetAllMetrics:
    async def test_empty_metrics_returns_zero_total(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        svc = MetricsService()
        overview = await svc.get_all_metrics()
        assert overview["total_metrics"] == 0
        assert overview["metrics"] == {}

    async def test_collection_status_stopped_initially(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        svc = MetricsService()
        overview = await svc.get_all_metrics()
        assert overview["collection_status"] == "stopped"

    async def test_collection_status_running_when_started(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        svc = MetricsService()
        svc._running = True
        overview = await svc.get_all_metrics()
        assert overview["collection_status"] == "running"

    async def test_metrics_summary_included(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        svc = MetricsService()
        await svc.record_metric("cpu", 50.0)
        overview = await svc.get_all_metrics()
        assert "cpu" in overview["metrics"]
        assert overview["metrics"]["cpu"]["point_count"] == 1

    async def test_latest_timestamp_present(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        svc = MetricsService()
        await svc.record_metric("cpu", 50.0)
        overview = await svc.get_all_metrics()
        assert overview["metrics"]["cpu"]["latest_timestamp"] is not None


# ===========================================================================
# MetricsService.get_system_metrics
# ===========================================================================


@pytest.mark.asyncio
class TestGetSystemMetrics:
    async def test_returns_cpu_key(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        svc = MetricsService()
        result = await svc.get_system_metrics()
        assert "cpu" in result

    async def test_returns_memory_key(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        svc = MetricsService()
        result = await svc.get_system_metrics()
        assert "memory" in result

    async def test_returns_disk_key(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        svc = MetricsService()
        result = await svc.get_system_metrics()
        assert "disk" in result

    async def test_returns_network_key(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        svc = MetricsService()
        result = await svc.get_system_metrics()
        assert "network" in result

    async def test_records_cpu_metric(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        svc = MetricsService()
        await svc.get_system_metrics()
        assert "system.cpu_percent" in svc.metrics

    async def test_psutil_error_returns_error_dict(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        import types

        import youtube_extension.backend.services.metrics_service as _mod
        fake_psutil = types.SimpleNamespace(
            cpu_percent=MagicMock(side_effect=RuntimeError("psutil failed")),
        )
        monkeypatch.setattr(_mod, 'psutil', fake_psutil)
        svc = MetricsService()
        result = await svc.get_system_metrics()
        assert "error" in result


# ===========================================================================
# MetricsService.export_metrics
# ===========================================================================


@pytest.mark.asyncio
class TestExportMetrics:
    async def test_json_export_parses_correctly(self, tmp_path, monkeypatch):
        import json
        monkeypatch.chdir(tmp_path)
        svc = MetricsService()
        await svc.record_metric("cpu", 50.0)
        exported = await svc.export_metrics("json")
        data = json.loads(exported)
        assert "export_timestamp" in data
        assert "cpu" in data["metrics"]

    async def test_json_export_includes_all_points(self, tmp_path, monkeypatch):
        import json
        monkeypatch.chdir(tmp_path)
        svc = MetricsService()
        for v in [10, 20, 30]:
            await svc.record_metric("cpu", float(v))
        exported = await svc.export_metrics("json")
        data = json.loads(exported)
        assert len(data["metrics"]["cpu"]["points"]) == 3

    async def test_prometheus_export_format(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        svc = MetricsService()
        await svc.record_metric("cpu", 75.0)
        exported = await svc.export_metrics("prometheus")
        assert "cpu" in exported
        assert "75.0" in exported

    async def test_unsupported_format_raises(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        svc = MetricsService()
        with pytest.raises(ValueError, match="Unsupported export format"):
            await svc.export_metrics("xml")

    async def test_empty_metrics_prometheus_export(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        svc = MetricsService()
        exported = await svc.export_metrics("prometheus")
        assert exported == ""


# ===========================================================================
# MetricsService.clear_old_metrics
# ===========================================================================


@pytest.mark.asyncio
class TestClearOldMetrics:
    async def test_clears_old_points(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        svc = MetricsService()
        old_ts = datetime.utcnow() - timedelta(seconds=7200)
        svc.metrics["x"] = MetricSeries(name="x")
        svc.metrics["x"].add_point(1, timestamp=old_ts)
        svc.metrics["x"].add_point(2)  # recent
        cleared = await svc.clear_old_metrics(retention_seconds=3600)
        assert cleared == 1
        assert len(svc.metrics["x"].points) == 1

    async def test_uses_default_retention_when_none_given(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        svc = MetricsService()
        svc.retention_period = 3600
        old_ts = datetime.utcnow() - timedelta(seconds=7200)
        svc.metrics["y"] = MetricSeries(name="y")
        svc.metrics["y"].add_point(5, timestamp=old_ts)
        cleared = await svc.clear_old_metrics()
        assert cleared == 1

    async def test_no_old_points_returns_zero(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        svc = MetricsService()
        await svc.record_metric("fresh", 1.0)
        cleared = await svc.clear_old_metrics(retention_seconds=300)
        assert cleared == 0


# ===========================================================================
# MetricsService.load_persisted_metrics
# ===========================================================================


@pytest.mark.asyncio
class TestLoadPersistedMetrics:
    async def test_returns_false_when_file_missing(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        svc = MetricsService()
        # Ensure the file doesn't exist
        svc.metrics_file = tmp_path / "nonexistent.json"
        result = await svc.load_persisted_metrics()
        assert result is False

    async def test_returns_true_when_file_exists(self, tmp_path, monkeypatch):
        import json
        monkeypatch.chdir(tmp_path)
        svc = MetricsService()
        svc.metrics_file = tmp_path / "metrics.json"
        svc.metrics_file.write_text(json.dumps({"export_timestamp": "now", "metrics": {}}))
        result = await svc.load_persisted_metrics()
        assert result is True

    async def test_returns_false_on_invalid_json(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        svc = MetricsService()
        svc.metrics_file = tmp_path / "metrics.json"
        svc.metrics_file.write_text("NOT JSON {{{")
        result = await svc.load_persisted_metrics()
        assert result is False


# ===========================================================================
# MetricsService.health_check
# ===========================================================================


@pytest.mark.asyncio
class TestHealthCheck:
    async def test_returns_healthy_status(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        svc = MetricsService()
        health = await svc.health_check()
        assert health["service"] == "metrics_service"
        assert health["status"] in ("healthy", "degraded")

    async def test_health_check_reports_collection_running_false(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        svc = MetricsService()
        health = await svc.health_check()
        assert health["metrics"]["collection_running"] is False

    async def test_recording_works_true_when_no_error(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        svc = MetricsService()
        health = await svc.health_check()
        assert health["metrics"]["recording_works"] is True

    async def test_system_collection_works_true_by_default(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        svc = MetricsService()
        health = await svc.health_check()
        assert health["metrics"]["system_collection_works"] is True


# ===========================================================================
# MetricsService.start_collection / stop_collection
# ===========================================================================


@pytest.mark.asyncio
class TestStartStopCollection:
    async def test_start_sets_running_true(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        svc = MetricsService()
        # Patch background task to avoid real collection loop
        with patch.object(svc, "_background_collection", new_callable=AsyncMock):
            await svc.start_collection()
            assert svc._running is True
            await svc.stop_collection()

    async def test_start_is_idempotent(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        svc = MetricsService()
        with patch.object(svc, "_background_collection", new_callable=AsyncMock):
            await svc.start_collection()
            task1 = svc._collection_task
            await svc.start_collection()  # second call should be a no-op
            assert svc._collection_task is task1
            await svc.stop_collection()

    async def test_stop_sets_running_false(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        svc = MetricsService()
        with patch.object(svc, "_background_collection", new_callable=AsyncMock):
            await svc.start_collection()
            await svc.stop_collection()
            assert svc._running is False


# ===========================================================================
# MetricsService — disk I/O must not block the event loop
# ===========================================================================


class TestDiskIoDoesNotBlockEventLoop:
    """`record_metric` persists every 10th point while serving requests.

    A synchronous ``open()``/``write()`` there stalls every other task on the
    loop for the whole disk write. These tests measure loop responsiveness
    directly: a 5 ms heartbeat must get at least one tick while a deliberately
    slow file operation is in flight.
    """

    async def _count_heartbeats_during(self, coro):
        ticks = 0
        stop = False

        async def heartbeat():
            nonlocal ticks
            while not stop:
                await asyncio.sleep(0.005)
                ticks += 1

        beat = asyncio.create_task(heartbeat())
        await asyncio.sleep(0)  # let the heartbeat reach its first await first
        try:
            result = await coro
        finally:
            stop = True
            beat.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await beat
        return result, ticks

    @staticmethod
    def _slow_write(_path, _contents):
        time.sleep(0.15)

    @staticmethod
    def _slow_read(_path):
        time.sleep(0.15)
        return {}

    async def test_persist_metrics_does_not_block_the_loop(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        svc = MetricsService()
        await svc.record_metric("latency", 1.0)

        with patch.object(
            MetricsService, "_write_text_file", staticmethod(self._slow_write)
        ):
            _, ticks = await self._count_heartbeats_during(svc._persist_metrics())

        assert ticks > 0, (
            "event loop was blocked for the whole 0.15s metrics write: "
            f"the 0.005s heartbeat ticked {ticks} times"
        )

    async def test_load_persisted_metrics_does_not_block_the_loop(
        self, tmp_path, monkeypatch
    ):
        monkeypatch.chdir(tmp_path)
        svc = MetricsService()
        svc.metrics_file.write_text("{}")

        with patch.object(
            MetricsService, "_read_json_file", staticmethod(self._slow_read)
        ):
            ok, ticks = await self._count_heartbeats_during(
                svc.load_persisted_metrics()
            )

        assert ok is True
        assert ticks > 0, (
            "event loop was blocked for the whole 0.15s metrics read: "
            f"the 0.005s heartbeat ticked {ticks} times"
        )

    async def test_record_metric_hot_path_does_not_block_the_loop(
        self, tmp_path, monkeypatch
    ):
        """The real production trigger: every 10th point persists inline."""
        monkeypatch.chdir(tmp_path)
        svc = MetricsService()
        for _ in range(9):
            await svc.record_metric("latency", 1.0)

        with patch.object(
            MetricsService, "_write_text_file", staticmethod(self._slow_write)
        ):
            # the 10th point crosses the `% 10 == 0` boundary and persists
            _, ticks = await self._count_heartbeats_during(
                svc.record_metric("latency", 1.0)
            )

        assert ticks > 0, (
            "record_metric blocked the loop for the whole 0.15s persist "
            f"({ticks} heartbeats)"
        )

    # --- preserved-behaviour guards (pass under both old and new code) ---

    async def test_persist_writes_exported_payload_to_disk(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        svc = MetricsService()
        await svc.record_metric("latency", 42.0)

        await svc._persist_metrics()

        written = json.loads(svc.metrics_file.read_text())
        assert "latency" in written["metrics"]
        assert written["metrics"]["latency"]["points"][0]["value"] == 42.0

    async def test_persist_swallows_write_errors(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        svc = MetricsService()
        await svc.record_metric("latency", 1.0)

        def _boom(_path, _contents):
            raise OSError("disk full")

        with patch.object(MetricsService, "_write_text_file", staticmethod(_boom)):
            await svc._persist_metrics()  # must not raise

    async def test_load_returns_false_when_file_missing(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        svc = MetricsService()
        svc.metrics_file.unlink(missing_ok=True)

        assert await svc.load_persisted_metrics() is False

    async def test_load_returns_false_on_corrupt_json(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        svc = MetricsService()
        svc.metrics_file.write_text("{not json")

        assert await svc.load_persisted_metrics() is False
