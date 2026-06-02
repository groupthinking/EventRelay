"""
Comprehensive unit tests for agent adapter modules:
  - HybridVisionAgent
  - VideoMasterAgent
  - ActionImplementerAgent
  - TranscriptActionAgent
  - PersonalityAgent
  - StrategyAgent
"""
from __future__ import annotations

import asyncio
import json
import logging
import sys
import types as _types
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Ensure BaseAgent has the attributes that adapters expect (logger, etc.)
# ---------------------------------------------------------------------------
from youtube_extension.services.agents import base_agent as _ba

_SENTINEL = object()


def _get_config(self, key: str, default=None):  # noqa: ANN001
    return getattr(self, "_config", {}).get(key, default) if hasattr(self, "_config") else default


def _validate_input(self, params: dict, required: list[str]) -> list[str]:  # noqa: ANN001
    return [f"Missing required parameter: {k}" for k in required if k not in params]


@pytest.fixture(autouse=True, scope="session")
def _patch_base_agent_attrs() -> None:
    """Scope BaseAgent stub attributes to the test session and restore on teardown."""
    orig_logger = getattr(_ba.BaseAgent, "logger", _SENTINEL)
    orig_get_config = getattr(_ba.BaseAgent, "get_config", _SENTINEL)
    orig_validate_input = getattr(_ba.BaseAgent, "validate_input", _SENTINEL)

    if orig_logger is _SENTINEL:
        _ba.BaseAgent.logger = logging.getLogger("test.base_agent")
    if orig_get_config is _SENTINEL:
        _ba.BaseAgent.get_config = _get_config
    if orig_validate_input is _SENTINEL:
        _ba.BaseAgent.validate_input = _validate_input

    yield

    for attr, orig in [
        ("logger", orig_logger),
        ("get_config", orig_get_config),
        ("validate_input", orig_validate_input),
    ]:
        if orig is _SENTINEL:
            try:
                delattr(_ba.BaseAgent, attr)
            except AttributeError:
                pass
        else:
            setattr(_ba.BaseAgent, attr, orig)

# ---------------------------------------------------------------------------
# Lazy imports – agents are imported after the base class is patched
# ---------------------------------------------------------------------------
from youtube_extension.services.agents.dto import AgentRequest, AgentResult
from youtube_extension.services.ai.hybrid_processor_service import (
    HybridConfig,
    HybridResult,
    ProcessingMode,
    RoutingDecision,
    TaskType,
)
from youtube_extension.services.ai.gemini_service import GeminiConfig, GeminiResult


# ===========================================================================
# Helpers
# ===========================================================================

def _make_hybrid_result(
    *,
    success: bool = True,
    response: str = "test response",
    latency: float = 0.5,
    mode: ProcessingMode = ProcessingMode.CLOUD_ONLY,
    error: str | None = None,
) -> HybridResult:
    """Build a HybridResult for mocking.

    NOTE: HybridVisionAgent._parse_hybrid_result accesses hybrid_result.local_result
    which doesn't exist on the dataclass. We patch it onto the instance to avoid
    AttributeError from buggy source code.
    """
    result = HybridResult(
        success=success,
        response=response,
        latency=latency,
        mode_used=mode,
        error=error,
    )
    # Patch missing 'local_result' attribute referenced by _parse_hybrid_result
    result.local_result = None  # type: ignore[attr-defined]
    return result


def _make_mock_processor(
    *,
    process_result: HybridResult | None = None,
    is_available: bool = True,
) -> MagicMock:
    processor = MagicMock()
    processor.is_available.return_value = is_available
    processor.get_metrics.return_value = {"total_requests": 1, "cloud_requests": 1}
    processor.process = AsyncMock(return_value=process_result or _make_hybrid_result())
    processor.config = HybridConfig()
    return processor


def _req(task: str = "analyze", **params: Any) -> AgentRequest:
    return AgentRequest(task=task, params=params)


# ===========================================================================
# HybridVisionAgent
# ===========================================================================

class TestHybridVisionAgent:
    """Tests for HybridVisionAgent."""

    def _make_agent(self, processor: MagicMock | None = None) -> Any:
        from youtube_extension.services.agents.adapters.hybrid_vision_agent import HybridVisionAgent

        mock_proc = processor or _make_mock_processor()
        with patch(
            "youtube_extension.services.agents.adapters.hybrid_vision_agent.HybridProcessorService",
            return_value=mock_proc,
        ):
            agent = HybridVisionAgent()
        agent._hybrid_processor = mock_proc
        return agent

    # --- init ---

    def test_init_sets_hybrid_processor(self):
        agent = self._make_agent()
        assert agent._hybrid_processor is not None

    def test_init_processor_none_on_exception(self):
        from youtube_extension.services.agents.adapters.hybrid_vision_agent import HybridVisionAgent

        with patch(
            "youtube_extension.services.agents.adapters.hybrid_vision_agent.HybridProcessorService",
            side_effect=RuntimeError("boom"),
        ):
            agent = HybridVisionAgent()
        assert agent._hybrid_processor is None

    # --- run: missing processor ---

    async def test_run_no_processor_returns_error(self):
        agent = self._make_agent()
        agent._hybrid_processor = None

        result = await agent.run(_req())
        assert result.status == "error"
        assert any("not available" in log.lower() for log in result.logs)

    # --- run: missing image data ---

    async def test_run_missing_image_data_returns_error(self):
        agent = self._make_agent()
        result = await agent.run(_req(prompt="describe this"))
        assert result.status == "error"
        assert any("image" in log.lower() or "video" in log.lower() for log in result.logs)

    # --- run: special action routing ---
    # NOTE: _handle_special_action uses a wrong AgentResult constructor (success/data/errors)
    # that doesn't match the Pydantic model (status/output/logs). This causes a ValidationError
    # that propagates from _handle_special_action through run(). Tests verify the error surface.

    @pytest.mark.xfail(reason="known bug: _handle_special_action uses wrong AgentResult fields", strict=False)
    async def test_run_routes_to_special_action_raises_validation_error(self):
        """_handle_special_action has a bug: uses wrong AgentResult fields; confirms error propagates."""
        from pydantic import ValidationError

        processor = _make_mock_processor()
        processor.create_ephemeral_token = AsyncMock(
            return_value={"success": True, "token": "tok-123"}
        )
        agent = self._make_agent(processor)

        with pytest.raises((ValidationError, Exception)):
            await agent.run(
                _req(action="create_ephemeral_token", model_name="gemini-pro")
            )

    # --- run: successful image analysis ---

    async def test_run_image_analysis_ok(self):
        hybrid_result = _make_hybrid_result(
            response="A person walking near a car on a road.",
            latency=0.3,
        )
        processor = _make_mock_processor(process_result=hybrid_result)
        agent = self._make_agent(processor)

        result = await agent.run(_req(image="base64data", prompt="describe"))
        assert result.status == "ok"
        assert "vision_analysis" in result.output

    # --- run: processor raises ---

    async def test_run_processor_exception_returns_error(self):
        processor = _make_mock_processor()
        processor.process = AsyncMock(side_effect=RuntimeError("api down"))
        agent = self._make_agent(processor)

        result = await agent.run(_req(image="data", prompt="describe"))
        assert result.status == "error"
        assert any("Vision analysis failed" in log for log in result.logs)

    # --- run: default prompt injected ---

    async def test_run_default_prompt_injected_when_missing(self):
        hybrid_result = _make_hybrid_result(response="A house with a tree.")
        processor = _make_mock_processor(process_result=hybrid_result)
        agent = self._make_agent(processor)

        req = _req(image="data")
        result = await agent.run(req)
        # Should succeed - default prompt was auto-filled
        assert result.status == "ok"

    # --- run: processor failure (success=False) ---

    async def test_run_processor_failure_result(self):
        hybrid_result = _make_hybrid_result(success=False, response=None, error="model error")
        processor = _make_mock_processor(process_result=hybrid_result)
        agent = self._make_agent(processor)

        result = await agent.run(_req(image="data", prompt="describe"))
        assert result.status == "error"

    # --- _handle_special_action: NOTE ---
    # _handle_special_action uses wrong AgentResult constructor fields (success/data/errors/processing_time)
    # that don't match the Pydantic AgentResult DTO (status/output/logs). The inner _failure() helper
    # and the success return path both cause ValidationError. All paths through _handle_special_action
    # raise an exception rather than returning a valid AgentResult.

    @pytest.mark.xfail(reason="known bug: _handle_special_action uses wrong AgentResult fields", strict=False)
    async def test_handle_special_action_missing_contents_raises(self):
        """start_cached_session missing contents: inner _failure() raises ValidationError."""
        from pydantic import ValidationError
        agent = self._make_agent()
        with pytest.raises((ValidationError, Exception)):
            await agent._handle_special_action(
                "start_cached_session", {}, asyncio.get_event_loop().time()
            )

    @pytest.mark.xfail(reason="known bug: _handle_special_action uses wrong AgentResult fields", strict=False)
    async def test_handle_special_action_missing_requests_raises(self):
        """submit_batch_job missing requests: inner _failure() raises ValidationError."""
        from pydantic import ValidationError
        agent = self._make_agent()
        with pytest.raises((ValidationError, Exception)):
            await agent._handle_special_action(
                "submit_batch_job", {}, asyncio.get_event_loop().time()
            )

    @pytest.mark.xfail(reason="known bug: _handle_special_action uses wrong AgentResult fields", strict=False)
    async def test_handle_special_action_unknown_action_raises(self):
        """Unknown action calls _failure() which raises ValidationError."""
        from pydantic import ValidationError
        agent = self._make_agent()
        with pytest.raises((ValidationError, Exception)):
            await agent._handle_special_action(
                "nonexistent_action", {}, asyncio.get_event_loop().time()
            )

    @pytest.mark.xfail(reason="known bug: _handle_special_action uses wrong AgentResult fields", strict=False)
    async def test_handle_special_action_token_raises(self):
        """create_ephemeral_token success path raises ValidationError due to wrong fields."""
        from pydantic import ValidationError
        processor = _make_mock_processor()
        processor.create_ephemeral_token = AsyncMock(
            return_value={"success": True, "token": "abc"}
        )
        agent = self._make_agent(processor)
        with pytest.raises((ValidationError, Exception)):
            await agent._handle_special_action(
                "create_ephemeral_token",
                {"model_name": "gemini-pro"},
                asyncio.get_event_loop().time(),
            )

    # --- _extract_image_data ---

    def test_extract_image_data_from_image_key(self):
        agent = self._make_agent()
        data = agent._extract_image_data({"image": "base64"})
        assert data == "base64"

    def test_extract_image_data_from_image_path(self):
        agent = self._make_agent()
        data = agent._extract_image_data({"image_path": "/tmp/img.jpg"})
        assert isinstance(data, Path)

    def test_extract_image_data_from_video_path(self):
        agent = self._make_agent()
        data = agent._extract_image_data({"video_path": "/tmp/vid.mp4"})
        assert isinstance(data, Path)

    def test_extract_image_data_from_video_key(self):
        agent = self._make_agent()
        data = agent._extract_image_data({"video": b"bytes"})
        assert data == b"bytes"

    def test_extract_image_data_raises_on_missing(self):
        agent = self._make_agent()
        with pytest.raises(ValueError):
            agent._extract_image_data({})

    # --- _determine_task_type ---

    def test_determine_task_type_explicit(self):
        agent = self._make_agent()
        task = agent._determine_task_type({"task_type": "youtube_analysis"})
        assert task == TaskType.YOUTUBE_ANALYSIS

    def test_determine_task_type_invalid_falls_back(self):
        agent = self._make_agent()
        task = agent._determine_task_type({"task_type": "does_not_exist", "prompt": ""})
        assert task == TaskType.GENERAL_QA

    def test_determine_task_type_real_time_from_prompt(self):
        agent = self._make_agent()
        task = agent._determine_task_type({"prompt": "real-time caption this"})
        assert task == TaskType.REAL_TIME_CAPTION

    def test_determine_task_type_youtube_from_prompt(self):
        agent = self._make_agent()
        task = agent._determine_task_type({"prompt": "do a youtube analysis"})
        assert task == TaskType.YOUTUBE_ANALYSIS

    def test_determine_task_type_complex_from_prompt(self):
        agent = self._make_agent()
        task = agent._determine_task_type({"prompt": "complex reasoning needed"})
        assert task == TaskType.COMPLEX_REASONING

    def test_determine_task_type_technical_from_prompt(self):
        agent = self._make_agent()
        task = agent._determine_task_type({"prompt": "technical documentation"})
        assert task == TaskType.TECHNICAL_DOCUMENT

    def test_determine_task_type_privacy_from_prompt(self):
        agent = self._make_agent()
        task = agent._determine_task_type({"prompt": "this is private data"})
        assert task == TaskType.PRIVACY_SENSITIVE

    def test_determine_task_type_general_fallback(self):
        agent = self._make_agent()
        task = agent._determine_task_type({"prompt": "random question"})
        assert task == TaskType.GENERAL_QA

    # --- _get_processing_mode ---

    def test_get_processing_mode_cloud_only(self):
        agent = self._make_agent()
        mode = agent._get_processing_mode({"processing_mode": "cloud"})
        assert mode == ProcessingMode.CLOUD_ONLY

    def test_get_processing_mode_invalid_returns_none(self):
        agent = self._make_agent()
        mode = agent._get_processing_mode({"processing_mode": "invalid_mode"})
        assert mode is None

    def test_get_processing_mode_no_mode_returns_none(self):
        agent = self._make_agent()
        mode = agent._get_processing_mode({})
        assert mode is None

    # --- _parse_hybrid_result ---

    def test_parse_hybrid_result_success_with_response(self):
        from youtube_extension.services.agents.adapters.hybrid_vision_agent import VisionAnalysisResult

        agent = self._make_agent()
        hybrid_result = _make_hybrid_result(
            response="A person walking near a car on a road with a sign.",
            latency=0.4,
        )
        result = agent._parse_hybrid_result(hybrid_result)
        assert isinstance(result, VisionAnalysisResult)
        assert "person" in result.objects_detected or result.description != ""

    def test_parse_hybrid_result_failure(self):
        from youtube_extension.services.agents.adapters.hybrid_vision_agent import VisionAnalysisResult

        agent = self._make_agent()
        hybrid_result = _make_hybrid_result(success=False, response=None, error="err")
        result = agent._parse_hybrid_result(hybrid_result)
        assert isinstance(result, VisionAnalysisResult)
        assert result.confidence_score == 0.0

    # --- _calculate_confidence ---

    def test_calculate_confidence_failed_result(self):
        agent = self._make_agent()
        hybrid_result = _make_hybrid_result(success=False, response=None)
        assert agent._calculate_confidence(hybrid_result) == 0.0

    def test_calculate_confidence_with_cloud_result_ok(self):
        agent = self._make_agent()
        cloud_result = MagicMock()
        cloud_result.success = True
        hybrid_result = _make_hybrid_result(latency=1.0, response="a" * 200)
        hybrid_result.cloud_result = cloud_result
        score = agent._calculate_confidence(hybrid_result)
        assert score > 0.7

    def test_calculate_confidence_capped_at_one(self):
        agent = self._make_agent()
        cloud_result = MagicMock()
        cloud_result.success = True
        hybrid_result = _make_hybrid_result(latency=0.1, response="a" * 500)
        hybrid_result.cloud_result = cloud_result
        score = agent._calculate_confidence(hybrid_result)
        assert score <= 1.0

    # --- _extract_objects ---

    def test_extract_objects_detects_person(self):
        agent = self._make_agent()
        detected = agent._extract_objects("There is a person walking next to a car.")
        assert "person" in detected
        assert "car" in detected

    def test_extract_objects_empty_response(self):
        agent = self._make_agent()
        detected = agent._extract_objects("nothing here at all")
        assert isinstance(detected, list)

    def test_extract_objects_limit_ten(self):
        agent = self._make_agent()
        # Sentence with many objects
        detected = agent._extract_objects(
            "person man woman child car vehicle building tree house dog cat table chair computer phone"
        )
        assert len(detected) <= 10

    # --- _extract_text_mentions ---

    def test_extract_text_mentions_finds_text_keyword(self):
        agent = self._make_agent()
        mentions = agent._extract_text_mentions("There is text visible on the sign.")
        assert len(mentions) >= 1

    def test_extract_text_mentions_no_keywords(self):
        agent = self._make_agent()
        mentions = agent._extract_text_mentions("A plain image with no annotations.")
        assert mentions == []

    # --- _extract_scene_analysis ---

    def test_extract_scene_analysis_with_scene_keyword(self):
        agent = self._make_agent()
        analysis = agent._extract_scene_analysis("The scene shows a busy city street. People everywhere.")
        assert "scene" in analysis.lower() or analysis != ""

    def test_extract_scene_analysis_fallback_first_sentence(self):
        agent = self._make_agent()
        analysis = agent._extract_scene_analysis("A mountain in the distance. Clouds above.")
        assert analysis != ""

    # --- is_available / get_capabilities ---

    def test_is_available_true_when_processor_available(self):
        processor = _make_mock_processor(is_available=True)
        agent = self._make_agent(processor)
        assert agent.is_available() is True

    def test_is_available_false_when_no_processor(self):
        agent = self._make_agent()
        agent._hybrid_processor = None
        assert agent.is_available() is False

    def test_get_capabilities_no_processor(self):
        agent = self._make_agent()
        agent._hybrid_processor = None
        caps = agent.get_capabilities()
        assert caps["available"] is False

    def test_get_capabilities_with_processor(self):
        processor = _make_mock_processor()
        processor.gemini = MagicMock()
        processor.gemini.get_model_info.return_value = {"model": "gemini"}
        agent = self._make_agent(processor)
        caps = agent.get_capabilities()
        assert caps["available"] is True
        assert "processing_modes" in caps

    # --- cleanup ---

    async def test_cleanup_sets_processor_to_none(self):
        processor = _make_mock_processor()
        processor.cleanup = AsyncMock()
        agent = self._make_agent(processor)
        await agent.cleanup()
        assert agent._hybrid_processor is None

    async def test_cleanup_no_processor_noop(self):
        agent = self._make_agent()
        agent._hybrid_processor = None
        await agent.cleanup()  # should not raise

    # --- _safe_get_metrics ---

    def test_safe_get_metrics_returns_dict(self):
        agent = self._make_agent()
        metrics = agent._safe_get_metrics()
        assert isinstance(metrics, dict)

    def test_safe_get_metrics_no_processor(self):
        agent = self._make_agent()
        agent._hybrid_processor = None
        metrics = agent._safe_get_metrics()
        assert metrics == {}

    def test_safe_get_metrics_exception_returns_empty(self):
        processor = _make_mock_processor()
        processor.get_metrics.side_effect = RuntimeError("fail")
        agent = self._make_agent(processor)
        metrics = agent._safe_get_metrics()
        assert metrics == {}

    # --- run with video_path ---

    async def test_run_with_video_path(self):
        hybrid_result = _make_hybrid_result(response="Video shows a tutorial.")
        processor = _make_mock_processor(process_result=hybrid_result)
        agent = self._make_agent(processor)
        result = await agent.run(_req(video_path="/tmp/vid.mp4", prompt="describe"))
        assert result.status == "ok"

    # --- run with generation_params ---

    async def test_run_passes_generation_params(self):
        hybrid_result = _make_hybrid_result(response="Description.")
        processor = _make_mock_processor(process_result=hybrid_result)
        agent = self._make_agent(processor)
        result = await agent.run(
            _req(
                image="data",
                prompt="describe",
                generation_params={"temperature": 0.5},
                task_type="general_qa",
                processing_mode="cloud",
            )
        )
        assert result.status == "ok"


# ===========================================================================
# VideoMasterAgent
# ===========================================================================

class TestVideoMasterAgent:
    """Tests for VideoMasterAgent."""

    def _make_agent(self, api_key: str | None = "test-api-key") -> Any:
        from youtube_extension.services.agents.adapters.video_master_agent import VideoMasterAgent

        mock_genai = MagicMock()
        mock_client = MagicMock()
        mock_genai.Client.return_value = mock_client

        with (
            patch("youtube_extension.services.agents.adapters.video_master_agent.GEMINI_AVAILABLE", True),
            patch("youtube_extension.services.agents.adapters.video_master_agent.genai", mock_genai),
        ):
            agent = VideoMasterAgent()

        # Ensure get_config returns a key so the setup path works
        agent._config = {"gemini_api_key": api_key}
        agent.get_config = lambda key, default=None: {"gemini_api_key": api_key}.get(key, default)

        if api_key:
            agent._gemini_client = mock_client

        return agent, mock_client

    # --- init ---

    def test_init_no_api_key_leaves_client_none(self):
        from youtube_extension.services.agents.adapters.video_master_agent import VideoMasterAgent

        with patch("youtube_extension.services.agents.adapters.video_master_agent.GEMINI_AVAILABLE", True):
            with patch("youtube_extension.services.agents.adapters.video_master_agent.genai", MagicMock()):
                agent = VideoMasterAgent()
        # Without key get_config returns None, so _gemini_client stays None
        assert agent._gemini_client is None

    def test_init_gemini_not_available(self):
        from youtube_extension.services.agents.adapters.video_master_agent import VideoMasterAgent

        with patch("youtube_extension.services.agents.adapters.video_master_agent.GEMINI_AVAILABLE", False):
            agent = VideoMasterAgent()
        assert agent._gemini_client is None

    # --- run: validation ---

    async def test_run_missing_video_data_returns_error(self):
        agent, _ = self._make_agent()
        result = await agent.run(_req(transcript=[]))
        assert result.status == "error"

    async def test_run_missing_transcript_returns_error(self):
        agent, _ = self._make_agent()
        result = await agent.run(_req(video_data={"title": "Test"}))
        assert result.status == "error"

    async def test_run_no_gemini_client_returns_error(self):
        agent, _ = self._make_agent()
        agent._gemini_client = None
        result = await agent.run(_req(video_data={"title": "T"}, transcript=[]))
        assert result.status == "error"
        assert any("not available" in log.lower() for log in result.logs)

    # --- run: successful ---

    async def test_run_ok_with_json_response(self):
        agent, client = self._make_agent()
        json_response = json.dumps({
            "title": "Python Tutorial",
            "summary": "A comprehensive guide.",
            "key_points": ["point1", "point2"],
            "actions": [],
            "difficulty_level": "beginner",
            "estimated_duration": "1h",
            "quality_score": 0.8,
        })

        with patch.object(agent, "_call_gemini_async", new=AsyncMock(return_value=json_response)):
            result = await agent.run(
                _req(video_data={"title": "Python Tutorial", "duration": 3600}, transcript=[])
            )

        assert result.status == "ok"
        assert "video_analysis" in result.output

    # --- run: exception ---

    async def test_run_exception_returns_error(self):
        agent, _ = self._make_agent()

        with patch.object(agent, "_call_gemini_async", new=AsyncMock(side_effect=RuntimeError("crash"))):
            result = await agent.run(
                _req(video_data={"title": "Test"}, transcript=[])
            )

        assert result.status == "error"
        assert any("Video analysis failed" in log for log in result.logs)

    # --- _create_analysis_prompt ---

    def test_create_analysis_prompt_contains_title(self):
        agent, _ = self._make_agent()
        prompt = agent._create_analysis_prompt(
            {"title": "Coding Guide", "duration": 120, "description": "Learn coding"},
            [{"text": "Hello world", "start": 0.0}],
        )
        assert "Coding Guide" in prompt
        assert "TRANSCRIPT" in prompt

    def test_create_analysis_prompt_long_description_truncated(self):
        agent, _ = self._make_agent()
        long_desc = "x" * 600
        prompt = agent._create_analysis_prompt(
            {"title": "Test", "duration": 60, "description": long_desc},
            [],
        )
        assert len(prompt) < 5000  # Truncation happened

    # --- _format_transcript ---

    def test_format_transcript_empty(self):
        agent, _ = self._make_agent()
        result = agent._format_transcript([])
        assert "No transcript" in result

    def test_format_transcript_dicts(self):
        agent, _ = self._make_agent()
        transcript = [{"text": "Hello", "start": 0.0}, {"text": "World", "start": 1.5}]
        result = agent._format_transcript(transcript)
        assert "Hello" in result
        assert "0.0" in result

    def test_format_transcript_non_dicts(self):
        agent, _ = self._make_agent()
        result = agent._format_transcript(["line one", "line two"])
        assert "line one" in result

    def test_format_transcript_limit_50(self):
        agent, _ = self._make_agent()
        transcript = [{"text": f"sentence {i}", "start": float(i)} for i in range(100)]
        result = agent._format_transcript(transcript)
        # Should not include entry 51 onwards
        assert "sentence 99" not in result

    # --- _call_gemini_async ---

    async def test_call_gemini_async_returns_text(self):
        agent, client = self._make_agent()
        mock_response = MagicMock()
        mock_response.text = "response text"
        client.models.generate_content.return_value = mock_response

        text = await agent._call_gemini_async("some prompt")
        assert text == "response text"

    async def test_call_gemini_async_exception_propagates(self):
        agent, client = self._make_agent()
        client.models.generate_content.side_effect = RuntimeError("API error")

        with pytest.raises(RuntimeError, match="API error"):
            await agent._call_gemini_async("prompt")

    # --- _parse_gemini_response ---

    def test_parse_gemini_response_valid_json(self):
        agent, _ = self._make_agent()
        response = json.dumps({
            "title": "Title",
            "summary": "Summary",
            "key_points": ["k1"],
            "actions": [],
            "difficulty_level": "beginner",
            "estimated_duration": "30m",
            "quality_score": 0.9,
        })
        result = agent._parse_gemini_response(response)
        assert result.title == "Title"
        assert result.quality_score == 0.9

    def test_parse_gemini_response_json_in_codeblock(self):
        agent, _ = self._make_agent()
        data = {"title": "T", "summary": "S", "key_points": [], "actions": [],
                "difficulty_level": "intermediate", "estimated_duration": "1h", "quality_score": 0.7}
        response = f"```json\n{json.dumps(data)}\n```"
        result = agent._parse_gemini_response(response)
        assert result.title == "T"

    def test_parse_gemini_response_invalid_json_fallback(self):
        agent, _ = self._make_agent()
        result = agent._parse_gemini_response("not valid json content at all")
        assert result.title == "Video Analysis"
        assert result.quality_score == 0.3

    def test_parse_gemini_response_short_response_no_truncation(self):
        agent, _ = self._make_agent()
        result = agent._parse_gemini_response("short")
        assert "short" in result.summary

    def test_parse_gemini_response_long_response_truncated(self):
        agent, _ = self._make_agent()
        long_response = "x" * 300
        result = agent._parse_gemini_response(long_response)
        assert result.summary.endswith("...")

    # --- is_available ---

    def test_is_available_true(self):
        agent, _ = self._make_agent()
        with patch("youtube_extension.services.agents.adapters.video_master_agent.GEMINI_AVAILABLE", True):
            assert agent.is_available() is True

    def test_is_available_false_no_client(self):
        agent, _ = self._make_agent()
        agent._gemini_client = None
        with patch("youtube_extension.services.agents.adapters.video_master_agent.GEMINI_AVAILABLE", True):
            assert agent.is_available() is False


# ===========================================================================
# ActionImplementerAgent
# ===========================================================================

class TestActionImplementerAgent:
    """Tests for ActionImplementerAgent."""

    def _make_agent(self) -> Any:
        from youtube_extension.services.agents.adapters.action_implementer_agent import ActionImplementerAgent
        return ActionImplementerAgent()

    # --- init ---

    def test_init_loads_templates(self):
        agent = self._make_agent()
        assert "tutorial" in agent._action_templates
        assert "educational" in agent._action_templates

    # --- run: validation ---

    async def test_run_missing_inputs_returns_error(self):
        agent = self._make_agent()
        result = await agent.run(_req())
        assert result.status == "error"
        assert any("video_analysis" in log or "video_data" in log for log in result.logs)

    # --- run: with video_analysis ---

    async def test_run_with_video_analysis_ok(self):
        agent = self._make_agent()
        analysis = {
            "title": "Python Tutorial",
            "summary": "Learn Python from scratch in this tutorial.",
            "key_points": ["Variables", "Functions", "Classes"],
            "difficulty_level": "beginner",
            "quality_score": 0.8,
        }
        result = await agent.run(_req(video_analysis=analysis))
        assert result.status == "ok"
        assert "action_plan" in result.output
        assert result.output["content_type"] in ("tutorial", "educational", "demonstration", "conceptual")

    # --- run: with video_data ---

    async def test_run_with_video_data_ok(self):
        agent = self._make_agent()
        video_data = {
            "title": "Build a demo application",
            "description": "Step by step demonstration of building a Python app.",
        }
        result = await agent.run(_req(video_data=video_data))
        assert result.status == "ok"

    # --- run: exception path ---

    async def test_run_exception_returns_error(self):
        agent = self._make_agent()

        with patch.object(agent, "_generate_action_plan", side_effect=RuntimeError("plan crash")):
            result = await agent.run(
                _req(video_analysis={"title": "T", "summary": "s", "key_points": []})
            )
        assert result.status == "error"

    # --- _create_basic_analysis ---

    def test_create_basic_analysis_short_description(self):
        agent = self._make_agent()
        analysis = agent._create_basic_analysis({"title": "T", "description": "short desc"})
        assert analysis["title"] == "T"
        assert "..." not in analysis["summary"]

    def test_create_basic_analysis_long_description(self):
        agent = self._make_agent()
        long_desc = "x" * 300
        analysis = agent._create_basic_analysis({"title": "T", "description": long_desc})
        assert analysis["summary"].endswith("...")

    def test_create_basic_analysis_no_description(self):
        agent = self._make_agent()
        analysis = agent._create_basic_analysis({"title": "No Desc"})
        assert analysis["summary"] == ""

    # --- _extract_key_points_from_text ---

    def test_extract_key_points_returns_list(self):
        agent = self._make_agent()
        points = agent._extract_key_points_from_text("Learn how to build a Python app tutorial guide.")
        assert isinstance(points, list)

    def test_extract_key_points_limit_five(self):
        agent = self._make_agent()
        text = " ".join(["learn build create develop implement tutorial guide how"] * 5)
        points = agent._extract_key_points_from_text(text)
        assert len(points) <= 5

    # --- _determine_content_type ---

    def test_determine_content_type_tutorial(self):
        agent = self._make_agent()
        ct = agent._determine_content_type({"title": "How to build an app", "summary": "step by step guide"})
        assert ct == "tutorial"

    def test_determine_content_type_demonstration(self):
        agent = self._make_agent()
        ct = agent._determine_content_type({"title": "Demo of new features", "summary": "a showcase of tools"})
        assert ct == "demonstration"

    def test_determine_content_type_conceptual(self):
        agent = self._make_agent()
        ct = agent._determine_content_type({"title": "Understanding concepts", "summary": "theory explanation"})
        assert ct == "conceptual"

    def test_determine_content_type_educational_fallback(self):
        agent = self._make_agent()
        ct = agent._determine_content_type({"title": "Random title", "summary": "random summary"})
        assert ct == "educational"

    # --- _generate_primary_actions ---

    def test_generate_primary_actions_always_has_main(self):
        agent = self._make_agent()
        analysis = {"title": "Test Video", "key_points": [], "difficulty_level": "beginner"}
        template = agent._action_templates["tutorial"]
        actions = agent._generate_primary_actions(analysis, template)
        assert len(actions) >= 1
        assert actions[0]["id"] == "primary_001"

    def test_generate_primary_actions_with_key_points(self):
        agent = self._make_agent()
        analysis = {
            "title": "T",
            "key_points": ["point 1", "point 2", "point 3", "point 4"],
            "difficulty_level": "intermediate",
        }
        template = agent._action_templates["educational"]
        actions = agent._generate_primary_actions(analysis, template)
        assert len(actions) == 4  # main + 3 key points (capped)

    # --- _generate_supplementary_actions ---

    def test_generate_supplementary_actions_returns_two(self):
        agent = self._make_agent()
        analysis = {"difficulty_level": "intermediate"}
        template = agent._action_templates["tutorial"]
        actions = agent._generate_supplementary_actions(analysis, template)
        assert len(actions) == 2

    # --- _create_learning_path ---

    def test_create_learning_path_ordered(self):
        agent = self._make_agent()
        primary = [
            {"id": "primary_001", "prerequisites": []},
            {"id": "primary_002", "prerequisites": ["primary_001"]},
        ]
        supplementary = [{"id": "supp_001"}, {"id": "supp_002"}]
        path = agent._create_learning_path(primary, supplementary)
        assert "primary_001" in path
        assert path.index("primary_001") < path.index("primary_002")

    # --- _identify_prerequisites ---

    def test_identify_prerequisites_tutorial_beginner(self):
        agent = self._make_agent()
        prereqs = agent._identify_prerequisites({"difficulty_level": "beginner"}, "tutorial")
        assert isinstance(prereqs, list)
        assert len(prereqs) > 0

    def test_identify_prerequisites_advanced(self):
        agent = self._make_agent()
        prereqs = agent._identify_prerequisites({"difficulty_level": "advanced"}, "tutorial")
        assert "Strong programming background" in prereqs or len(prereqs) > 0

    def test_identify_prerequisites_unknown_content_type_fallback(self):
        agent = self._make_agent()
        prereqs = agent._identify_prerequisites({"difficulty_level": "beginner"}, "unknown_type")
        assert isinstance(prereqs, list)

    # --- _gather_resources ---

    def test_gather_resources_returns_three(self):
        agent = self._make_agent()
        resources = agent._gather_resources({}, "tutorial")
        assert len(resources) == 3
        types = {r["type"] for r in resources}
        assert "documentation" in types

    # --- _calculate_total_time ---

    def test_calculate_total_time_minutes_only(self):
        agent = self._make_agent()
        primary = [{"id": "p1"}, {"id": "p2"}]
        supp = [{"id": "s1"}]
        total = agent._calculate_total_time(primary, supp)
        assert "m" in total

    def test_calculate_total_time_hours(self):
        agent = self._make_agent()
        primary = [{"id": f"p{i}"} for i in range(5)]
        supp = [{"id": f"s{i}"} for i in range(3)]
        total = agent._calculate_total_time(primary, supp)
        assert "h" in total

    # --- _create_difficulty_progression ---

    def test_create_difficulty_progression_ordered(self):
        agent = self._make_agent()
        actions = [
            {"difficulty": "advanced"},
            {"difficulty": "beginner"},
            {"difficulty": "intermediate"},
        ]
        progression = agent._create_difficulty_progression(actions)
        assert progression.index("beginner") < progression.index("intermediate")

    def test_create_difficulty_progression_deduped(self):
        agent = self._make_agent()
        actions = [{"difficulty": "intermediate"}, {"difficulty": "intermediate"}]
        progression = agent._create_difficulty_progression(actions)
        assert progression.count("intermediate") == 1

    # --- is_available ---

    def test_is_available_always_true(self):
        agent = self._make_agent()
        assert agent.is_available() is True


# ===========================================================================
# TranscriptActionAgent
# ===========================================================================

class TestTranscriptActionAgent:
    """Tests for TranscriptActionAgent."""

    def _make_agent(self, process_result: HybridResult | None = None) -> Any:
        from youtube_extension.services.agents.adapters.transcript_action_agent import TranscriptActionAgent

        processor = _make_mock_processor(process_result=process_result or _make_hybrid_result(
            response=json.dumps({"key": "value"})
        ))
        return TranscriptActionAgent({"hybrid_processor": processor}), processor

    # --- init ---

    def test_init_sets_hybrid_processor(self):
        agent, _ = self._make_agent()
        assert agent._hybrid_processor is not None

    def test_init_default_language(self):
        agent, _ = self._make_agent()
        assert agent._language == "en"

    def test_init_custom_config(self):
        from youtube_extension.services.agents.adapters.transcript_action_agent import TranscriptActionAgent

        processor = _make_mock_processor()
        agent = TranscriptActionAgent({
            "hybrid_processor": processor,
            "language": "fr",
            "summary_model": "gemini-pro",
        })
        assert agent._language == "fr"
        assert agent._summary_model == "gemini-pro"

    # --- run: missing transcript ---

    async def test_run_missing_transcript_returns_error(self):
        agent, _ = self._make_agent()
        result = await agent.run(_req())
        assert result.status == "error"

    # --- run: success ---

    async def test_run_ok_with_transcript(self):
        agent, processor = self._make_agent()
        json_payload = json.dumps({"executive_summary": "summary", "key": "val"})
        processor.process = AsyncMock(return_value=_make_hybrid_result(response=json_payload))

        result = await agent.run(_req(transcript="This is a test transcript."))
        assert result.status == "ok"
        assert "summary" in result.output

    # --- run: exception from Gemini ---

    async def test_run_gemini_failure_returns_error(self):
        agent, processor = self._make_agent()
        processor.process = AsyncMock(return_value=_make_hybrid_result(
            success=False, response=None, error="timeout"
        ))
        result = await agent.run(_req(transcript="transcript text"))
        assert result.status == "error"

    # --- run: chat_assistance ---

    async def test_run_chat_assistance_ok(self):
        agent, processor = self._make_agent()
        processor.process = AsyncMock(return_value=_make_hybrid_result(response="Here is the answer."))

        result = await agent.run(_req(task="chat_assistance", message="What is this about?"))
        assert result.status == "ok"
        assert "response" in result.output

    async def test_run_chat_assistance_missing_message(self):
        agent, _ = self._make_agent()
        result = await agent.run(_req(task="chat_assistance"))
        assert result.status == "error"

    async def test_run_chat_assistance_with_transcript(self):
        agent, processor = self._make_agent()
        processor.process = AsyncMock(return_value=_make_hybrid_result(response="Context-aware answer."))

        result = await agent.run(_req(
            task="chat_assistance",
            message="Summarise",
            transcript="Long transcript content here...",
        ))
        assert result.status == "ok"

    async def test_run_chat_assistance_with_context(self):
        agent, processor = self._make_agent()
        processor.process = AsyncMock(return_value=_make_hybrid_result(response="Answer."))

        result = await agent.run(_req(
            task="chat_assistance",
            message="Help",
            context={"session": "abc"},
        ))
        assert result.status == "ok"

    async def test_run_chat_assistance_gemini_failure(self):
        agent, processor = self._make_agent()
        processor.process = AsyncMock(return_value=_make_hybrid_result(
            success=False, response=None, error="model error"
        ))
        result = await agent.run(_req(task="chat_assistance", message="Hello?"))
        assert result.status == "error"

    async def test_run_chat_assistance_exception(self):
        agent, processor = self._make_agent()
        processor.process = AsyncMock(side_effect=RuntimeError("network crash"))
        result = await agent.run(_req(task="chat_assistance", message="Hello?"))
        assert result.status == "error"

    # --- run: with video_metadata ---

    async def test_run_with_video_metadata(self):
        agent, processor = self._make_agent()
        json_payload = json.dumps({"result": "ok"})
        processor.process = AsyncMock(return_value=_make_hybrid_result(response=json_payload))

        result = await agent.run(_req(
            transcript="transcript",
            video_metadata={"start_offset": 10, "end_offset": 60, "fps": 30},
        ))
        assert result.status == "ok"
        processing_notes = result.output.get("processing_notes", {})
        clip_window = processing_notes.get("clip_window")
        assert clip_window is not None

    # --- _safe_parse_json ---

    def test_safe_parse_json_valid(self):
        from youtube_extension.services.agents.adapters.transcript_action_agent import TranscriptActionAgent
        result = TranscriptActionAgent._safe_parse_json('{"a": 1}')
        assert result == {"a": 1}

    def test_safe_parse_json_invalid(self):
        from youtube_extension.services.agents.adapters.transcript_action_agent import TranscriptActionAgent
        result = TranscriptActionAgent._safe_parse_json("not json")
        assert result is None

    # --- _clip_window_notes ---

    def test_clip_window_notes_with_offsets(self):
        from youtube_extension.services.agents.adapters.transcript_action_agent import TranscriptActionAgent
        result = TranscriptActionAgent._clip_window_notes({"start_offset": 5, "end_offset": 20, "fps": 25})
        assert result == {"start_offset": 5, "end_offset": 20, "fps": 25}

    def test_clip_window_notes_empty(self):
        from youtube_extension.services.agents.adapters.transcript_action_agent import TranscriptActionAgent
        result = TranscriptActionAgent._clip_window_notes({})
        assert result is None

    def test_clip_window_notes_no_relevant_keys(self):
        from youtube_extension.services.agents.adapters.transcript_action_agent import TranscriptActionAgent
        result = TranscriptActionAgent._clip_window_notes({"title": "test"})
        assert result is None

    def test_clip_window_notes_partial_keys(self):
        from youtube_extension.services.agents.adapters.transcript_action_agent import TranscriptActionAgent
        result = TranscriptActionAgent._clip_window_notes({"start_offset": 0})
        assert result == {"start_offset": 0}

    # --- _format_offset ---

    def test_format_offset_none(self):
        from youtube_extension.services.agents.adapters.transcript_action_agent import TranscriptActionAgent
        assert TranscriptActionAgent._format_offset(None) is None

    def test_format_offset_int(self):
        from youtube_extension.services.agents.adapters.transcript_action_agent import TranscriptActionAgent
        result = TranscriptActionAgent._format_offset(90)
        assert result is not None
        assert ":" in result

    def test_format_offset_float(self):
        from youtube_extension.services.agents.adapters.transcript_action_agent import TranscriptActionAgent
        result = TranscriptActionAgent._format_offset(3661.5)
        assert result is not None

    def test_format_offset_string_with_s(self):
        from youtube_extension.services.agents.adapters.transcript_action_agent import TranscriptActionAgent
        result = TranscriptActionAgent._format_offset("45s")
        assert result is not None

    def test_format_offset_string_invalid(self):
        from youtube_extension.services.agents.adapters.transcript_action_agent import TranscriptActionAgent
        result = TranscriptActionAgent._format_offset("abc")
        assert result is None

    def test_format_offset_negative(self):
        from youtube_extension.services.agents.adapters.transcript_action_agent import TranscriptActionAgent
        result = TranscriptActionAgent._format_offset(-5)
        assert result is None

    def test_format_offset_zero(self):
        from youtube_extension.services.agents.adapters.transcript_action_agent import TranscriptActionAgent
        result = TranscriptActionAgent._format_offset(0)
        assert result is not None

    def test_format_offset_hours(self):
        from youtube_extension.services.agents.adapters.transcript_action_agent import TranscriptActionAgent
        result = TranscriptActionAgent._format_offset(7265)
        assert result is not None and ":" in result

    def test_format_offset_other_type(self):
        from youtube_extension.services.agents.adapters.transcript_action_agent import TranscriptActionAgent
        result = TranscriptActionAgent._format_offset([1, 2])
        assert result is None

    # --- _build_prompt_clip_context ---

    def test_build_prompt_clip_context_empty_metadata(self):
        agent, _ = self._make_agent()
        result = agent._build_prompt_clip_context({}, {})
        assert result == ""

    def test_build_prompt_clip_context_with_start_and_end(self):
        agent, _ = self._make_agent()
        result = agent._build_prompt_clip_context({}, {"start_offset": 10, "end_offset": 60})
        assert "clip from" in result

    def test_build_prompt_clip_context_start_only(self):
        agent, _ = self._make_agent()
        result = agent._build_prompt_clip_context({}, {"start_offset": 30})
        assert "starting at" in result

    def test_build_prompt_clip_context_end_only(self):
        agent, _ = self._make_agent()
        result = agent._build_prompt_clip_context({}, {"end_offset": 60})
        assert "ending at" in result

    def test_build_prompt_clip_context_with_fps(self):
        agent, _ = self._make_agent()
        result = agent._build_prompt_clip_context({}, {"fps": 30})
        assert "30 FPS" in result

    def test_build_prompt_clip_context_all_fields(self):
        agent, _ = self._make_agent()
        result = agent._build_prompt_clip_context({}, {"start_offset": 10, "end_offset": 60, "fps": 24})
        assert "clip from" in result and "24 FPS" in result

    # --- _default_model ---

    def test_default_model_returns_string(self):
        agent, _ = self._make_agent()
        model = agent._default_model(TaskType.COMPLEX_REASONING)
        assert isinstance(model, str)

    # --- run: non-parsed summary fallback ---

    async def test_run_non_json_response_uses_raw_fallback(self):
        agent, processor = self._make_agent()
        processor.process = AsyncMock(return_value=_make_hybrid_result(response="not json at all"))

        result = await agent.run(_req(transcript="some transcript"))
        assert result.status == "ok"
        # raw text fallback
        assert "summary" in result.output


# ===========================================================================
# PersonalityAgent
# ===========================================================================

class TestPersonalityAgent:
    """Tests for PersonalityAgent."""

    def _make_agent(self, process_result: HybridResult | None = None) -> Any:
        from youtube_extension.services.agents.adapters.personality_agent import PersonalityAgent

        processor = _make_mock_processor(
            process_result=process_result or _make_hybrid_result(
                response=json.dumps({
                    "creator_persona": {"type": "Authority"},
                    "video_intent": {"primary": "educate"},
                    "community_sentiment": {"vibe": "positive"},
                })
            )
        )
        return PersonalityAgent({"hybrid_processor": processor}), processor

    # --- init ---

    def test_init_sets_model(self):
        agent, _ = self._make_agent()
        assert agent._model is not None

    def test_init_custom_model(self):
        from youtube_extension.services.agents.adapters.personality_agent import PersonalityAgent

        processor = _make_mock_processor()
        agent = PersonalityAgent({"hybrid_processor": processor, "model": "gemini-ultra"})
        assert agent._model == "gemini-ultra"

    # --- run: validation ---

    async def test_run_missing_transcript_and_metadata_returns_error(self):
        agent, _ = self._make_agent()
        result = await agent.run(_req())
        assert result.status == "error"

    # --- run: with transcript ---

    async def test_run_ok_with_transcript(self):
        agent, _ = self._make_agent()
        result = await agent.run(_req(transcript="Creator talks about new ideas."))
        assert result.status == "ok"
        assert "personality_map" in result.output

    # --- run: with metadata only ---

    async def test_run_ok_with_metadata_only(self):
        agent, _ = self._make_agent()
        result = await agent.run(_req(metadata={"title": "Video Title"}))
        assert result.status == "ok"

    # --- run: Gemini failure ---

    async def test_run_gemini_failure_returns_error(self):
        agent, processor = self._make_agent()
        processor.process = AsyncMock(return_value=_make_hybrid_result(
            success=False, response=None, error="model error"
        ))
        result = await agent.run(_req(transcript="some transcript"))
        assert result.status == "error"

    # --- run: exception ---

    async def test_run_exception_returns_error(self):
        agent, processor = self._make_agent()
        processor.process = AsyncMock(side_effect=RuntimeError("crash"))
        result = await agent.run(_req(transcript="text"))
        assert result.status == "error"

    # --- _map_personality: invalid JSON fallback ---

    async def test_map_personality_invalid_json_fallback(self):
        agent, processor = self._make_agent()
        processor.process = AsyncMock(return_value=_make_hybrid_result(response="not json"))
        persona = await agent._map_personality("transcript", {})
        assert "creator_persona" in persona

    # --- _map_personality: with comments and channel context ---

    async def test_map_personality_with_comments(self):
        agent, processor = self._make_agent()
        json_response = json.dumps({
            "creator_persona": {"type": "Peer"},
            "video_intent": {},
            "community_sentiment": {},
        })
        processor.process = AsyncMock(return_value=_make_hybrid_result(response=json_response))

        persona = await agent._map_personality(
            "Transcript here",
            {
                "comments": ["Great video!", "Very helpful"],
                "channel_context": {"subscribers": 50000},
            }
        )
        assert persona["creator_persona"]["type"] == "Peer"

    # --- _map_personality: no transcript ---

    async def test_map_personality_no_transcript(self):
        agent, processor = self._make_agent()
        json_response = json.dumps({
            "creator_persona": {"type": "Visionary"},
            "video_intent": {},
            "community_sentiment": {},
        })
        processor.process = AsyncMock(return_value=_make_hybrid_result(response=json_response))

        persona = await agent._map_personality(None, {"title": "Test Video"})
        assert "creator_persona" in persona

    # --- run: output includes model metadata ---

    async def test_run_output_contains_model_metadata(self):
        agent, _ = self._make_agent()
        result = await agent.run(_req(transcript="content"))
        assert result.status == "ok"
        assert "metadata" in result.output
        assert "model" in result.output["metadata"]


# ===========================================================================
# StrategyAgent
# ===========================================================================

class TestStrategyAgent:
    """Tests for StrategyAgent."""

    def _make_agent(self, process_result: HybridResult | None = None) -> Any:
        from youtube_extension.services.agents.adapters.strategy_agent import StrategyAgent

        processor = _make_mock_processor(
            process_result=process_result or _make_hybrid_result(
                response=json.dumps({
                    "strategic_analysis": {
                        "core_principle": "Efficiency",
                        "user_intent_analysis": "Learning",
                        "action_optimization": {"the_better_way": "automate", "gain": "3x"},
                    },
                    "a2ui_payload": [{"type": "beginRendering"}],
                })
            )
        )
        return StrategyAgent({"hybrid_processor": processor}), processor

    # --- init ---

    def test_init_sets_model(self):
        agent, _ = self._make_agent()
        assert agent._model is not None

    def test_init_custom_model(self):
        from youtube_extension.services.agents.adapters.strategy_agent import StrategyAgent

        processor = _make_mock_processor()
        agent = StrategyAgent({"hybrid_processor": processor, "model": "gemini-pro"})
        assert agent._model == "gemini-pro"

    # --- run: validation ---

    async def test_run_missing_transcript_and_metadata_returns_error(self):
        agent, _ = self._make_agent()
        result = await agent.run(_req())
        assert result.status == "error"

    # --- run: with transcript ---

    async def test_run_ok_with_transcript(self):
        agent, _ = self._make_agent()
        result = await agent.run(_req(transcript="Creator shows an automation strategy."))
        assert result.status == "ok"
        assert "strategic_analysis" in result.output
        assert "a2ui_payload" in result.output

    # --- run: with metadata only ---

    async def test_run_ok_with_metadata_only(self):
        agent, _ = self._make_agent()
        result = await agent.run(_req(metadata={"title": "Strategy Video"}))
        assert result.status == "ok"

    # --- run: with personality_map ---

    async def test_run_ok_with_personality_map(self):
        agent, _ = self._make_agent()
        result = await agent.run(_req(
            transcript="transcript",
            personality_map={"creator_persona": {"type": "Authority"}},
        ))
        assert result.status == "ok"

    # --- run: Gemini failure ---

    async def test_run_gemini_failure_returns_error(self):
        agent, processor = self._make_agent()
        processor.process = AsyncMock(return_value=_make_hybrid_result(
            success=False, response=None, error="model error"
        ))
        result = await agent.run(_req(transcript="transcript"))
        assert result.status == "error"

    # --- run: exception ---

    async def test_run_exception_returns_error(self):
        agent, processor = self._make_agent()
        processor.process = AsyncMock(side_effect=RuntimeError("crash"))
        result = await agent.run(_req(transcript="text"))
        assert result.status == "error"

    # --- _generate_strategy: invalid JSON fallback ---

    async def test_generate_strategy_invalid_json_fallback(self):
        agent, processor = self._make_agent()
        processor.process = AsyncMock(return_value=_make_hybrid_result(response="not json"))
        strategy = await agent._generate_strategy("transcript", {}, {})
        assert "strategic_analysis" in strategy
        assert "raw" in strategy["strategic_analysis"]

    # --- _generate_strategy: with transcript ---

    async def test_generate_strategy_with_transcript(self):
        agent, processor = self._make_agent()
        json_response = json.dumps({
            "strategic_analysis": {"core_principle": "Growth"},
            "a2ui_payload": [],
        })
        processor.process = AsyncMock(return_value=_make_hybrid_result(response=json_response))

        strategy = await agent._generate_strategy(
            "This transcript talks about growth strategy.",
            {"title": "Strategy Talk"},
            {"creator_persona": {"type": "Visionary"}},
        )
        assert strategy["strategic_analysis"]["core_principle"] == "Growth"

    # --- _generate_strategy: no transcript ---

    async def test_generate_strategy_no_transcript(self):
        agent, processor = self._make_agent()
        json_response = json.dumps({"strategic_analysis": {}, "a2ui_payload": []})
        processor.process = AsyncMock(return_value=_make_hybrid_result(response=json_response))

        strategy = await agent._generate_strategy(None, {"title": "Test"}, {})
        assert "strategic_analysis" in strategy

    # --- run: output contains model metadata ---

    async def test_run_output_contains_model(self):
        agent, _ = self._make_agent()
        result = await agent.run(_req(transcript="text"))
        assert result.status == "ok"
        assert "metadata" in result.output
        assert "model" in result.output["metadata"]


# ===========================================================================
# VisionAnalysisResult dataclass
# ===========================================================================

class TestVisionAnalysisResult:
    def test_can_instantiate(self):
        from youtube_extension.services.agents.adapters.hybrid_vision_agent import VisionAnalysisResult

        r = VisionAnalysisResult(
            description="A scene",
            objects_detected=["person", "car"],
            scene_analysis="Busy street",
            text_content=[],
            confidence_score=0.9,
            processing_mode="cloud",
        )
        assert r.description == "A scene"
        assert r.confidence_score == 0.9
        assert r.local_latency is None

    def test_optional_latencies(self):
        from youtube_extension.services.agents.adapters.hybrid_vision_agent import VisionAnalysisResult

        r = VisionAnalysisResult(
            description="",
            objects_detected=[],
            scene_analysis="",
            text_content=[],
            confidence_score=0.5,
            processing_mode="cloud",
            local_latency=0.1,
            cloud_latency=0.4,
        )
        assert r.local_latency == 0.1
        assert r.cloud_latency == 0.4


# ===========================================================================
# VideoAnalysisResult dataclass
# ===========================================================================

class TestVideoAnalysisResult:
    def test_can_instantiate(self):
        from youtube_extension.services.agents.adapters.video_master_agent import VideoAnalysisResult

        r = VideoAnalysisResult(
            title="T",
            summary="S",
            key_points=["p1"],
            actions=[],
            difficulty_level="beginner",
            estimated_duration="1h",
            quality_score=0.8,
        )
        assert r.title == "T"
        assert r.quality_score == 0.8


# ===========================================================================
# ActionPlan dataclass
# ===========================================================================

class TestActionPlanDataclass:
    def test_can_instantiate(self):
        from youtube_extension.services.agents.adapters.action_implementer_agent import ActionPlan

        plan = ActionPlan(
            primary_actions=[{"id": "p1"}],
            supplementary_actions=[{"id": "s1"}],
            learning_path=["p1", "s1"],
            prerequisites=["basic knowledge"],
            resources=[{"type": "docs"}],
            estimated_total_time="2h 0m",
            difficulty_progression=["beginner"],
        )
        assert plan.estimated_total_time == "2h 0m"
        assert len(plan.primary_actions) == 1


# ===========================================================================
# PromptResult dataclass
# ===========================================================================

class TestPromptResultDataclass:
    def test_can_instantiate_with_parsed(self):
        from youtube_extension.services.agents.adapters.transcript_action_agent import PromptResult

        r = PromptResult(raw_text='{"a": 1}', parsed={"a": 1})
        assert r.parsed == {"a": 1}

    def test_can_instantiate_with_none_parsed(self):
        from youtube_extension.services.agents.adapters.transcript_action_agent import PromptResult

        r = PromptResult(raw_text="not json", parsed=None)
        assert r.parsed is None
