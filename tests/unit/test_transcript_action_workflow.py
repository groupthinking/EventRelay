from __future__ import annotations

import asyncio
import datetime
from dataclasses import asdict
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import youtube_extension.services.cloud.cloud_tasks_queue as cloud_tasks_queue
from shared.youtube import RobustYouTubeMetadata
from youtube_extension.backend.api.v1.models import TranscriptActionRequest
from youtube_extension.backend.api.v1.router import _queue_transcript_action_job
from youtube_extension.services.agents.adapters.agent_orchestrator import (
    AgentOrchestrator,
    OrchestrationResult,
)
from youtube_extension.services.agents.dto import AgentResult
from youtube_extension.services.ai.speech_to_text_service import SpeechToTextResult
from youtube_extension.services.cloud.cloud_tasks_queue import CloudTasksQueueService
from youtube_extension.services.workflows.transcript_action_workflow import (
    TranscriptActionWorkflow,
)


@pytest.fixture(autouse=True)
def _isolate_skill_builder(monkeypatch, tmp_path) -> None:
    """Workflow unit tests must not use the process user's persistent skills."""
    skill_builder = MagicMock()
    skill_builder.get_context.return_value = {
        "has_data": False,
        "lessons": [],
        "success_rate": 0,
    }
    skill_builder.skills_dir = tmp_path / "skills"
    monkeypatch.setattr(
        "youtube_extension.services.workflows.transcript_action_workflow.get_skill_builder",
        lambda: skill_builder,
    )


class _UnexpectedYouTubeService:
    async def __aenter__(self):
        raise AssertionError("YouTube service should not be entered for playlist URLs")

    async def __aexit__(self, exc_type, exc, tb):
        return False


@pytest.mark.asyncio
async def test_playlist_urls_fail_fast() -> None:
    workflow = TranscriptActionWorkflow(
        youtube_service_factory=lambda: _UnexpectedYouTubeService(),
        orchestrator=SimpleNamespace(),
        speech_service=SimpleNamespace(),
    )

    with pytest.raises(ValueError, match="Playlist URLs are not supported"):
        await workflow.run("https://www.youtube.com/playlist?list=PL1234567890")


@pytest.mark.asyncio
async def test_queue_transcript_action_job_uses_cloud_tasks(monkeypatch) -> None:
    async def _fake_enqueue(self, video_task, task_config=None) -> str:
        return task_config.task_name if task_config else video_task.video_id

    monkeypatch.setattr(cloud_tasks_queue, "CLOUD_TASKS_AVAILABLE", True)
    monkeypatch.setattr(CloudTasksQueueService, "initialize", lambda self: None)
    monkeypatch.setattr(CloudTasksQueueService, "close", lambda self: None)
    monkeypatch.setattr(
        CloudTasksQueueService,
        "enqueue_video_processing",
        _fake_enqueue,
    )

    request = TranscriptActionRequest(
        video_url="https://www.youtube.com/watch?v=auJzb1D-fag",
        language="en",
    )
    metadata = RobustYouTubeMetadata(
        video_id="auJzb1D-fag",
        title="Long Video",
        description="",
        channel_id="channel",
        channel_title="Channel",
        published_at="2024-01-01T00:00:00Z",
        duration="PT16M",
        view_count=100,
        like_count=10,
        comment_count=1,
        thumbnail_urls={},
        tags=[],
        category_id="28",
        default_language="en",
        default_audio_language="en",
        live_broadcast_content="none",
        transcript_available=True,
        transcript_segments=12,
        source_api="test",
    )

    result = await _queue_transcript_action_job(
        request,
        metadata=metadata,
        http_request=SimpleNamespace(base_url="http://testserver/"),
    )

    assert result["async_processing"] is True
    assert result["processing_transport"] == "cloud_tasks"
    assert result["status_url"] == "http://testserver/api/v1/videos/" + result["job_id"] + "/status"


# ---------------------------------------------------------------------------
# Helpers / shared fixtures
# ---------------------------------------------------------------------------

def _make_metadata(**overrides) -> RobustYouTubeMetadata:
    """Return a minimal but valid RobustYouTubeMetadata instance."""
    defaults = dict(
        video_id="auJzb1D-fag",
        title="Test Video",
        description="A test video",
        channel_id="UC_channel",
        channel_title="Test Channel",
        published_at="2024-01-01T00:00:00Z",
        duration="PT5M",
        view_count=1000,
        like_count=50,
        comment_count=10,
        thumbnail_urls={},
        tags=["test"],
        category_id="28",
        default_language="en",
        default_audio_language="en",
        live_broadcast_content="none",
        transcript_available=True,
        transcript_segments=5,
        source_api="test",
    )
    defaults.update(overrides)
    return RobustYouTubeMetadata(**defaults)


def _make_yt_service_factory(
    metadata: RobustYouTubeMetadata,
    transcript: dict | None = None,
) -> callable:
    """Factory for a fake async-context-manager YouTube service."""

    class _FakeYTService:
        async def get_video_metadata(self, url):
            return metadata

        async def get_transcript(self, video_id, language="en"):
            return transcript or {"text": "Hello world transcript.", "segments": [], "source": "youtube_api"}

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            pass

    return lambda: _FakeYTService()


def _make_orchestrator(
    agent_data: dict | None = None,
    success: bool = True,
    errors: list | None = None,
) -> MagicMock:
    """Return a mock AgentOrchestrator whose execute_task returns an OrchestrationResult."""
    agent_output = agent_data or {"task_board": {}}
    agent_result = AgentResult(
        status="ok" if success else "error",
        output=agent_output,
        logs=[],
    )
    result = OrchestrationResult(
        success=success,
        results={"transcript_action": agent_result},
        errors=errors or [],
        total_processing_time=0.5,
        agents_used=["transcript_action"],
        timestamp=datetime.datetime.utcnow(),
    )
    mock_orch = MagicMock(spec=AgentOrchestrator)
    mock_orch.execute_task = AsyncMock(return_value=result)
    return mock_orch


def _make_workflow(
    metadata: RobustYouTubeMetadata | None = None,
    transcript: dict | None = None,
    orchestrator: MagicMock | None = None,
    ml_client: MagicMock | None = None,
    metrics_service: MagicMock | None = None,
    hybrid_processor: MagicMock | None = None,
    speech_service: MagicMock | None = None,
) -> TranscriptActionWorkflow:
    """Build a TranscriptActionWorkflow with all external dependencies mocked."""
    meta = metadata or _make_metadata()
    yt_factory = _make_yt_service_factory(meta, transcript)
    orch = orchestrator or _make_orchestrator()

    # Default ML client that does nothing but not raise
    if ml_client is None:
        ml = MagicMock()
        ml.score_transcript = AsyncMock(return_value=None)
        ml.record_transcript_outcome = AsyncMock(return_value=None)
        ml.rank_actions = AsyncMock(return_value={"ranked_actions": []})
    else:
        ml = ml_client

    # Skill builder that does nothing
    skill_builder = MagicMock()
    skill_builder.get_context.return_value = {"has_data": False, "lessons": [], "success_rate": 0}
    skill_builder.record_deployment.return_value = None

    wf = TranscriptActionWorkflow(
        youtube_service_factory=yt_factory,
        orchestrator=orch,
        hybrid_processor=hybrid_processor,
        speech_service=speech_service or MagicMock(),
        metrics_service=metrics_service,
        ml_client=ml,
    )
    # Replace skill builder so we control it
    wf._skill_builder = skill_builder
    return wf


# ---------------------------------------------------------------------------
# validate_video_url
# ---------------------------------------------------------------------------

class TestValidateVideoUrl:
    def test_valid_watch_url(self):
        wf = _make_workflow()
        # Should not raise
        wf.validate_video_url("https://www.youtube.com/watch?v=auJzb1D-fag")

    def test_valid_short_url(self):
        wf = _make_workflow()
        wf.validate_video_url("https://youtu.be/auJzb1D-fag")

    def test_playlist_url_raises(self):
        wf = _make_workflow()
        with pytest.raises(ValueError, match="Playlist URLs are not supported"):
            wf.validate_video_url("https://www.youtube.com/playlist?list=PL1234567890")

    def test_playlist_path_raises(self):
        wf = _make_workflow()
        with pytest.raises(ValueError, match="Playlist URLs are not supported"):
            wf.validate_video_url("https://www.youtube.com/playlist")

    def test_list_param_without_video_id_raises(self):
        wf = _make_workflow()
        with pytest.raises(ValueError, match="Playlist URLs are not supported"):
            wf.validate_video_url("https://www.youtube.com/watch?list=PLsomelist")

    def test_video_with_list_param_allowed(self):
        wf = _make_workflow()
        # watch?v= takes priority over list=
        wf.validate_video_url("https://www.youtube.com/watch?v=auJzb1D-fag&list=PLsomelist")


# ---------------------------------------------------------------------------
# get_duration_seconds
# ---------------------------------------------------------------------------

class TestGetDurationSeconds:
    def test_pt5m(self):
        meta = _make_metadata(duration="PT5M")
        assert TranscriptActionWorkflow.get_duration_seconds(meta) == 300

    def test_pt1h(self):
        meta = _make_metadata(duration="PT1H")
        assert TranscriptActionWorkflow.get_duration_seconds(meta) == 3600

    def test_pt0s(self):
        meta = _make_metadata(duration="PT0S")
        assert TranscriptActionWorkflow.get_duration_seconds(meta) == 0

    def test_dict_input(self):
        assert TranscriptActionWorkflow.get_duration_seconds({"duration": "PT2M30S"}) == 150

    def test_none_duration(self):
        result = TranscriptActionWorkflow.get_duration_seconds({"duration": None})
        assert result == 0


# ---------------------------------------------------------------------------
# _coerce_metadata
# ---------------------------------------------------------------------------

class TestCoerceMetadata:
    def test_none_returns_none(self):
        assert TranscriptActionWorkflow._coerce_metadata(None) is None

    def test_metadata_object_returned_unchanged(self):
        meta = _make_metadata()
        assert TranscriptActionWorkflow._coerce_metadata(meta) is meta

    def test_dict_creates_metadata(self):
        meta = _make_metadata()
        d = asdict(meta)
        result = TranscriptActionWorkflow._coerce_metadata(d)
        assert isinstance(result, RobustYouTubeMetadata)
        assert result.video_id == meta.video_id


# ---------------------------------------------------------------------------
# _build_transcript_source_order
# ---------------------------------------------------------------------------

class TestBuildTranscriptSourceOrder:
    def test_none_predicted_returns_default(self):
        order = TranscriptActionWorkflow._build_transcript_source_order(None)
        assert order == ["youtube_api", "speech_v2", "gemini_video"]

    def test_youtube_api_predicted_starts_with_youtube(self):
        order = TranscriptActionWorkflow._build_transcript_source_order("youtube_api")
        assert order[0] == "youtube_api"

    def test_speech_v2_predicted_starts_with_speech(self):
        order = TranscriptActionWorkflow._build_transcript_source_order("speech_v2")
        assert order[0] == "speech_v2"

    def test_gemini_video_predicted(self):
        order = TranscriptActionWorkflow._build_transcript_source_order("gemini_video")
        assert order[0] == "gemini_video"

    def test_gemini_video_file_maps_to_gemini(self):
        order = TranscriptActionWorkflow._build_transcript_source_order("gemini_video_file")
        assert order[0] == "gemini_video"

    def test_no_duplicates(self):
        for pred in [None, "youtube_api", "speech_v2", "gemini_video", "gemini_video_file"]:
            order = TranscriptActionWorkflow._build_transcript_source_order(pred)
            assert len(order) == len(set(order)), f"Duplicates found for predicted={pred!r}"

    def test_all_three_sources_present(self):
        for pred in [None, "youtube_api", "speech_v2", "gemini_video"]:
            order = TranscriptActionWorkflow._build_transcript_source_order(pred)
            assert set(order) >= {"youtube_api", "speech_v2", "gemini_video"}


# ---------------------------------------------------------------------------
# _normalize_transcript_source
# ---------------------------------------------------------------------------

class TestNormalizeTranscriptSource:
    def test_youtube_transcript_api(self):
        assert TranscriptActionWorkflow._normalize_transcript_source("youtube_transcript_api") == "youtube_api"

    def test_innertube_android(self):
        assert TranscriptActionWorkflow._normalize_transcript_source("innertube_android") == "youtube_api"

    def test_youtube_search_python(self):
        assert TranscriptActionWorkflow._normalize_transcript_source("youtube_search_python") == "youtube_api"

    def test_speech_to_text_v2_prefix(self):
        assert TranscriptActionWorkflow._normalize_transcript_source("speech_to_text_v2_gcs") == "speech_v2"

    def test_speech_to_text_v2_exact(self):
        assert TranscriptActionWorkflow._normalize_transcript_source("speech_to_text_v2") == "speech_v2"

    def test_gemini_video(self):
        assert TranscriptActionWorkflow._normalize_transcript_source("gemini_video") == "gemini_video"

    def test_gemini_video_file(self):
        assert TranscriptActionWorkflow._normalize_transcript_source("gemini_video_file") == "gemini_video_file"

    def test_unknown_passthrough(self):
        assert TranscriptActionWorkflow._normalize_transcript_source("custom_source") == "custom_source"


# ---------------------------------------------------------------------------
# _parse_gemini_transcript_payload
# ---------------------------------------------------------------------------

class TestParseGeminiTranscriptPayload:
    def test_empty_string(self):
        text, segs = TranscriptActionWorkflow._parse_gemini_transcript_payload("")
        assert text == ""
        assert segs == []

    def test_json_with_transcript_key(self):
        import json
        payload = json.dumps({"transcript": "Hello world", "segments": []})
        text, segs = TranscriptActionWorkflow._parse_gemini_transcript_payload(payload)
        assert text == "Hello world"
        assert segs == []

    def test_json_with_text_key(self):
        import json
        payload = json.dumps({"text": "Goodbye world", "segments": []})
        text, segs = TranscriptActionWorkflow._parse_gemini_transcript_payload(payload)
        assert text == "Goodbye world"

    def test_invalid_json_returns_raw(self):
        raw = "not json at all"
        text, segs = TranscriptActionWorkflow._parse_gemini_transcript_payload(raw)
        assert text == raw
        assert segs == []

    def test_json_list_of_dicts(self):
        import json
        payload = json.dumps([{"text": "segment one"}, {"text": "segment two"}])
        text, segs = TranscriptActionWorkflow._parse_gemini_transcript_payload(payload)
        assert "segment one" in text
        assert "segment two" in text

    def test_json_with_segments(self):
        import json
        payload = json.dumps({
            "transcript": "Hello",
            "segments": [{"text": "Hello", "start": 0, "duration": 1}]
        })
        text, segs = TranscriptActionWorkflow._parse_gemini_transcript_payload(payload)
        assert text == "Hello"
        assert len(segs) == 1
        assert segs[0]["text"] == "Hello"

    def test_json_dict_with_no_text_key_returns_json(self):
        import json
        payload = json.dumps({"foo": "bar"})
        text, segs = TranscriptActionWorkflow._parse_gemini_transcript_payload(payload)
        # non-empty dict without transcript/text key falls back to json dump
        assert text == payload

    def test_json_scalar_string(self):
        import json
        payload = json.dumps("hello scalar")
        text, segs = TranscriptActionWorkflow._parse_gemini_transcript_payload(payload)
        assert text == "hello scalar"
        assert segs == []


# ---------------------------------------------------------------------------
# _normalise_segments
# ---------------------------------------------------------------------------

class TestNormaliseSegments:
    def test_none_returns_empty(self):
        assert TranscriptActionWorkflow._normalise_segments(None) == []

    def test_empty_list(self):
        assert TranscriptActionWorkflow._normalise_segments([]) == []

    def test_non_list_returns_empty(self):
        assert TranscriptActionWorkflow._normalise_segments("bad") == []

    def test_skips_entries_without_text(self):
        segs = [{"start": 0, "duration": 1}]  # no text key
        result = TranscriptActionWorkflow._normalise_segments(segs)
        assert result == []

    def test_normalises_basic_segment(self):
        segs = [{"text": "Hello", "start": 0.0, "duration": 1.5}]
        result = TranscriptActionWorkflow._normalise_segments(segs)
        assert len(result) == 1
        assert result[0]["text"] == "Hello"
        assert result[0]["start"] == 0.0
        assert result[0]["duration"] == 1.5

    def test_computes_duration_from_end(self):
        segs = [{"text": "Hi", "start": 1.0, "end": 3.0}]
        result = TranscriptActionWorkflow._normalise_segments(segs)
        assert result[0]["duration"] == pytest.approx(2.0)

    def test_skips_non_dict_entries(self):
        segs = ["string entry", {"text": "Real segment", "start": 0}]
        result = TranscriptActionWorkflow._normalise_segments(segs)
        assert len(result) == 1
        assert result[0]["text"] == "Real segment"

    def test_start_time_alias(self):
        segs = [{"text": "Hi", "start_time": "1.5s", "duration": 2}]
        result = TranscriptActionWorkflow._normalise_segments(segs)
        assert result[0]["start"] == pytest.approx(1.5)


# ---------------------------------------------------------------------------
# _parse_to_seconds
# ---------------------------------------------------------------------------

class TestParseToSeconds:
    def test_none_returns_zero(self):
        assert TranscriptActionWorkflow._parse_to_seconds(None) == 0.0

    def test_int(self):
        assert TranscriptActionWorkflow._parse_to_seconds(30) == 30.0

    def test_float(self):
        assert TranscriptActionWorkflow._parse_to_seconds(1.5) == 1.5

    def test_string_seconds_with_s(self):
        assert TranscriptActionWorkflow._parse_to_seconds("5s") == 5.0

    def test_string_float(self):
        assert TranscriptActionWorkflow._parse_to_seconds("3.14") == pytest.approx(3.14)

    def test_mm_ss_format(self):
        assert TranscriptActionWorkflow._parse_to_seconds("1:30") == 90.0

    def test_hh_mm_ss_format(self):
        assert TranscriptActionWorkflow._parse_to_seconds("1:00:00") == 3600.0

    def test_invalid_string_returns_zero(self):
        assert TranscriptActionWorkflow._parse_to_seconds("abc") == 0.0

    def test_non_string_non_numeric(self):
        assert TranscriptActionWorkflow._parse_to_seconds([]) == 0.0


# ---------------------------------------------------------------------------
# _seconds_to_offset
# ---------------------------------------------------------------------------

class TestSecondsToOffset:
    def test_integer_seconds(self):
        assert TranscriptActionWorkflow._seconds_to_offset(5.0) == "5s"

    def test_fractional_seconds(self):
        assert TranscriptActionWorkflow._seconds_to_offset(1.5) == "1.5s"

    def test_zero(self):
        assert TranscriptActionWorkflow._seconds_to_offset(0.0) == "0s"


# ---------------------------------------------------------------------------
# _build_video_metadata
# ---------------------------------------------------------------------------

class TestBuildVideoMetadata:
    def _wf(self):
        return _make_workflow()

    def test_none_returns_none(self):
        assert self._wf()._build_video_metadata(None) is None

    def test_empty_dict_returns_none(self):
        assert self._wf()._build_video_metadata({}) is None

    def test_start_seconds(self):
        result = self._wf()._build_video_metadata({"start_seconds": 10})
        assert result["start_offset"] == "10s"

    def test_end_seconds(self):
        result = self._wf()._build_video_metadata({"end_seconds": 60})
        assert result["end_offset"] == "60s"

    def test_fps(self):
        result = self._wf()._build_video_metadata({"fps": 30})
        assert result["fps"] == 30.0

    def test_namespace_options(self):
        opts = SimpleNamespace(start_seconds=5, end_seconds=None, fps=None)
        result = self._wf()._build_video_metadata(opts)
        assert result is not None
        assert result["start_offset"] == "5s"

    def test_namespace_all_none_returns_none(self):
        opts = SimpleNamespace(start_seconds=None, end_seconds=None, fps=None)
        assert self._wf()._build_video_metadata(opts) is None


# ---------------------------------------------------------------------------
# _extract_actions_for_ranking
# ---------------------------------------------------------------------------

class TestExtractActionsForRanking:
    def test_empty_data_returns_empty(self):
        result = TranscriptActionWorkflow._extract_actions_for_ranking({})
        assert result == []

    def test_task_board_not_dict_returns_empty(self):
        result = TranscriptActionWorkflow._extract_actions_for_ranking({"task_board": "bad"})
        assert result == []

    def test_extracts_items_from_columns(self):
        data = {
            "task_board": {
                "todo": [{"title": "Do something", "description": "Detailed desc"}]
            }
        }
        result = TranscriptActionWorkflow._extract_actions_for_ranking(data)
        assert len(result) == 1
        assert result[0]["category"] == "todo"
        assert "Do something" in result[0]["text"]

    def test_skips_items_without_text(self):
        data = {
            "task_board": {
                "todo": [{"title": "", "description": ""}]
            }
        }
        result = TranscriptActionWorkflow._extract_actions_for_ranking(data)
        assert result == []

    def test_uses_definition_of_done_if_present(self):
        data = {
            "task_board": {
                "todo": [{"title": "T", "definition_of_done": "DoD text"}]
            }
        }
        result = TranscriptActionWorkflow._extract_actions_for_ranking(data)
        assert "DoD text" in result[0]["text"]

    def test_skips_non_dict_items(self):
        data = {
            "task_board": {
                "todo": ["string item", {"title": "Real Task", "description": "desc"}]
            }
        }
        result = TranscriptActionWorkflow._extract_actions_for_ranking(data)
        assert len(result) == 1

    def test_skips_non_list_columns(self):
        data = {
            "task_board": {
                "bad_column": "not a list",
                "good_column": [{"title": "Task", "description": "desc"}],
            }
        }
        result = TranscriptActionWorkflow._extract_actions_for_ranking(data)
        assert len(result) == 1


# ---------------------------------------------------------------------------
# _serialize_agent
# ---------------------------------------------------------------------------

class TestSerializeAgent:
    def test_agent_result_with_status_ok(self):
        ar = AgentResult(status="ok", output={"key": "val"}, logs=[])
        result = TranscriptActionWorkflow._serialize_agent(ar)
        assert result["success"] is True
        assert result["data"] == {"key": "val"}
        assert result["errors"] == []

    def test_agent_result_with_status_error(self):
        ar = AgentResult(status="error", output={}, logs=["something went wrong"])
        result = TranscriptActionWorkflow._serialize_agent(ar)
        assert result["success"] is False

    def test_uses_success_attr_when_present(self):
        mock_ar = SimpleNamespace(success=True, data={"a": 1}, errors=[], processing_time=0.1, timestamp=None)
        result = TranscriptActionWorkflow._serialize_agent(mock_ar)
        assert result["success"] is True
        assert result["data"] == {"a": 1}

    def test_timestamp_isoformat(self):
        ts = datetime.datetime(2024, 1, 1, 12, 0, 0)
        mock_ar = SimpleNamespace(success=True, data=None, errors=[], processing_time=0.0, timestamp=ts)
        result = TranscriptActionWorkflow._serialize_agent(mock_ar)
        assert result["timestamp"] == ts.isoformat()

    def test_timestamp_none_stays_none(self):
        mock_ar = SimpleNamespace(success=True, data=None, errors=[], processing_time=0.0, timestamp=None)
        result = TranscriptActionWorkflow._serialize_agent(mock_ar)
        assert result["timestamp"] is None


# ---------------------------------------------------------------------------
# fetch_video_metadata
# ---------------------------------------------------------------------------

class TestFetchVideoMetadata:
    async def test_returns_metadata_from_service(self):
        meta = _make_metadata()
        wf = _make_workflow(metadata=meta)
        result = await wf.fetch_video_metadata("https://www.youtube.com/watch?v=auJzb1D-fag")
        assert result.video_id == "auJzb1D-fag"

    async def test_fallback_on_exception(self):
        """When yt_service.get_video_metadata raises, fallback metadata is returned."""
        meta = _make_metadata()

        class _FailingYTService:
            async def get_video_metadata(self, url):
                raise RuntimeError("service down")

            async def __aenter__(self):
                return self

            async def __aexit__(self, *a):
                pass

        wf = _make_workflow(metadata=meta)
        wf._youtube_service_factory = lambda: _FailingYTService()
        result = await wf.fetch_video_metadata("https://www.youtube.com/watch?v=auJzb1D-fag")
        # Fallback should return metadata with extracted video_id
        assert result.video_id == "auJzb1D-fag"
        assert result.source_api == "fallback"

    async def test_rejects_playlist(self):
        wf = _make_workflow()
        with pytest.raises(ValueError, match="Playlist URLs are not supported"):
            await wf.fetch_video_metadata("https://www.youtube.com/playlist?list=PL123")


# ---------------------------------------------------------------------------
# run() — full pipeline
# ---------------------------------------------------------------------------

class TestRun:
    async def test_run_with_prefetched_metadata_and_transcript_text(self):
        """Providing both prefetched metadata and transcript_text skips YT fetching."""
        meta = _make_metadata()
        orch = _make_orchestrator()
        wf = _make_workflow(metadata=meta, orchestrator=orch)

        result = await wf.run(
            "https://www.youtube.com/watch?v=auJzb1D-fag",
            transcript_text="This is a test transcript",
            prefetched_metadata=meta,
        )

        assert result["success"] is True
        assert result["transcript"]["source"] == "provided"
        assert result["transcript"]["text"] == "This is a test transcript"

    async def test_run_returns_failure_when_transcript_empty(self):
        """If transcript extraction returns empty text, run() returns success=False."""
        meta = _make_metadata()
        empty_transcript = {"text": "", "segments": [], "source": "youtube_api", "error": "no captions"}
        orch = _make_orchestrator()

        class _EmptyTranscriptService:
            async def get_video_metadata(self, url):
                return meta

            async def get_transcript(self, video_id, language="en"):
                return empty_transcript

            async def __aenter__(self):
                return self

            async def __aexit__(self, *a):
                pass

        # Speech service that also returns empty (so all fallbacks fail)
        from youtube_extension.services.ai.speech_to_text_service import SpeechToTextResult
        failing_speech_result = SpeechToTextResult(
            success=False,
            transcript="",
            segments=[],
            latency=0.1,
            error="no audio",
            source="speech_to_text_v2",
        )
        speech_service = MagicMock()
        speech_service.transcribe_youtube_video = AsyncMock(return_value=failing_speech_result)

        wf = _make_workflow(metadata=meta, orchestrator=orch, speech_service=speech_service, hybrid_processor=MagicMock())
        # Disable gemini so it doesn't try file downloads
        wf._hybrid_processor = None
        wf._youtube_service_factory = lambda: _EmptyTranscriptService()

        result = await wf.run(
            "https://www.youtube.com/watch?v=auJzb1D-fag",
            prefetched_metadata=meta,
        )

        assert result["success"] is False
        assert "errors" in result
        assert len(result["errors"]) > 0

    async def test_run_with_video_options(self):
        """video_options dict is passed through to transcript metadata."""
        meta = _make_metadata()
        orch = _make_orchestrator()
        wf = _make_workflow(metadata=meta, orchestrator=orch)

        result = await wf.run(
            "https://www.youtube.com/watch?v=auJzb1D-fag",
            transcript_text="Test text",
            prefetched_metadata=meta,
            video_options={"start_seconds": 10, "end_seconds": 60},
        )

        assert result["success"] is True
        assert "requested_video_metadata" in result["transcript"]

    async def test_run_playlist_raises(self):
        wf = _make_workflow()
        with pytest.raises(ValueError, match="Playlist URLs are not supported"):
            await wf.run("https://www.youtube.com/playlist?list=PL12345")

    async def test_run_dict_prefetched_metadata(self):
        """Prefetched metadata as dict is coerced to RobustYouTubeMetadata."""
        meta = _make_metadata()
        meta_dict = asdict(meta)
        orch = _make_orchestrator()
        wf = _make_workflow(metadata=meta, orchestrator=orch)

        result = await wf.run(
            "https://www.youtube.com/watch?v=auJzb1D-fag",
            transcript_text="Dict metadata test",
            prefetched_metadata=meta_dict,
        )

        assert result["success"] is True

    async def test_run_skill_builder_called(self):
        """skill_builder.record_deployment is called after successful run."""
        meta = _make_metadata()
        orch = _make_orchestrator()
        wf = _make_workflow(metadata=meta, orchestrator=orch)

        await wf.run(
            "https://www.youtube.com/watch?v=auJzb1D-fag",
            transcript_text="Test",
            prefetched_metadata=meta,
        )

        wf._skill_builder.record_deployment.assert_called_once()

    async def test_run_with_learned_lessons(self):
        """If skill_builder returns lessons, they are injected into agent input."""
        meta = _make_metadata()
        orch = _make_orchestrator()
        wf = _make_workflow(metadata=meta, orchestrator=orch)
        wf._skill_builder.get_context.return_value = {
            "has_data": True,
            "lessons": ["lesson 1", "lesson 2"],
            "success_rate": 0.9,
        }

        result = await wf.run(
            "https://www.youtube.com/watch?v=auJzb1D-fag",
            transcript_text="Test",
            prefetched_metadata=meta,
        )

        assert result["success"] is True
        # orchestrator.execute_task should have been called with learned_lessons
        call_args = orch.execute_task.call_args
        agent_input = call_args[0][1]
        assert "learned_lessons" in agent_input


# ---------------------------------------------------------------------------
# _record_transcript_outcome
# ---------------------------------------------------------------------------

class TestRecordTranscriptOutcome:
    async def test_records_outcome_on_success(self):
        ml = MagicMock()
        ml.record_transcript_outcome = AsyncMock()
        wf = _make_workflow(ml_client=ml)

        await wf._record_transcript_outcome(
            {"video_id": "auJzb1D-fag"},
            {"text": "Hello world " * 50, "source": "youtube_api", "segments": [{}] * 10},
        )

        ml.record_transcript_outcome.assert_called_once()
        call_kwargs = ml.record_transcript_outcome.call_args[1]
        assert call_kwargs["success"] is True
        assert call_kwargs["actual_source"] == "youtube_api"
        assert 0.0 <= call_kwargs["actual_quality"] <= 1.0

    async def test_records_outcome_on_failure(self):
        ml = MagicMock()
        ml.record_transcript_outcome = AsyncMock()
        wf = _make_workflow(ml_client=ml)

        await wf._record_transcript_outcome(
            {"video_id": "auJzb1D-fag"},
            {"text": "", "source": "unavailable", "segments": []},
        )

        ml.record_transcript_outcome.assert_called_once()
        call_kwargs = ml.record_transcript_outcome.call_args[1]
        assert call_kwargs["success"] is False
        assert call_kwargs["actual_quality"] == 0.0

    async def test_swallows_ml_exception(self):
        """record_transcript_outcome swallows exceptions from ml_client."""
        ml = MagicMock()
        ml.record_transcript_outcome = AsyncMock(side_effect=RuntimeError("ml unavailable"))
        wf = _make_workflow(ml_client=ml)

        # Must not raise
        await wf._record_transcript_outcome(
            {"video_id": "auJzb1D-fag"},
            {"text": "some text", "source": "youtube_api", "segments": []},
        )

    async def test_quality_capped_at_1(self):
        """Quality should never exceed 1.0."""
        ml = MagicMock()
        ml.record_transcript_outcome = AsyncMock()
        wf = _make_workflow(ml_client=ml)

        # Very long transcript with many segments
        huge_text = "word " * 10000
        many_segments = [{}] * 1000

        await wf._record_transcript_outcome(
            {"video_id": "auJzb1D-fag"},
            {"text": huge_text, "source": "youtube_api", "segments": many_segments},
        )

        call_kwargs = ml.record_transcript_outcome.call_args[1]
        assert call_kwargs["actual_quality"] <= 1.0

    async def test_normalizes_youtube_api_sources(self):
        """Source youtube_transcript_api should be normalized to youtube_api."""
        ml = MagicMock()
        ml.record_transcript_outcome = AsyncMock()
        wf = _make_workflow(ml_client=ml)

        await wf._record_transcript_outcome(
            {"video_id": "auJzb1D-fag"},
            {"text": "transcript text", "source": "youtube_transcript_api", "segments": []},
        )

        call_kwargs = ml.record_transcript_outcome.call_args[1]
        assert call_kwargs["actual_source"] == "youtube_api"


# ---------------------------------------------------------------------------
# _safe_score_transcript
# ---------------------------------------------------------------------------

class TestSafeScoreTranscript:
    async def test_returns_score_from_ml_client(self):
        ml = MagicMock()
        ml.score_transcript = AsyncMock(return_value={"recommended_source": "youtube_api"})
        wf = _make_workflow(ml_client=ml)

        result = await wf._safe_score_transcript({"video_id": "auJzb1D-fag"})

        assert result == {"recommended_source": "youtube_api"}

    async def test_returns_none_on_ml_exception(self):
        ml = MagicMock()
        ml.score_transcript = AsyncMock(side_effect=RuntimeError("ml down"))
        wf = _make_workflow(ml_client=ml)

        result = await wf._safe_score_transcript({"video_id": "auJzb1D-fag"})

        assert result is None


# ---------------------------------------------------------------------------
# _rank_orchestrated_actions
# ---------------------------------------------------------------------------

class TestRankOrchestratedActions:
    async def test_does_nothing_when_no_transcript_action(self):
        ml = MagicMock()
        ml.rank_actions = AsyncMock(return_value={"ranked_actions": []})
        wf = _make_workflow(ml_client=ml)

        meta = _make_metadata()
        orchestration = {"agents": {}, "success": True, "errors": []}
        await wf._rank_orchestrated_actions(orchestration, meta)

        ml.rank_actions.assert_not_called()

    async def test_does_nothing_when_no_task_board(self):
        ml = MagicMock()
        ml.rank_actions = AsyncMock(return_value={"ranked_actions": []})
        wf = _make_workflow(ml_client=ml)

        meta = _make_metadata()
        orchestration = {
            "agents": {"transcript_action": {"data": {"no_task_board": True}}},
            "success": True,
            "errors": [],
        }
        await wf._rank_orchestrated_actions(orchestration, meta)

        ml.rank_actions.assert_not_called()

    async def test_ranks_actions_when_task_board_present(self):
        ml = MagicMock()
        ml.rank_actions = AsyncMock(return_value={
            "ranked_actions": [{"text": "Do X — desc", "score": 0.9}],
            "total_actions": 1,
            "processing_time_seconds": 0.1,
        })
        wf = _make_workflow(ml_client=ml)

        meta = _make_metadata()
        orchestration = {
            "agents": {
                "transcript_action": {
                    "data": {
                        "task_board": {
                            "todo": [{"title": "Do X", "description": "desc"}]
                        }
                    }
                }
            },
            "success": True,
            "errors": [],
        }
        await wf._rank_orchestrated_actions(orchestration, meta)

        ml.rank_actions.assert_called_once()
        data = orchestration["agents"]["transcript_action"]["data"]
        assert "priority_ranked_actions" in data
        assert "action_ranking_meta" in data

    async def test_swallows_ranking_exception(self):
        ml = MagicMock()
        ml.rank_actions = AsyncMock(side_effect=RuntimeError("ranking unavailable"))
        wf = _make_workflow(ml_client=ml)

        meta = _make_metadata()
        orchestration = {
            "agents": {
                "transcript_action": {
                    "data": {
                        "task_board": {"todo": [{"title": "Task", "description": "desc"}]}
                    }
                }
            },
        }
        # Must not raise
        await wf._rank_orchestrated_actions(orchestration, meta)

    async def test_does_nothing_when_ranked_actions_empty(self):
        ml = MagicMock()
        ml.rank_actions = AsyncMock(return_value={"ranked_actions": []})
        wf = _make_workflow(ml_client=ml)

        meta = _make_metadata()
        data = {"task_board": {"todo": [{"title": "Task", "description": "desc"}]}}
        orchestration = {
            "agents": {"transcript_action": {"data": data}}
        }
        await wf._rank_orchestrated_actions(orchestration, meta)

        assert "priority_ranked_actions" not in data


# ---------------------------------------------------------------------------
# _record_metric
# ---------------------------------------------------------------------------

class TestRecordMetric:
    async def test_does_nothing_without_metrics_service(self):
        wf = _make_workflow(metrics_service=None)
        # Should not raise
        await wf._record_metric("test_metric", 1.0, tags={"key": "val"})

    async def test_calls_metrics_service(self):
        metrics = MagicMock()
        metrics.record_metric = AsyncMock()
        wf = _make_workflow(metrics_service=metrics)

        await wf._record_metric("test_metric", 2.5, tags={"provider": "test"})

        metrics.record_metric.assert_called_once_with(
            "test_metric", 2.5, tags={"provider": "test"}
        )


# ---------------------------------------------------------------------------
# _fallback_transcript_with_speech_service
# ---------------------------------------------------------------------------

class TestFallbackTranscriptWithSpeechService:
    async def test_success_path(self):
        speech_result = SpeechToTextResult(
            success=True,
            transcript="Speech transcript",
            segments=[{"text": "segment", "start": 0, "duration": 1}],
            latency=0.5,
            source="speech_to_text_v2",
        )
        speech_service = MagicMock()
        speech_service.transcribe_youtube_video = AsyncMock(return_value=speech_result)
        wf = _make_workflow(speech_service=speech_service)

        result = await wf._fallback_transcript_with_speech_service(
            "https://www.youtube.com/watch?v=auJzb1D-fag",
            language="en",
        )

        assert result["text"] == "Speech transcript"
        assert result["source"] == "speech_to_text_v2"
        assert "error" not in result

    async def test_failure_path(self):
        speech_result = SpeechToTextResult(
            success=False,
            transcript="",
            segments=[],
            latency=0.2,
            error="no audio",
            source="speech_to_text_v2",
        )
        speech_service = MagicMock()
        speech_service.transcribe_youtube_video = AsyncMock(return_value=speech_result)
        wf = _make_workflow(speech_service=speech_service)

        result = await wf._fallback_transcript_with_speech_service(
            "https://www.youtube.com/watch?v=auJzb1D-fag",
            language="en",
        )

        assert result["text"] == ""
        assert "error" in result


# ---------------------------------------------------------------------------
# _fallback_transcript_with_gemini
# ---------------------------------------------------------------------------

class TestFallbackTranscriptWithGemini:
    async def test_returns_unavailable_when_no_hybrid_processor(self):
        wf = _make_workflow(hybrid_processor=None)
        # Explicitly set to None to trigger the guard
        wf._hybrid_processor = None

        result = await wf._fallback_transcript_with_gemini(
            "https://www.youtube.com/watch?v=auJzb1D-fag",
            language="en",
            video_metadata=None,
        )

        assert result["text"] == ""
        assert result["source"] == "gemini_unavailable"

    async def test_returns_unavailable_when_gemini_service_missing(self):
        hybrid = MagicMock()
        hybrid.gemini = None
        wf = _make_workflow(hybrid_processor=hybrid)

        result = await wf._fallback_transcript_with_gemini(
            "https://www.youtube.com/watch?v=auJzb1D-fag",
            language="en",
            video_metadata=None,
        )

        assert result["text"] == ""
        assert result["source"] == "gemini_video_unavailable"

    async def test_returns_unavailable_when_gemini_not_available(self):
        gemini_service = MagicMock()
        gemini_service.is_available.return_value = False
        hybrid = MagicMock()
        hybrid.gemini = gemini_service
        wf = _make_workflow(hybrid_processor=hybrid)

        result = await wf._fallback_transcript_with_gemini(
            "https://www.youtube.com/watch?v=auJzb1D-fag",
            language="en",
            video_metadata=None,
        )

        assert result["source"] == "gemini_video_unavailable"

    async def test_success_via_youtube_url(self):
        import json
        gemini_result = MagicMock()
        gemini_result.success = True
        gemini_result.response = json.dumps({"transcript": "Gemini transcript", "segments": []})
        gemini_result.latency = 1.0
        gemini_result.error = None

        gemini_service = MagicMock()
        gemini_service.is_available.return_value = True
        gemini_service.process_youtube = AsyncMock(return_value=gemini_result)
        gemini_service.select_model = MagicMock()

        hybrid = MagicMock()
        hybrid.gemini = gemini_service
        hybrid.config.gemini.model_name = "gemini-2.5-flash"
        hybrid.config.model_routing = {}

        wf = _make_workflow(hybrid_processor=hybrid)

        result = await wf._fallback_transcript_with_gemini(
            "https://www.youtube.com/watch?v=auJzb1D-fag",
            language="en",
            video_metadata=None,
        )

        assert result["text"] == "Gemini transcript"
        assert result["source"] == "gemini_video"
