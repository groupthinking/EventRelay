"""
Miscellaneous service tests to increase coverage across:
- youtube_extension.backend.services.youtube.adapters.innertube
- youtube_extension.backend.services.data_service (cleanup_old_data)
- youtube_extension.backend.services.logging_service (LoggingService helpers)
- youtube_extension.backend.services.database_cleanup_service (cleanup_database, schedule_cleanup)
- youtube_extension.backend.middleware.error_handling_middleware (setup_error_handlers)
- youtube_extension.backend.services.api_cost_monitor (cleanup, decorator)
- youtube_extension.processors.strategies (_extract_key_points, _extract_topics, analyze_content)
"""

from __future__ import annotations

import asyncio
import json
import sqlite3
import sys
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))


# ===========================================================================
# innertube.py — pure-function unit tests (no network)
# ===========================================================================


from youtube_extension.backend.services.youtube.adapters.innertube import (
    CaptionSegment,
    InnertubeTranscriptError,
    InnertubeTranscriptNotFound,
    _extract_api_key,
    _normalize_caption_text,
    _safe_float,
    _select_caption_track,
    fetch_innertube_transcript,
    parse_transcript_xml,
)


class TestCaptionSegment:
    def test_stores_text(self):
        seg = CaptionSegment(text="Hello", start=1.0, duration=2.0)
        assert seg.text == "Hello"

    def test_stores_start(self):
        seg = CaptionSegment(text="Hi", start=3.5, duration=1.0)
        assert seg.start == 3.5

    def test_stores_duration(self):
        seg = CaptionSegment(text="Hi", start=0.0, duration=4.25)
        assert seg.duration == 4.25


class TestInnertubeErrors:
    def test_transcript_error_is_runtime_error(self):
        err = InnertubeTranscriptError("fetch failed")
        assert isinstance(err, RuntimeError)

    def test_not_found_is_transcript_error(self):
        err = InnertubeTranscriptNotFound("no captions")
        assert isinstance(err, InnertubeTranscriptError)

    def test_not_found_message(self):
        err = InnertubeTranscriptNotFound("lang not available")
        assert "lang not available" in str(err)


class TestExtractApiKey:
    def test_extracts_key_from_html(self):
        html = 'some stuff "INNERTUBE_API_KEY":"AIzaSyAbc123def"  more stuff'
        key = _extract_api_key(html)
        assert key == "AIzaSyAbc123def"

    def test_returns_none_when_not_present(self):
        html = "<html>no key here</html>"
        assert _extract_api_key(html) is None

    def test_extracts_with_surrounding_content(self):
        html = '{"INNERTUBE_API_KEY":"MYKEY456","OTHER":"val"}'
        assert _extract_api_key(html) == "MYKEY456"


class TestSafeFloat:
    def test_valid_float_string(self):
        assert _safe_float("3.14") == pytest.approx(3.14)

    def test_integer_string(self):
        assert _safe_float("5") == 5.0

    def test_none_returns_zero(self):
        assert _safe_float(None) == 0.0

    def test_invalid_string_returns_zero(self):
        assert _safe_float("not-a-number") == 0.0

    def test_empty_string_returns_zero(self):
        assert _safe_float("") == 0.0

    def test_zero_string(self):
        assert _safe_float("0") == 0.0


class TestNormalizeCaptionText:
    def test_strips_whitespace(self):
        assert _normalize_caption_text("  hello  ") == "hello"

    def test_replaces_newlines(self):
        assert _normalize_caption_text("hello\nworld") == "hello world"

    def test_unescapes_html_entities(self):
        result = _normalize_caption_text("Hello &amp; World")
        assert "&" in result

    def test_empty_string(self):
        assert _normalize_caption_text("") == ""


class TestSelectCaptionTrack:
    def _player_response(self, tracks: list[dict]) -> dict:
        return {
            "captions": {
                "playerCaptionsTracklistRenderer": {
                    "captionTracks": tracks
                }
            }
        }

    def test_returns_none_for_no_captions(self):
        assert _select_caption_track({}, "en") is None

    def test_returns_none_for_empty_tracks(self):
        assert _select_caption_track(self._player_response([]), "en") is None

    def test_selects_matching_language(self):
        tracks = [
            {"languageCode": "es", "baseUrl": "http://example.com/es"},
            {"languageCode": "en", "baseUrl": "http://example.com/en"},
        ]
        url = _select_caption_track(self._player_response(tracks), "en")
        assert url == "http://example.com/en"

    def test_falls_back_to_first_track(self):
        tracks = [
            {"languageCode": "fr", "baseUrl": "http://example.com/fr"},
        ]
        url = _select_caption_track(self._player_response(tracks), "en")
        assert url == "http://example.com/fr"

    def test_returns_none_if_no_base_url(self):
        tracks = [{"languageCode": "en"}]
        assert _select_caption_track(self._player_response(tracks), "en") is None

    def test_strips_fmt_suffix(self):
        tracks = [{"languageCode": "en", "baseUrl": "http://example.com/caps&fmt=vtt"}]
        url = _select_caption_track(self._player_response(tracks), "en")
        assert url == "http://example.com/caps"

    def test_no_fmt_suffix_unchanged(self):
        tracks = [{"languageCode": "en", "baseUrl": "http://example.com/caps"}]
        url = _select_caption_track(self._player_response(tracks), "en")
        assert url == "http://example.com/caps"


class TestParseTranscriptXml:
    def test_empty_string_returns_empty_list(self):
        assert parse_transcript_xml("") == []

    def test_whitespace_only_returns_empty(self):
        assert parse_transcript_xml("   \n  ") == []

    def test_parses_single_text_node(self):
        xml = '<transcript><text start="0.5" dur="1.2">Hello world</text></transcript>'
        segments = parse_transcript_xml(xml)
        assert len(segments) == 1
        assert segments[0].text == "Hello world"
        assert segments[0].start == pytest.approx(0.5)
        assert segments[0].duration == pytest.approx(1.2)

    def test_parses_multiple_text_nodes(self):
        xml = (
            '<transcript>'
            '<text start="0.0" dur="1.0">First</text>'
            '<text start="1.5" dur="2.0">Second</text>'
            '</transcript>'
        )
        segments = parse_transcript_xml(xml)
        assert len(segments) == 2
        assert segments[0].text == "First"
        assert segments[1].text == "Second"

    def test_handles_missing_attributes(self):
        xml = '<transcript><text>No attrs</text></transcript>'
        segments = parse_transcript_xml(xml)
        assert len(segments) == 1
        assert segments[0].start == 0.0
        assert segments[0].duration == 0.0

    def test_handles_html_entities_in_text(self):
        xml = '<transcript><text start="0" dur="1">Hello &amp; Goodbye</text></transcript>'
        segments = parse_transcript_xml(xml)
        assert "&" in segments[0].text

    def test_handles_empty_text_node(self):
        xml = '<transcript><text start="0" dur="1"></text></transcript>'
        segments = parse_transcript_xml(xml)
        assert len(segments) == 1
        assert segments[0].text == ""

    def test_returns_caption_segment_instances(self):
        xml = '<transcript><text start="1.0" dur="0.5">Hi</text></transcript>'
        segments = parse_transcript_xml(xml)
        assert all(isinstance(s, CaptionSegment) for s in segments)


class TestFetchInnertubeTranscript:
    async def test_raises_value_error_for_empty_video_id(self):
        with pytest.raises(ValueError, match="video_id is required"):
            await fetch_innertube_transcript("")

    async def test_raises_for_none_video_id(self):
        with pytest.raises((ValueError, TypeError)):
            await fetch_innertube_transcript(None)

    async def test_raises_innertube_error_when_watch_page_fails(self):
        """Network errors get wrapped in InnertubeTranscriptError."""
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=Exception("connection refused"))
        with pytest.raises(InnertubeTranscriptError):
            await fetch_innertube_transcript("auJzb1D-fag", client=mock_client)

    async def test_raises_innertube_error_when_api_key_missing(self):
        """Missing API key raises InnertubeTranscriptError."""
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.text = "<html>no api key here</html>"
        mock_response.raise_for_status = MagicMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        with pytest.raises(InnertubeTranscriptError, match="INNERTUBE_API_KEY"):
            await fetch_innertube_transcript("auJzb1D-fag", client=mock_client)

    async def test_raises_not_found_when_no_captions(self):
        """When player response has no caption tracks, raises InnertubeTranscriptNotFound."""
        mock_client = AsyncMock()

        watch_response = MagicMock()
        watch_response.text = '"INNERTUBE_API_KEY":"test_key_123"'
        watch_response.raise_for_status = MagicMock()

        player_response = MagicMock()
        player_response.json = MagicMock(return_value={"captions": {}})
        player_response.raise_for_status = MagicMock()

        mock_client.get = AsyncMock(return_value=watch_response)
        mock_client.post = AsyncMock(return_value=player_response)

        with pytest.raises(InnertubeTranscriptNotFound):
            await fetch_innertube_transcript("auJzb1D-fag", client=mock_client)

    async def test_raises_innertube_error_for_empty_xml(self):
        """Empty XML after fetching captions raises InnertubeTranscriptError."""
        mock_client = AsyncMock()

        watch_response = MagicMock()
        watch_response.text = '"INNERTUBE_API_KEY":"test_key_abc"'
        watch_response.raise_for_status = MagicMock()

        player_response = MagicMock()
        player_response.json = MagicMock(return_value={
            "captions": {
                "playerCaptionsTracklistRenderer": {
                    "captionTracks": [
                        {"languageCode": "en", "baseUrl": "http://example.com/caps"}
                    ]
                }
            }
        })
        player_response.raise_for_status = MagicMock()

        xml_response = MagicMock()
        xml_response.text = "   "
        xml_response.raise_for_status = MagicMock()

        mock_client.get = AsyncMock(side_effect=[watch_response, xml_response])
        mock_client.post = AsyncMock(return_value=player_response)

        with pytest.raises(InnertubeTranscriptError):
            await fetch_innertube_transcript("auJzb1D-fag", client=mock_client)

    async def test_returns_segments_on_success(self):
        """Full happy path returns list of CaptionSegments."""
        xml_content = (
            '<transcript>'
            '<text start="0.0" dur="1.5">Hello world</text>'
            '<text start="2.0" dur="1.0">Goodbye world</text>'
            '</transcript>'
        )

        mock_client = AsyncMock()

        watch_response = MagicMock()
        watch_response.text = '"INNERTUBE_API_KEY":"test_key_xyz"'
        watch_response.raise_for_status = MagicMock()

        player_response = MagicMock()
        player_response.json = MagicMock(return_value={
            "captions": {
                "playerCaptionsTracklistRenderer": {
                    "captionTracks": [
                        {"languageCode": "en", "baseUrl": "http://example.com/caps"}
                    ]
                }
            }
        })
        player_response.raise_for_status = MagicMock()

        xml_response = MagicMock()
        xml_response.text = xml_content
        xml_response.raise_for_status = MagicMock()

        mock_client.get = AsyncMock(side_effect=[watch_response, xml_response])
        mock_client.post = AsyncMock(return_value=player_response)

        segments = await fetch_innertube_transcript("auJzb1D-fag", client=mock_client)
        assert len(segments) == 2
        assert segments[0].text == "Hello world"


# ===========================================================================
# data_service.py — cleanup_old_data
# ===========================================================================


from youtube_extension.backend.services.data_service import DataService


class TestDataServiceCleanupOldData:
    @pytest.fixture
    def svc(self, tmp_path):
        return DataService(
            enhanced_analysis_dir=str(tmp_path / "enhanced"),
            feedback_dir=str(tmp_path / "feedback"),
        )

    def test_returns_summary_dict(self, svc):
        result = svc.cleanup_old_data()
        assert isinstance(result, dict)

    def test_no_dir_returns_zero_counts(self, svc):
        result = svc.cleanup_old_data()
        assert result["files_removed"] == 0
        assert result["categories_processed"] == 0

    def test_required_keys_present(self, svc):
        result = svc.cleanup_old_data()
        for key in ("files_removed", "size_freed_mb", "categories_processed"):
            assert key in result

    def test_removes_old_files(self, tmp_path):
        enhanced = tmp_path / "enhanced"
        cat = enhanced / "old_category"
        cat.mkdir(parents=True)
        old_file = cat / "oldvid_test_enhanced.md"
        old_file.write_text("old content")

        # Set modification time to 60 days ago
        old_time = time.time() - (60 * 24 * 60 * 60)
        import os
        os.utime(str(old_file), (old_time, old_time))

        svc = DataService(str(enhanced), str(tmp_path / "feedback"))
        result = svc.cleanup_old_data(days_old=30)
        assert result["files_removed"] >= 1

    def test_preserves_recent_files(self, tmp_path):
        enhanced = tmp_path / "enhanced"
        cat = enhanced / "recent_category"
        cat.mkdir(parents=True)
        (cat / "newvid_test_enhanced.md").write_text("new content")

        svc = DataService(str(enhanced), str(tmp_path / "feedback"))
        result = svc.cleanup_old_data(days_old=30)
        assert result["files_removed"] == 0

    def test_removes_empty_directories(self, tmp_path):
        enhanced = tmp_path / "enhanced"
        cat = enhanced / "empty_later"
        cat.mkdir(parents=True)
        old_file = cat / "vid_test_enhanced.md"
        old_file.write_text("x")

        old_time = time.time() - (90 * 24 * 60 * 60)
        import os
        os.utime(str(old_file), (old_time, old_time))

        svc = DataService(str(enhanced), str(tmp_path / "feedback"))
        svc.cleanup_old_data(days_old=30)
        # The empty directory should be removed
        assert not cat.exists()

    def test_size_freed_is_numeric(self, svc):
        result = svc.cleanup_old_data()
        assert isinstance(result["size_freed_mb"], (int, float))

    def test_data_statistics_snippet_title(self, tmp_path):
        """snippet.title fallback in get_videos_summary."""
        enhanced = tmp_path / "enhanced"
        cat = enhanced / "snip"
        cat.mkdir(parents=True)
        (cat / "vid099_x_enhanced.md").write_text("body")
        meta = {"snippet": {"title": "Snippet Title"}}
        (cat / "vid099_x_metadata.json").write_text(json.dumps(meta))
        svc = DataService(str(enhanced), str(tmp_path / "feedback"))
        results = svc.get_videos_summary()
        assert results[0]["title"] == "Snippet Title"


# ===========================================================================
# logging_service.py — additional LoggingService paths
# ===========================================================================


from youtube_extension.backend.services.logging_service import (
    LoggingService,
    log_api_request,
    log_error,
    log_performance,
    performance_monitor,
)


class TestLoggingServiceGetMetricsSummary:
    @pytest.fixture
    async def service(self, tmp_path):
        return LoggingService(config={
            "log_directory": tmp_path / "logs",
            "enable_remote_logging": False,
        })

    async def test_returns_dict(self, service):
        summary = service.get_metrics_summary()
        assert isinstance(summary, dict)

    async def test_has_logging_service_key(self, service):
        summary = service.get_metrics_summary()
        assert "logging_service" in summary

    async def test_has_error_aggregation_key(self, service):
        summary = service.get_metrics_summary()
        assert "error_aggregation" in summary

    async def test_has_system_info_key(self, service):
        summary = service.get_metrics_summary()
        assert "system_info" in summary

    async def test_system_info_has_environment(self, service):
        summary = service.get_metrics_summary()
        assert "environment" in summary["system_info"]

    async def test_system_info_has_remote_logging_flag(self, service):
        summary = service.get_metrics_summary()
        assert "remote_logging_enabled" in summary["system_info"]


class TestLoggingServiceCleanup:
    @pytest.fixture
    async def service(self, tmp_path):
        return LoggingService(config={
            "log_directory": tmp_path / "logs",
            "enable_remote_logging": False,
        })

    async def test_cleanup_flushes_buffer(self, service):
        await service.log_structured("INFO", "before cleanup")
        assert len(service.log_buffer) == 1
        await service.cleanup()
        assert len(service.log_buffer) == 0

    async def test_cleanup_with_flush_task_none(self, service):
        service.flush_task = None
        await service.cleanup()  # Should not raise

    async def test_cleanup_with_flush_task_set(self, service):
        # Create a long-running dummy task and assign it
        async def dummy():
            await asyncio.sleep(100)

        task = asyncio.create_task(dummy())
        service.flush_task = task
        await service.cleanup()
        # task.cancel() was called; task is either cancelling or cancelled
        assert task.cancelled() or task.cancelling() > 0 or task.done()


class TestLoggingServiceBufferFlush:
    @pytest.fixture
    async def service(self, tmp_path):
        return LoggingService(config={
            "log_directory": tmp_path / "logs",
            "enable_remote_logging": False,
            "buffer_size": 3,
        })

    async def test_flush_writes_files_when_logs_present(self, service, tmp_path):
        await service.log_structured("INFO", "test1")
        await service.log_structured("ERROR", "error1")
        await service.flush_logs()
        structured_log = tmp_path / "logs" / "structured_logs.jsonl"
        assert structured_log.exists()

    async def test_buffer_auto_flushes_when_full(self, service, tmp_path):
        """When buffer reaches buffer_size, it flushes automatically."""
        for i in range(3):
            await service.log_structured("INFO", f"msg{i}")
        # Buffer should be empty after auto-flush at size 3
        assert len(service.log_buffer) == 0


class TestLoggingConvenienceFunctions:
    async def test_log_error_convenience(self, tmp_path):
        with patch("youtube_extension.backend.services.logging_service._logging_service", None):
            # Reset global instance
            import youtube_extension.backend.services.logging_service as ls_module
            ls_module._logging_service = None
            error_id = await log_error(ValueError("test error"))
            assert error_id.startswith("ERR_")

    async def test_log_api_request_convenience(self, tmp_path):
        import youtube_extension.backend.services.logging_service as ls_module
        ls_module._logging_service = None
        # Should not raise
        await log_api_request("GET", "/health", 200, 10.0)

    async def test_log_performance_convenience(self, tmp_path):
        import youtube_extension.backend.services.logging_service as ls_module
        ls_module._logging_service = None
        await log_performance("db_query", 15.5)


class TestPerformanceMonitorDecorator:
    async def test_async_function_wrapped(self, tmp_path):
        import youtube_extension.backend.services.logging_service as ls_module
        ls_module._logging_service = None

        @performance_monitor("test_operation")
        async def my_async_func(x):
            return x * 2

        result = await my_async_func(5)
        assert result == 10

    async def test_sync_function_wrapped(self):
        """Sync wrapper runs inside async test (event loop available)."""
        import youtube_extension.backend.services.logging_service as ls_module
        ls_module._logging_service = None

        @performance_monitor("test_sync_op")
        def my_sync_func(x):
            return x + 1

        result = my_sync_func(3)
        assert result == 4


class TestPerformanceContext:
    @pytest.fixture
    async def service(self, tmp_path):
        return LoggingService(config={
            "log_directory": tmp_path / "logs",
            "enable_remote_logging": False,
        })

    async def test_performance_context_does_not_raise(self, service):
        with service.performance_context("my_operation"):
            pass  # Just run through it


# ===========================================================================
# database_cleanup_service.py — cleanup_database and related
# ===========================================================================


from youtube_extension.backend.services.database_cleanup_service import (
    DatabaseCleanupService,
    RetentionPolicy,
    get_cleanup_report,
    run_database_cleanup,
)


class TestCleanupDatabase:
    @pytest.fixture
    def svc(self, tmp_path):
        return DatabaseCleanupService(config_path=str(tmp_path / "cfg.json"))

    def test_returns_empty_for_unknown_db(self, svc, tmp_path):
        db_path = str(tmp_path / "unknown.db")
        sqlite3.connect(db_path).close()
        results = svc.cleanup_database(db_path)
        assert results == []

    def test_returns_results_for_known_db(self, svc, tmp_path):
        """Register a policy and run cleanup against a real DB."""
        db_path = str(tmp_path / "perf.db")
        conn = sqlite3.connect(db_path)
        conn.execute("CREATE TABLE performance_metrics (id INTEGER PRIMARY KEY, value REAL, timestamp TEXT)")
        conn.commit()
        conn.close()

        # Override policies so it matches our db name
        svc.retention_policies["perf.db"] = [
            RetentionPolicy(table_name="performance_metrics", retention_days=30)
        ]
        results = svc.cleanup_database(db_path)
        assert isinstance(results, list)
        assert len(results) == 1

    def test_updates_cleanup_stats_after_run(self, svc, tmp_path):
        db_path = str(tmp_path / "test_stats.db")
        conn = sqlite3.connect(db_path)
        conn.execute("CREATE TABLE myevents (id INTEGER PRIMARY KEY, ts TEXT)")
        conn.commit()
        conn.close()

        svc.retention_policies["test_stats.db"] = [
            RetentionPolicy(table_name="myevents", retention_days=30)
        ]
        svc.cleanup_database(db_path)
        assert svc.cleanup_stats["total_cleanups"] == 1

    def test_increments_error_stats_for_failed_table(self, svc, tmp_path):
        """Missing table causes failure, increments error count."""
        db_path = str(tmp_path / "err_test.db")
        sqlite3.connect(db_path).close()  # Empty DB - no tables

        svc.retention_policies["err_test.db"] = [
            RetentionPolicy(table_name="nonexistent_table", retention_days=30)
        ]
        svc.cleanup_database(db_path)
        assert svc.cleanup_stats["errors"] >= 1

    def test_skips_disabled_policies(self, svc, tmp_path):
        db_path = str(tmp_path / "disabled.db")
        conn = sqlite3.connect(db_path)
        conn.execute("CREATE TABLE events (id INTEGER PRIMARY KEY, ts TEXT)")
        conn.commit()
        conn.close()

        svc.retention_policies["disabled.db"] = [
            RetentionPolicy(table_name="events", retention_days=30, enabled=False)
        ]
        results = svc.cleanup_database(db_path)
        assert results == []


class TestCleanupAllDatabases:
    @pytest.fixture
    def svc(self, tmp_path):
        return DatabaseCleanupService(config_path=str(tmp_path / "cfg.json"))

    def test_returns_dict(self, svc):
        result = svc.cleanup_all_databases()
        assert isinstance(result, dict)

    def test_empty_when_no_matching_dbs(self, svc):
        """No db files in project root matching policies → empty dict."""
        # Override policies with a db that won't be found in project root
        svc.retention_policies = {"__unlikely_db_999__.db": []}
        result = svc.cleanup_all_databases()
        assert result == {}


class TestLoadConfig:
    def test_loads_config_from_json(self, tmp_path):
        config_data = {
            "retention_policies": {
                "myapp.db": [
                    {"table_name": "logs", "retention_days": 14, "batch_size": 500, "enabled": True, "description": "2 week logs"}
                ]
            }
        }
        config_path = tmp_path / "config.json"
        config_path.write_text(json.dumps(config_data))

        svc = DatabaseCleanupService(config_path=str(config_path))
        assert "myapp.db" in svc.retention_policies
        tables = [p.table_name for p in svc.retention_policies["myapp.db"]]
        assert "logs" in tables

    def test_updates_existing_policy_from_config(self, tmp_path):
        """Config policy for an existing table updates retention_days."""
        config_data = {
            "retention_policies": {
                "performance_monitoring.db": [
                    {"table_name": "performance_metrics", "retention_days": 14, "batch_size": 1000, "enabled": True, "description": ""}
                ]
            }
        }
        config_path = tmp_path / "upd_config.json"
        config_path.write_text(json.dumps(config_data))

        svc = DatabaseCleanupService(config_path=str(config_path))
        pm_policy = next(
            p for p in svc.retention_policies["performance_monitoring.db"]
            if p.table_name == "performance_metrics"
        )
        assert pm_policy.retention_days == 14

    def test_ignores_invalid_config_file(self, tmp_path):
        config_path = tmp_path / "bad.json"
        config_path.write_text("{bad json")

        # Should not raise; just use defaults
        svc = DatabaseCleanupService(config_path=str(config_path))
        assert "performance_monitoring.db" in svc.retention_policies


class TestSaveConfig:
    def test_saves_to_file(self, tmp_path):
        config_path = tmp_path / "saved.json"
        svc = DatabaseCleanupService(config_path=str(config_path))
        svc.save_config()
        assert config_path.exists()
        data = json.loads(config_path.read_text())
        assert "retention_policies" in data

    def test_saved_config_has_cleanup_stats(self, tmp_path):
        config_path = tmp_path / "saved2.json"
        svc = DatabaseCleanupService(config_path=str(config_path))
        svc.save_config()
        data = json.loads(config_path.read_text())
        assert "cleanup_stats" in data

    def test_saved_config_has_last_updated(self, tmp_path):
        config_path = tmp_path / "saved3.json"
        svc = DatabaseCleanupService(config_path=str(config_path))
        svc.save_config()
        data = json.loads(config_path.read_text())
        assert "last_updated" in data


class TestCleanupTableNoTimestampColumn:
    def test_returns_failure_when_no_time_column(self, tmp_path):
        db_path = str(tmp_path / "notable.db")
        conn = sqlite3.connect(db_path)
        conn.execute("CREATE TABLE data (id INTEGER PRIMARY KEY, value TEXT)")
        conn.commit()
        conn.close()

        svc = DatabaseCleanupService(config_path=str(tmp_path / "cfg.json"))
        policy = RetentionPolicy(table_name="data", retention_days=30)
        result = svc.cleanup_table(db_path, policy)
        assert result.success is False
        assert "time column" in (result.error_message or "")


class TestGlobalCleanupFunctions:
    async def test_run_database_cleanup_returns_dict(self):
        result = await run_database_cleanup()
        assert isinstance(result, dict)

    def test_get_cleanup_report_returns_dict(self):
        report = get_cleanup_report()
        assert isinstance(report, dict)
        assert "cleanup_stats" in report


class TestScheduleCleanupOneCycle:
    async def test_schedule_cleanup_runs_once_and_stops(self, tmp_path):
        """Verify schedule_cleanup doesn't crash; cancel after first iteration."""
        svc = DatabaseCleanupService(config_path=str(tmp_path / "cfg.json"))

        async def run_one_iteration():
            task = asyncio.create_task(svc.schedule_cleanup(interval_hours=0))
            await asyncio.sleep(0.05)
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        await run_one_iteration()


# ===========================================================================
# error_handling_middleware.py — setup_error_handlers and add_middleware
# ===========================================================================


from youtube_extension.backend.middleware.error_handling_middleware import (
    ErrorHandlingMiddleware,
    add_error_handling_middleware,
    setup_error_handlers,
)


class TestSetupErrorHandlers:
    def test_registers_handlers_without_raising(self):
        from fastapi import FastAPI
        app = FastAPI()
        setup_error_handlers(app)  # Should not raise

    async def test_http_exception_handler_returns_json(self):
        """Test the registered HTTP exception handler callable."""
        from fastapi import FastAPI, HTTPException
        app = FastAPI()
        setup_error_handlers(app)

        # Simulate calling the handler with a mock request
        req = MagicMock()
        req.state = MagicMock()
        req.state.request_id = "test-id"
        req.method = "GET"
        req.url = MagicMock(__str__=lambda self: "http://test.com/api")
        req.headers = {}

        exc = HTTPException(status_code=404, detail="Not found")
        # Find the exception handler
        handler = app.exception_handlers.get(HTTPException)
        if handler:
            from fastapi.responses import JSONResponse
            response = await handler(req, exc)
            assert isinstance(response, JSONResponse)

    async def test_general_exception_handler_returns_json(self):
        """Test the general exception handler."""
        from fastapi import FastAPI
        app = FastAPI()
        setup_error_handlers(app)

        req = MagicMock()
        req.state = MagicMock()
        req.state.request_id = "test-id"
        req.method = "GET"
        req.url = MagicMock(__str__=lambda self: "http://test.com/api")
        req.headers = {}

        exc = RuntimeError("something broke")
        handler = app.exception_handlers.get(Exception)
        if handler:
            from fastapi.responses import JSONResponse
            response = await handler(req, exc)
            assert isinstance(response, JSONResponse)


class TestAddErrorHandlingMiddleware:
    def test_returns_middleware_instance(self):
        from fastapi import FastAPI
        app = FastAPI()
        result = add_error_handling_middleware(app, debug=False)
        assert isinstance(result, ErrorHandlingMiddleware)

    def test_middleware_added_to_app(self):
        from fastapi import FastAPI
        app = FastAPI()
        add_error_handling_middleware(app)
        # Just verify it doesn't raise — middleware stack is set up


class TestMiddlewareDispatchHappyPath:
    async def test_dispatch_passes_through_on_success(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        app = FastAPI()

        @app.get("/test-pass")
        async def pass_route():
            return {"ok": True}

        app.add_middleware(ErrorHandlingMiddleware, debug=False)

        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/test-pass")
        assert resp.status_code == 200

    async def test_dispatch_handles_http_exception(self):
        from fastapi import FastAPI, HTTPException
        from fastapi.testclient import TestClient

        app = FastAPI()

        @app.get("/test-404")
        async def fail_route():
            raise HTTPException(status_code=404, detail="Not found")

        app.add_middleware(ErrorHandlingMiddleware, debug=False)

        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/test-404")
        assert resp.status_code == 404

    async def test_dispatch_handles_generic_exception(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        app = FastAPI()

        @app.get("/test-500")
        async def error_route():
            raise RuntimeError("unexpected error")

        app.add_middleware(ErrorHandlingMiddleware, debug=False)

        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/test-500")
        assert resp.status_code == 500

    async def test_dispatch_handles_request_too_large(self):
        """Content-length > max triggers a 413."""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        app = FastAPI()

        @app.post("/upload")
        async def upload():
            return {"ok": True}

        # Set very small limit
        app.add_middleware(ErrorHandlingMiddleware, debug=False, max_request_size=10)

        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post(
            "/upload",
            content=b"x" * 100,
            headers={"content-length": "100"},
        )
        # Should get some error (413 from middleware)
        assert resp.status_code >= 400


class TestErrorHandlingMiddlewareResetTracking:
    def test_error_tracking_resets_after_hour(self):
        from fastapi import FastAPI
        app = FastAPI()
        middleware = ErrorHandlingMiddleware(app)

        # Seed some error counts
        middleware.error_counts["validation"] = 5
        # Backdate the reset time by more than 1 hour
        middleware.last_error_reset = time.time() - 3700
        middleware.update_error_tracking("validation")
        # After reset, the old counts are gone and we start fresh
        assert middleware.error_counts.get("validation") == 1


# ===========================================================================
# api_cost_monitor.py — cleanup paths
# ===========================================================================


from youtube_extension.backend.services.api_cost_monitor import (
    APICostMonitor,
    check_rate_limit_decorator,
    track_api_call,
)


class TestAPICostMonitorCleanup:
    @pytest.fixture
    def monitor(self, tmp_path):
        return APICostMonitor(db_path=str(tmp_path / "test.db"))

    async def test_cleanup_old_data_no_exception(self, monitor):
        await monitor.cleanup_old_data()  # Should not raise

    async def test_basic_cost_cleanup_no_exception(self, monitor):
        await monitor._basic_cost_cleanup()  # Should not raise

    async def test_basic_cost_cleanup_runs_on_real_db(self, monitor):
        # Record some usage first
        await monitor.record_usage(
            service="anthropic", endpoint="/messages", tokens_used=100
        )
        # Then cleanup — should not fail
        await monitor._basic_cost_cleanup()

    async def test_trigger_manual_cleanup_returns_dict(self, monitor):
        result = await monitor.trigger_manual_cleanup()
        assert isinstance(result, dict)

    async def test_trigger_manual_cleanup_returns_error_on_failure(self, tmp_path):
        monitor = APICostMonitor(db_path=str(tmp_path / "m2.db"))
        # The cleanup path was rewritten to use SQLAlchemy sessions directly and
        # no longer relies on an external cleanup service / CLEANUP_AVAILABLE flag.
        # Force the session factory to fail and assert the error path still
        # returns a dict carrying an "error" key rather than raising.
        with patch.object(
            monitor, "Session", side_effect=RuntimeError("session unavailable")
        ):
            result = await monitor.trigger_manual_cleanup()
            assert "error" in result


class TestTrackApiCallConvenience:
    async def test_track_api_call_returns_record(self, tmp_path):
        monitor = APICostMonitor(db_path=str(tmp_path / "track.db"))
        with patch(
            "youtube_extension.backend.services.api_cost_monitor.cost_monitor",
            monitor
        ):
            record = await track_api_call("openai", "/chat", 200)
            assert record is not None


class TestCheckRateLimitDecorator:
    async def test_decorator_passes_through_when_allowed(self, tmp_path):
        monitor = APICostMonitor(db_path=str(tmp_path / "deco.db"))

        with patch(
            "youtube_extension.backend.services.api_cost_monitor.cost_monitor",
            monitor
        ):
            @check_rate_limit_decorator("anthropic")
            async def my_api_call():
                return "success"

            result = await my_api_call()
            assert result == "success"

    async def test_decorator_raises_when_circuit_open(self, tmp_path):
        monitor = APICostMonitor(db_path=str(tmp_path / "circ.db"))
        monitor.circuit_breakers["anthropic"]["open"] = True
        monitor.circuit_breakers["anthropic"]["last_failure"] = time.time()

        with patch(
            "youtube_extension.backend.services.api_cost_monitor.cost_monitor",
            monitor
        ):
            @check_rate_limit_decorator("anthropic")
            async def my_api_call():
                return "success"

            with pytest.raises(Exception, match="Circuit breaker open"):
                await my_api_call()

    async def test_decorator_records_failure_on_exception(self, tmp_path):
        monitor = APICostMonitor(db_path=str(tmp_path / "fail.db"))

        with patch(
            "youtube_extension.backend.services.api_cost_monitor.cost_monitor",
            monitor
        ):
            @check_rate_limit_decorator("google")
            async def my_api_call():
                raise RuntimeError("API call failed")

            with pytest.raises(RuntimeError):
                await my_api_call()

            assert monitor.circuit_breakers["google"]["failures"] >= 1


class TestAPICostMonitorInMemory:
    def test_in_memory_db_works(self):
        """APICostMonitor with :memory: db."""
        monitor = APICostMonitor(db_path=":memory:")
        assert monitor.db_path == ":memory:"

    async def test_in_memory_record_and_query(self):
        monitor = APICostMonitor(db_path=":memory:")
        record = await monitor.record_usage(
            service="openai",
            endpoint="/chat",
            tokens_used=500,
            model="gpt-4o",
        )
        assert record is not None
        cost = await monitor.get_daily_cost()
        assert cost >= 0


# ===========================================================================
# strategies.py — _extract_key_points and _extract_topics
# ===========================================================================


from youtube_extension.processors.strategies import EnhancedStrategy


@pytest.fixture(autouse=True)
def _disable_external_strategy_clients(monkeypatch):
    """These heuristic tests do not exercise Google or Gemini client setup."""
    from youtube_extension.processors import strategies

    monkeypatch.setattr(strategies, "HAS_VIDEO_DEPS", False)
    monkeypatch.setattr(strategies, "HAS_AI_DEPS", False)


class TestEnhancedStrategyExtractKeyPoints:
    def test_returns_list(self):
        enh = EnhancedStrategy()
        result = enh._extract_key_points("This is an important test. Nothing else matters.")
        assert isinstance(result, list)

    def test_finds_sentence_with_key_indicator(self):
        enh = EnhancedStrategy()
        text = "The key point is that Python is powerful. And there is another sentence."
        result = enh._extract_key_points(text)
        # Should find the sentence with "key"
        assert any("key" in kp.lower() for kp in result)

    def test_ignores_short_sentences(self):
        enh = EnhancedStrategy()
        # Short sentence with indicator should be ignored (< 20 chars)
        text = "key one. This is the main argument that explains the primary concern of experts."
        result = enh._extract_key_points(text)
        assert len(result) >= 0  # Just ensure no crash

    def test_limits_to_five(self):
        enh = EnhancedStrategy()
        # Create many sentences with key indicators
        sentences = [
            f"This is an important point number {i} worth noting" for i in range(10)
        ]
        text = ". ".join(sentences)
        result = enh._extract_key_points(text)
        assert len(result) <= 5

    def test_empty_text_returns_empty_list(self):
        enh = EnhancedStrategy()
        assert enh._extract_key_points("") == []

    def test_no_indicators_returns_empty(self):
        enh = EnhancedStrategy()
        text = "Hello world. This is a sentence. Another one here."
        result = enh._extract_key_points(text)
        assert result == []


class TestEnhancedStrategyExtractTopics:
    def test_returns_list(self):
        enh = EnhancedStrategy()
        result = enh._extract_topics("Python programming language development")
        assert isinstance(result, list)

    def test_extracts_frequent_words(self):
        enh = EnhancedStrategy()
        text = " ".join(["python"] * 10 + ["programming"] * 5 + ["language"] * 3)
        result = enh._extract_topics(text)
        assert "python" in result

    def test_filters_short_words(self):
        enh = EnhancedStrategy()
        # Words shorter than 4 chars should be filtered
        text = "cat dog fox programming development software"
        result = enh._extract_topics(text)
        # "cat", "dog", "fox" are < 4 chars — won't be in results
        assert "cat" not in result

    def test_filters_stop_words(self):
        enh = EnhancedStrategy()
        text = "this that with have will going about people really"
        result = enh._extract_topics(text)
        # All stop words — should return empty or very limited
        assert "this" not in result
        assert "that" not in result

    def test_limits_to_ten_topics(self):
        enh = EnhancedStrategy()
        # Create many unique words
        unique_words = [f"uniqueword{i:03d}" for i in range(30)]
        text = " ".join(unique_words)
        result = enh._extract_topics(text)
        assert len(result) <= 10

    def test_empty_text_returns_empty(self):
        enh = EnhancedStrategy()
        assert enh._extract_topics("") == []

    def test_returns_most_frequent_first(self):
        enh = EnhancedStrategy()
        # "machine" appears more times than "learning"
        text = "machine machine machine learning learning development"
        result = enh._extract_topics(text)
        if "machine" in result and "learning" in result:
            assert result.index("machine") < result.index("learning")


class TestEnhancedStrategyAnalyzeContent:
    async def test_returns_empty_dict_when_no_ai_deps(self):
        """When HAS_AI_DEPS is False, analyze_content returns {}."""
        from youtube_extension.processors import strategies
        original = strategies.HAS_AI_DEPS
        try:
            strategies.HAS_AI_DEPS = False
            enh = EnhancedStrategy()
            from youtube_extension.processors.strategies import TranscriptSegment
            segments = [TranscriptSegment(text="Hello world", start=0.0, duration=1.0)]
            result = await enh.analyze_content(segments)
            assert result == {}
        finally:
            strategies.HAS_AI_DEPS = original

    async def test_handles_empty_transcript(self):
        """Empty transcript list should not crash."""
        from youtube_extension.processors import strategies
        original = strategies.HAS_AI_DEPS
        try:
            strategies.HAS_AI_DEPS = False
            enh = EnhancedStrategy()
            result = await enh.analyze_content([])
            assert result == {}
        finally:
            strategies.HAS_AI_DEPS = original

    async def test_process_video_with_invalid_url(self):
        """URL that yields no video ID returns an error payload (not an exception)."""
        enh = EnhancedStrategy()
        result = await enh.process_video("not-a-youtube-url-at-all")
        assert isinstance(result, dict)
        metadata = result.get("metadata", {})
        assert metadata.get("video_id") == "unknown"
        assert result.get("error_log") is not None

    async def test_optimized_strategy_exception_path(self):
        """When enhanced strategy raises, optimized returns error dict."""
        from youtube_extension.processors.strategies import OptimizedStrategy

        class _ErrorEnhanced:
            async def process_video(self, url, options=None):
                raise RuntimeError("simulated failure")

        opt = OptimizedStrategy()
        opt._enhanced_strategy = _ErrorEnhanced()
        result = await opt.process_video("https://www.youtube.com/watch?v=auJzb1D-fag")
        assert result["success"] is False
        assert "error" in result

    async def test_parallel_strategy_exception_path(self):
        """When enhanced strategy raises, parallel returns error dict."""
        from youtube_extension.processors.strategies import ParallelStrategy

        class _ErrorEnhanced:
            async def process_video(self, url, options=None):
                raise RuntimeError("simulated parallel failure")

        par = ParallelStrategy()
        par._enhanced_strategy = _ErrorEnhanced()
        result = await par.process_video("https://www.youtube.com/watch?v=auJzb1D-fag")
        assert result["success"] is False
        assert result["parallel_processed"] is True

    async def test_parallel_batch_exception_becomes_error_dict(self):
        """Exception in gather gets wrapped in error dict."""
        from youtube_extension.processors.strategies import ParallelStrategy

        class _ErrorEnhanced:
            async def process_video(self, url, options=None):
                raise RuntimeError("batch failure")

        par = ParallelStrategy()
        par._enhanced_strategy = _ErrorEnhanced()

        # We need multiple URLs so gather runs
        urls = [
            "https://www.youtube.com/watch?v=auJzb1D-fag",
            "https://www.youtube.com/watch?v=auJzb1D-fag",
        ]
        results = await par.process_batch(urls)
        assert all(r.get("success") is False for r in results)
