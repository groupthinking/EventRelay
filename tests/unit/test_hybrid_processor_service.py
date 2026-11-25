"""Unit tests for services/ai/hybrid_processor_service.py."""

from __future__ import annotations

import sys
import types as _types
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------
_SRC = Path(__file__).resolve().parents[2] / "src"
sys.path.insert(0, str(_SRC))

# ---------------------------------------------------------------------------
# Stub PIL only if not actually installable (avoids polluting sys.modules
# when Pillow is present, which would break other tests that need PIL.Image.new)
# ---------------------------------------------------------------------------
try:
    import PIL.Image  # noqa: F401  — triggers real load into sys.modules
except ImportError:
    _pil = _types.ModuleType("PIL")
    _pil_image = _types.ModuleType("PIL.Image")

    class _FakeImage:  # minimal stub used in type hints
        pass

    _pil.Image = _pil_image  # type: ignore[attr-defined]
    _pil_image.Image = _FakeImage  # type: ignore[attr-defined]
    sys.modules["PIL"] = _pil
    sys.modules["PIL.Image"] = _pil_image

# ---------------------------------------------------------------------------
# Stub google.generativeai so GeminiService can import without the real SDK
# ---------------------------------------------------------------------------
if "google" not in sys.modules:
    _google = _types.ModuleType("google")
    _google.__path__ = []  # type: ignore[attr-defined]
    sys.modules["google"] = _google

if "google.generativeai" not in sys.modules:
    _genai = _types.ModuleType("google.generativeai")
    sys.modules["google.generativeai"] = _genai
    sys.modules["google"].generativeai = _genai  # type: ignore[attr-defined]

# Stub transformers so import succeeds without the actual package
if "transformers" not in sys.modules:
    _transformers = _types.ModuleType("transformers")
    _transformers.pipeline = None  # type: ignore[attr-defined]
    sys.modules["transformers"] = _transformers

# Stub vertexai
if "vertexai" not in sys.modules:
    _vertexai = _types.ModuleType("vertexai")
    _vertexai.init = MagicMock()  # type: ignore[attr-defined]
    _vm = _types.ModuleType("vertexai.generative_models")
    _vm.GenerativeModel = MagicMock()  # type: ignore[attr-defined]
    _vm.Part = MagicMock()  # type: ignore[attr-defined]
    sys.modules["vertexai"] = _vertexai
    sys.modules["vertexai.generative_models"] = _vm

# ---------------------------------------------------------------------------
# Now import the module under test
# ---------------------------------------------------------------------------
# Clear previously-cached copies of the service modules so our stubs take
# effect.  Be careful NOT to delete the test module itself which pytest may
# already have registered under a "unit.test_..." key.
_SERVICE_PREFIXES = (
    "youtube_extension.services.ai.hybrid_processor_service",
    "youtube_extension.services.ai.gemini_service",
)
for _k in list(sys.modules):
    if any(_k == p or _k.startswith(p + ".") for p in _SERVICE_PREFIXES):
        del sys.modules[_k]

from youtube_extension.services.ai.gemini_service import GeminiConfig, GeminiResult
from youtube_extension.services.ai.hybrid_processor_service import (  # noqa: E402
    TASK_ROUTING_RULES,
    HybridConfig,
    HybridProcessorService,
    HybridResult,
    ProcessingMode,
    RoutingDecision,
    RoutingEngine,
    TaskType,
)

# ===========================================================================
# Helpers
# ===========================================================================


def _make_gemini_result(
    *,
    success: bool = True,
    response: str | None = "ok",
    latency: float = 0.05,
    model_name: str = "gemini-2.0-flash",
    backend: str = "api",
    error: str | None = None,
    usage_metadata: object | None = None,
) -> GeminiResult:
    return GeminiResult(
        success=success,
        response=response,
        latency=latency,
        model_name=model_name,
        backend=backend,
        error=error,
        usage_metadata=usage_metadata,
    )


def _make_mock_gemini_service(
    *,
    available: bool = False,
    result: GeminiResult | None = None,
) -> MagicMock:
    """Return a mock GeminiService whose async methods return *result*."""
    svc = MagicMock()
    svc.is_available.return_value = available
    svc.get_model_info.return_value = {"available": available, "model": "gemini-2.0-flash"}
    svc.select_model = MagicMock()
    svc.cleanup = AsyncMock()

    _result = result or _make_gemini_result()
    svc.process_image = AsyncMock(return_value=_result)
    svc.process_video = AsyncMock(return_value=_result)
    svc.process_audio = AsyncMock(return_value=_result)
    svc.process_text = AsyncMock(return_value=_result)
    svc.process_youtube = AsyncMock(return_value=_result)
    return svc


# ===========================================================================
# Enums
# ===========================================================================


class TestProcessingMode:
    def test_only_cloud_mode(self):
        assert ProcessingMode.CLOUD_ONLY.value == "cloud"
        assert len(ProcessingMode) == 1
        assert list(ProcessingMode) == [ProcessingMode.CLOUD_ONLY]


class TestTaskType:
    def test_expected_members_present(self):
        expected = {
            "YOUTUBE_ANALYSIS",
            "LONG_VIDEO_SUMMARY",
            "COMPLEX_REASONING",
            "MULTIMODAL_SEARCH",
            "BATCH_PROCESSING",
            "GENERAL_QA",
            "IMAGE_DESCRIPTION",
            "VIDEO_UNDERSTANDING",
            "AUDIO_ANALYSIS",
            "REAL_TIME_CAPTION",
            "TECHNICAL_DOCUMENT",
            "PRODUCT_DEMO",
            "PRIVACY_SENSITIVE",
            "LOW_LATENCY_QA",
        }
        actual = {m.name for m in TaskType}
        assert expected == actual

    def test_values_are_strings(self):
        for member in TaskType:
            assert isinstance(member.value, str)


# ===========================================================================
# Dataclasses
# ===========================================================================


class TestHybridConfig:
    def test_defaults(self):
        cfg = HybridConfig()
        assert cfg.default_mode == ProcessingMode.CLOUD_ONLY
        assert cfg.routing_threshold == 0.7
        assert cfg.enable_caching is True
        assert cfg.cache_ttl == 3600
        assert cfg.enable_metrics is True
        assert isinstance(cfg.gemini, GeminiConfig)

    def test_model_routing_populated_in_post_init(self):
        cfg = HybridConfig()
        assert cfg.model_routing is not None
        assert TaskType.YOUTUBE_ANALYSIS in cfg.model_routing
        assert cfg.model_routing[TaskType.YOUTUBE_ANALYSIS] == cfg.gemini.model_name

    def test_custom_gemini_config_preserved(self):
        g = GeminiConfig(model_name="gemini-1.5-pro")
        cfg = HybridConfig(gemini=g)
        assert cfg.gemini is g


class TestRoutingDecision:
    def test_fields(self):
        rd = RoutingDecision(
            mode=ProcessingMode.CLOUD_ONLY,
            confidence=0.9,
            reason="test",
            task_type=TaskType.GENERAL_QA,
        )
        assert rd.mode == ProcessingMode.CLOUD_ONLY
        assert rd.confidence == 0.9
        assert rd.reason == "test"
        assert rd.task_type == TaskType.GENERAL_QA


class TestHybridResult:
    def test_minimal_fields(self):
        gr = _make_gemini_result()
        hr = HybridResult(
            success=True,
            response="hello",
            latency=0.1,
            mode_used=ProcessingMode.CLOUD_ONLY,
        )
        assert hr.success is True
        assert hr.response == "hello"
        assert hr.from_cache is False
        assert hr.error is None
        assert hr.cloud_result is None
        assert hr.routing_decision is None

    def test_full_fields(self):
        gr = _make_gemini_result()
        rd = RoutingDecision(
            mode=ProcessingMode.CLOUD_ONLY,
            confidence=0.9,
            reason="r",
            task_type=TaskType.GENERAL_QA,
        )
        hr = HybridResult(
            success=True,
            response="data",
            latency=0.2,
            mode_used=ProcessingMode.CLOUD_ONLY,
            cloud_result=gr,
            routing_decision=rd,
            from_cache=True,
            error=None,
        )
        assert hr.cloud_result is gr
        assert hr.routing_decision is rd
        assert hr.from_cache is True


# ===========================================================================
# TASK_ROUTING_RULES constant
# ===========================================================================


class TestTaskRoutingRules:
    def test_all_task_types_covered(self):
        for task in TaskType:
            assert task in TASK_ROUTING_RULES

    def test_all_map_to_cloud_only(self):
        for task, mode in TASK_ROUTING_RULES.items():
            assert mode == ProcessingMode.CLOUD_ONLY, f"{task} should be CLOUD_ONLY"


# ===========================================================================
# RoutingEngine
# ===========================================================================


class TestRoutingEngine:
    def _engine(self) -> RoutingEngine:
        return RoutingEngine(HybridConfig())

    # decide_routing always returns CLOUD_ONLY ----------------------------------

    def test_decide_routing_returns_cloud_only(self):
        engine = self._engine()
        decision = engine.decide_routing("what is AI?")
        assert decision.mode == ProcessingMode.CLOUD_ONLY
        assert decision.confidence == 0.9
        assert "Gemini" in decision.reason

    def test_decide_routing_respects_provided_task_type(self):
        engine = self._engine()
        decision = engine.decide_routing("irrelevant", task_type=TaskType.BATCH_PROCESSING)
        assert decision.task_type == TaskType.BATCH_PROCESSING

    def test_decide_routing_infers_task_when_none_given(self):
        engine = self._engine()
        decision = engine.decide_routing("youtube video summary")
        assert decision.task_type == TaskType.YOUTUBE_ANALYSIS

    # _classify_task keyword branches ------------------------------------------

    def test_classify_privacy_sensitive(self):
        engine = self._engine()
        task = engine._classify_task("this is private data", {})
        assert task == TaskType.PRIVACY_SENSITIVE

    def test_classify_privacy_sensitive_confidential(self):
        engine = self._engine()
        assert engine._classify_task("confidential document", {}) == TaskType.PRIVACY_SENSITIVE

    def test_classify_privacy_sensitive_personal(self):
        engine = self._engine()
        assert engine._classify_task("personal health records", {}) == TaskType.PRIVACY_SENSITIVE

    def test_classify_real_time_caption(self):
        engine = self._engine()
        assert engine._classify_task("real-time transcription needed", {}) == TaskType.REAL_TIME_CAPTION

    def test_classify_real_time_live(self):
        engine = self._engine()
        assert engine._classify_task("live stream processing", {}) == TaskType.REAL_TIME_CAPTION

    def test_classify_youtube_analysis(self):
        engine = self._engine()
        assert engine._classify_task("youtube video on deep learning", {}) == TaskType.YOUTUBE_ANALYSIS

    def test_classify_complex_reasoning(self):
        engine = self._engine()
        assert engine._classify_task("analyze the complex system", {}) == TaskType.COMPLEX_REASONING

    def test_classify_complex_reasoning_detailed(self):
        engine = self._engine()
        assert engine._classify_task("detailed analysis required", {}) == TaskType.COMPLEX_REASONING

    def test_classify_audio_analysis_transcribe(self):
        engine = self._engine()
        assert engine._classify_task("please transcribe this recording", {}) == TaskType.AUDIO_ANALYSIS

    def test_classify_audio_analysis_podcast(self):
        engine = self._engine()
        assert engine._classify_task("podcast episode summary", {}) == TaskType.AUDIO_ANALYSIS

    def test_classify_technical_document_code(self):
        engine = self._engine()
        assert engine._classify_task("review this code documentation", {}) == TaskType.TECHNICAL_DOCUMENT

    def test_classify_technical_document_diagram(self):
        engine = self._engine()
        assert engine._classify_task("explain the diagram", {}) == TaskType.TECHNICAL_DOCUMENT

    def test_classify_fallback_general_qa(self):
        engine = self._engine()
        assert engine._classify_task("what is the capital of France?", {}) == TaskType.GENERAL_QA

    def test_classify_empty_prompt_general_qa(self):
        engine = self._engine()
        assert engine._classify_task("", {}) == TaskType.GENERAL_QA

    def test_classify_priority_privacy_over_youtube(self):
        """Privacy keywords take precedence because they are checked first."""
        engine = self._engine()
        # "private" + "youtube" — privacy check comes before youtube check
        task = engine._classify_task("private youtube channel", {})
        assert task == TaskType.PRIVACY_SENSITIVE


# ===========================================================================
# HybridProcessorService.__init__
# ===========================================================================


class TestHybridProcessorServiceInit:
    def _make_service(self, cfg: HybridConfig | None = None) -> HybridProcessorService:
        with patch("youtube_extension.services.ai.hybrid_processor_service.GeminiService") as MockGemini:
            mock_g = _make_mock_gemini_service()
            MockGemini.return_value = mock_g
            svc = HybridProcessorService(cfg)
            svc.gemini = mock_g
        return svc

    def test_default_config_created_when_none(self):
        svc = self._make_service()
        assert isinstance(svc.config, HybridConfig)

    def test_custom_config_stored(self):
        cfg = HybridConfig(routing_threshold=0.5)
        svc = self._make_service(cfg)
        assert svc.config is cfg

    def test_router_is_routing_engine(self):
        svc = self._make_service()
        assert isinstance(svc.router, RoutingEngine)

    def test_metrics_initial_values(self):
        svc = self._make_service()
        assert svc.metrics["total_requests"] == 0
        assert svc.metrics["cloud_requests"] == 0
        assert svc.metrics["cache_hits"] == 0
        assert svc.metrics["errors"] == 0
        assert svc.metrics["total_latency"] == 0.0

    def test_cache_enabled_by_default(self):
        svc = self._make_service()
        assert svc._cache is not None
        assert isinstance(svc._cache, dict)

    def test_cache_disabled_when_config_says_so(self):
        cfg = HybridConfig(enable_caching=False)
        svc = self._make_service(cfg)
        assert svc._cache is None


# ===========================================================================
# HybridProcessorService.is_available / get_metrics
# ===========================================================================


class TestServiceAvailabilityAndMetrics:
    def _svc(self, available: bool = False) -> HybridProcessorService:
        with patch("youtube_extension.services.ai.hybrid_processor_service.GeminiService") as Mg:
            mock_g = _make_mock_gemini_service(available=available)
            Mg.return_value = mock_g
            svc = HybridProcessorService()
            svc.gemini = mock_g
        return svc

    def test_is_available_delegates_to_gemini(self):
        svc = self._svc(available=True)
        assert svc.is_available() is True

    def test_is_not_available_when_gemini_unavailable(self):
        svc = self._svc(available=False)
        assert svc.is_available() is False

    def test_get_metrics_zero_requests(self):
        svc = self._svc()
        m = svc.get_metrics()
        assert m["total_requests"] == 0
        assert m["average_latency"] == 0.0
        assert m["cache_hit_rate"] == 0.0
        assert m["error_rate"] == 0.0

    def test_get_metrics_after_manual_increment(self):
        svc = self._svc()
        svc.metrics["total_requests"] = 10
        svc.metrics["cache_hits"] = 3
        svc.metrics["errors"] = 1
        svc.metrics["total_latency"] = 5.0
        m = svc.get_metrics()
        assert m["average_latency"] == pytest.approx(0.5)
        assert m["cache_hit_rate"] == pytest.approx(0.3)
        assert m["error_rate"] == pytest.approx(0.1)


# ===========================================================================
# HybridProcessorService._get_cache_key
# ===========================================================================


class TestGetCacheKey:
    def _svc(self) -> HybridProcessorService:
        with patch("youtube_extension.services.ai.hybrid_processor_service.GeminiService") as Mg:
            mock_g = _make_mock_gemini_service()
            Mg.return_value = mock_g
            svc = HybridProcessorService()
            svc.gemini = mock_g
        return svc

    def test_same_inputs_same_key(self):
        svc = self._svc()
        k1 = svc._get_cache_key("input.txt", "prompt")
        k2 = svc._get_cache_key("input.txt", "prompt")
        assert k1 == k2

    def test_different_prompt_different_key(self):
        svc = self._svc()
        k1 = svc._get_cache_key("file.mp4", "summarise")
        k2 = svc._get_cache_key("file.mp4", "describe")
        assert k1 != k2

    def test_different_input_different_key(self):
        svc = self._svc()
        k1 = svc._get_cache_key("a.mp4", "prompt")
        k2 = svc._get_cache_key("b.mp4", "prompt")
        assert k1 != k2


# ===========================================================================
# HybridProcessorService.process – Gemini unavailable
# ===========================================================================


class TestProcessGeminiUnavailable:
    async def test_unavailable_returns_failure(self):
        cfg = HybridConfig(enable_caching=False)
        with patch("youtube_extension.services.ai.hybrid_processor_service.GeminiService") as Mg:
            mock_g = _make_mock_gemini_service(available=False)
            Mg.return_value = mock_g
            svc = HybridProcessorService(cfg)
            svc.gemini = mock_g

        result = await svc.process("input", "describe the personality")

        assert result.success is False
        assert result.response is None
        assert result.mode_used == ProcessingMode.CLOUD_ONLY
        assert result.error == "Gemini not available or not initialized"
        assert svc.metrics["errors"] == 1
        mock_g.process_text.assert_not_awaited()
        mock_g.process_image.assert_not_awaited()
        mock_g.process_video.assert_not_awaited()
        mock_g.process_audio.assert_not_awaited()
        mock_g.process_youtube.assert_not_awaited()


# ===========================================================================
# HybridProcessorService.process – live Gemini path
# ===========================================================================


class TestProcessLiveGeminiPath:
    """When Gemini is available, process() calls the matching Gemini method."""

    def _svc(self, gemini_result: GeminiResult | None = None) -> HybridProcessorService:
        res = gemini_result or _make_gemini_result()
        cfg = HybridConfig(enable_caching=False)
        with patch("youtube_extension.services.ai.hybrid_processor_service.GeminiService") as Mg:
            mock_g = _make_mock_gemini_service(available=True, result=res)
            Mg.return_value = mock_g
            svc = HybridProcessorService(cfg)
            svc.gemini = mock_g
        return svc

    async def test_process_routes_youtube_url(self):
        svc = self._svc()
        await svc.process("https://www.youtube.com/watch?v=abc", "summarize")
        svc.gemini.process_youtube.assert_awaited_once()

    async def test_process_routes_mp4_video(self):
        svc = self._svc()
        await svc.process("/data/video.mp4", "describe")
        svc.gemini.process_video.assert_awaited_once()

    async def test_process_routes_mp3_audio(self):
        svc = self._svc()
        await svc.process("/data/audio.mp3", "transcribe")
        svc.gemini.process_audio.assert_awaited_once()

    async def test_process_routes_wav_audio(self):
        svc = self._svc()
        await svc.process("/data/audio.wav", "transcribe")
        svc.gemini.process_audio.assert_awaited_once()

    async def test_process_routes_mov_video(self):
        svc = self._svc()
        await svc.process("/data/clip.mov", "analyse")
        svc.gemini.process_video.assert_awaited_once()

    async def test_process_routes_avi_video(self):
        svc = self._svc()
        await svc.process("/data/clip.avi", "analyse")
        svc.gemini.process_video.assert_awaited_once()

    async def test_process_routes_text_string_with_spaces(self):
        svc = self._svc()
        await svc.process("This is a long text input with spaces", "summarize")
        svc.gemini.process_text.assert_awaited_once()

    async def test_process_routes_multiline_text(self):
        svc = self._svc()
        await svc.process("line one\nline two", "summarize")
        svc.gemini.process_text.assert_awaited_once()

    async def test_process_gemini_failure_returns_hybrid_result_with_error(self):
        failed_result = _make_gemini_result(success=False, response=None, error="API error")
        svc = self._svc(gemini_result=failed_result)
        result = await svc.process("input.mp4", "describe")
        assert result.success is False
        assert result.error == "API error"

    async def test_process_exception_returns_error_result(self):
        cfg = HybridConfig(enable_caching=False)
        with patch("youtube_extension.services.ai.hybrid_processor_service.GeminiService") as Mg:
            mock_g = _make_mock_gemini_service(available=True)
            mock_g.process_video = AsyncMock(side_effect=RuntimeError("network error"))
            Mg.return_value = mock_g
            svc = HybridProcessorService(cfg)
            svc.gemini = mock_g

        result = await svc.process("crash.mp4", "analyse")
        assert result.success is False
        assert "network error" in result.error
        assert svc.metrics["errors"] == 1

    async def test_process_selects_model_from_routing(self):
        svc = self._svc()
        await svc.process("clip.mp4", "describe", task_type=TaskType.VIDEO_UNDERSTANDING)
        svc.gemini.select_model.assert_called_once_with(svc.config.gemini.model_name)

    async def test_process_uses_explicit_model_name_kwarg(self):
        svc = self._svc()
        await svc.process("clip.mp4", "describe", model_name="gemini-1.5-pro")
        svc.gemini.select_model.assert_called_with("gemini-1.5-pro")

    async def test_process_passes_video_metadata(self):
        svc = self._svc()
        meta = {"start_offset": 10, "end_offset": 60}
        await svc.process("video.mp4", "clip analysis", video_metadata=meta)
        call_kwargs = svc.gemini.process_video.call_args
        assert call_kwargs.kwargs.get("video_metadata") == meta or meta in call_kwargs.args


# ===========================================================================
# HybridProcessorService.cleanup
# ===========================================================================


class TestCleanup:
    async def test_cleanup_clears_cache(self):
        with patch("youtube_extension.services.ai.hybrid_processor_service.GeminiService") as Mg:
            mock_g = _make_mock_gemini_service()
            Mg.return_value = mock_g
            svc = HybridProcessorService()
            svc.gemini = mock_g
            svc._cache["key"] = MagicMock()
            await svc.cleanup()
            assert svc._cache == {}
            svc.gemini.cleanup.assert_awaited_once()

    async def test_cleanup_with_no_cache(self):
        cfg = HybridConfig(enable_caching=False)
        with patch("youtube_extension.services.ai.hybrid_processor_service.GeminiService") as Mg:
            mock_g = _make_mock_gemini_service()
            Mg.return_value = mock_g
            svc = HybridProcessorService(cfg)
            svc.gemini = mock_g
            # Should not raise even when _cache is None
            await svc.cleanup()
            svc.gemini.cleanup.assert_awaited_once()


# ===========================================================================
# _update_metrics internal helper
# ===========================================================================


class TestUpdateMetrics:
    def _svc(self) -> HybridProcessorService:
        with patch("youtube_extension.services.ai.hybrid_processor_service.GeminiService") as Mg:
            mock_g = _make_mock_gemini_service()
            Mg.return_value = mock_g
            svc = HybridProcessorService()
            svc.gemini = mock_g
        return svc

    def test_update_metrics_increments_cloud_requests(self):
        svc = self._svc()
        svc._update_metrics(0.25)
        assert svc.metrics["cloud_requests"] == 1

    def test_update_metrics_accumulates_latency(self):
        svc = self._svc()
        svc._update_metrics(0.1)
        svc._update_metrics(0.2)
        assert svc.metrics["total_latency"] == pytest.approx(0.3)


# ===========================================================================
# Edge cases for _call_gemini routing
# ===========================================================================


class TestCallGeminiRouting:
    """Tests for the _call_gemini branching logic via process()."""

    def _svc(self, result: GeminiResult | None = None) -> HybridProcessorService:
        res = result or _make_gemini_result()
        cfg = HybridConfig(enable_caching=False)
        with patch("youtube_extension.services.ai.hybrid_processor_service.GeminiService") as Mg:
            mock_g = _make_mock_gemini_service(available=True, result=res)
            Mg.return_value = mock_g
            svc = HybridProcessorService(cfg)
            svc.gemini = mock_g
        return svc

    async def test_webm_routed_to_video(self):
        svc = self._svc()
        await svc.process("clip.webm", "analyse")
        svc.gemini.process_video.assert_awaited_once()

    async def test_mkv_routed_to_video(self):
        svc = self._svc()
        await svc.process("clip.mkv", "analyse")
        svc.gemini.process_video.assert_awaited_once()

    async def test_m4a_routed_to_audio(self):
        svc = self._svc()
        await svc.process("track.m4a", "transcribe")
        svc.gemini.process_audio.assert_awaited_once()

    async def test_flac_routed_to_audio(self):
        svc = self._svc()
        await svc.process("song.flac", "transcribe")
        svc.gemini.process_audio.assert_awaited_once()

    async def test_long_text_over_255_chars_routed_to_text(self):
        svc = self._svc()
        long_text = "word " * 60  # 300+ chars, has spaces
        await svc.process(long_text, "summarize")
        svc.gemini.process_text.assert_awaited_once()

    async def test_short_ambiguous_string_falls_through_to_image(self):
        """A short string with no spaces/newlines and <= 255 chars that does
        not match any extension is sent to process_image as a fallback."""
        svc = self._svc()
        await svc.process("unknownpath", "describe")
        svc.gemini.process_image.assert_awaited_once()

    async def test_path_object_routed_based_on_extension(self):
        svc = self._svc()
        await svc.process(Path("/data/video.mp4"), "describe")
        svc.gemini.process_video.assert_awaited_once()

    async def test_model_routing_uses_task_type_model(self):
        svc = self._svc()
        svc.config.model_routing[TaskType.AUDIO_ANALYSIS] = "gemini-special"
        await svc.process("audio.mp3", "transcribe", task_type=TaskType.AUDIO_ANALYSIS)
        svc.gemini.select_model.assert_called_with("gemini-special")
