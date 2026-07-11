from types import SimpleNamespace

import pytest

from youtube_extension.services.workflows.transcript_action_workflow import TranscriptActionWorkflow
from src.shared.youtube import RobustYouTubeMetadata
from youtube_extension.services.ai.speech_to_text_service import SpeechToTextResult
from youtube_extension.services.agents.adapters.agent_orchestrator import OrchestrationResult
from youtube_extension.services.agents.dto import AgentResult


class _StubYouTubeService:
    def __init__(self, metadata: RobustYouTubeMetadata, transcript: dict[str, object]):
        self._metadata = metadata
        self._transcript = transcript

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def get_video_metadata(self, video_url: str) -> RobustYouTubeMetadata:
        return self._metadata

    async def get_transcript(self, video_id: str, language: str = "en") -> dict[str, object]:
        return self._transcript


class _StubSpeechService:
    def __init__(self, result: SpeechToTextResult):
        self._result = result
        self.calls = 0

    async def transcribe_youtube_video(self, video_url: str, *, language_code: str = "en") -> SpeechToTextResult:
        self.calls += 1
        return self._result


class _StubGemini:
    def __init__(self, available: bool = False):
        self._available = available

    def is_available(self) -> bool:
        return self._available

    async def process_youtube(self, *args, **kwargs):  # pragma: no cover - not used in tests
        raise AssertionError("Gemini should not be invoked in these tests")


class _StubHybridProcessor:
    def __init__(self):
        self.gemini = _StubGemini(available=False)
        self.config = SimpleNamespace(
            model_routing={},
            gemini=SimpleNamespace(model_name="mock-model"),
        )


class _StubOrchestrator:
    def __init__(self):
        self.calls: list[dict[str, object]] = []

    async def execute_task(self, task_type: str, input_data: dict[str, object], agent_configs=None) -> OrchestrationResult:
        self.calls.append({
            "task_type": task_type,
            "input": input_data,
        })
        return OrchestrationResult(
            success=True,
            results={
                "transcript_action": AgentResult(status="ok", output={"summary": "done"}, logs=[])
            },
            errors=[],
            total_processing_time=0.25,
            agents_used=["transcript_action"],
        )


def _sample_metadata() -> RobustYouTubeMetadata:
    return RobustYouTubeMetadata(
        video_id="abc123",
        title="Sample",
        description="",
        channel_id="channel",
        channel_title="Channel",
        published_at="2025-01-01T00:00:00Z",
        duration="PT10M",
        view_count=100,
        like_count=10,
        comment_count=1,
        thumbnail_urls={"default": "http://example.com/thumb.jpg"},
        tags=[],
        category_id="22",
        default_language="en",
        default_audio_language="en",
        live_broadcast_content="none",
        transcript_available=True,
        transcript_segments=10,
        source_api="youtube_data_api_v3",
    )


@pytest.mark.asyncio
async def test_transcript_action_workflow_uses_primary_transcript():
    metadata = _sample_metadata()
    yt_service = _StubYouTubeService(metadata, {"text": "primary transcript", "segments": []})
    orchestrator = _StubOrchestrator()

    workflow = TranscriptActionWorkflow(
        youtube_service_factory=lambda: yt_service,
        orchestrator=orchestrator,
        hybrid_processor=_StubHybridProcessor(),
        speech_service=_StubSpeechService(
            SpeechToTextResult(False, "", [], 0.0, error="should not be used", source="test")
        ),
    )

    result = await workflow.run("https://youtu.be/abc123", language="en")

    assert result["success"] is True
    assert result["transcript"]["text"] == "primary transcript"
    assert orchestrator.calls != []
    assert orchestrator.calls[0]["input"]["transcript"] == "primary transcript"


@pytest.mark.asyncio
async def test_transcript_action_workflow_falls_back_to_speech():
    metadata = _sample_metadata()
    yt_service = _StubYouTubeService(metadata, {"text": "", "segments": []})
    orchestrator = _StubOrchestrator()
    speech_result = SpeechToTextResult(True, "speech transcript", [], 1.0)

    workflow = TranscriptActionWorkflow(
        youtube_service_factory=lambda: yt_service,
        orchestrator=orchestrator,
        hybrid_processor=_StubHybridProcessor(),
        speech_service=_StubSpeechService(speech_result),
    )

    result = await workflow.run("https://youtu.be/abc123", language="en")

    assert result["success"] is True
    assert result["transcript"]["text"] == "speech transcript"
    assert result["transcript"]["source"] == "speech_to_text_v2"
    assert orchestrator.calls, "Orchestrator should have been invoked"


@pytest.mark.asyncio
async def test_transcript_action_workflow_returns_structured_error():
    metadata = _sample_metadata()
    yt_service = _StubYouTubeService(metadata, {"text": "", "segments": []})
    orchestrator = _StubOrchestrator()
    speech_result = SpeechToTextResult(False, "", [], 0.1, error="speech failure", source="speech_to_text_v2")

    workflow = TranscriptActionWorkflow(
        youtube_service_factory=lambda: yt_service,
        orchestrator=orchestrator,
        hybrid_processor=_StubHybridProcessor(),
        speech_service=_StubSpeechService(speech_result),
    )

    result = await workflow.run("https://youtu.be/abc123", language="en")

    assert result["success"] is False
    assert result["errors"], "Failure response should include errors"
    assert result["outputs"] == {}
    assert orchestrator.calls == [], "Orchestrator should not run when transcript generation fails"
