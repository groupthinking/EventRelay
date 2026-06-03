"""Unit tests for integrations/cloud_ai/integrator.py."""

from __future__ import annotations

import sys
import types as _types
from pathlib import Path

import pytest

_SRC = Path(__file__).resolve().parents[2] / "src"
sys.path.insert(0, str(_SRC))


def _inject_stub(name: str, path: str) -> None:
    if name not in sys.modules:
        stub = _types.ModuleType(name)
        stub.__path__ = [path]
        stub.__package__ = name
        sys.modules[name] = stub


_inject_stub("youtube_extension.integrations", str(_SRC / "youtube_extension/integrations"))

for _key in [k for k in list(sys.modules.keys()) if "youtube_extension" in k and "cloud_ai" in k]:
    del sys.modules[_key]

from youtube_extension.integrations.cloud_ai.base import (
    AnalysisType,
    BaseCloudAI,
    CloudAIProvider,
    DetectionResult,
    VideoAnalysisResult,
)
from youtube_extension.integrations.cloud_ai.exceptions import CloudAIError
from youtube_extension.integrations.cloud_ai.integrator import CloudAIIntegrator


def _make_result(provider=CloudAIProvider.GOOGLE_CLOUD, video_id="vid1",
                 analysis_types=None, objects=None, labels=None,
                 text_detections=None, faces=None, logos=None,
                 shots=None, scenes=None, processing_time=1.0,
                 cost_estimate=None) -> VideoAnalysisResult:
    return VideoAnalysisResult(
        provider=provider,
        video_id=video_id,
        analysis_types=analysis_types or [AnalysisType.OCR],
        objects=objects or [],
        labels=labels or [],
        text_detections=text_detections or [],
        faces=faces or [],
        logos=logos or [],
        shots=shots or [],
        scenes=scenes or [],
        processing_time=processing_time,
        cost_estimate=cost_estimate,
    )


class _FakeProvider(BaseCloudAI):
    """Minimal concrete provider for testing."""

    def __init__(self, config=None, supported_types=None, result=None, raise_on_analyze=None):
        super().__init__(config or {})
        self._supported = supported_types or list(AnalysisType)
        self._result = result
        self._raise = raise_on_analyze
        self.cleanup_called = False

    async def initialize(self) -> None:
        pass

    async def cleanup(self) -> None:
        self.cleanup_called = True

    async def analyze_video(self, video_url, analysis_types):
        if self._raise:
            raise self._raise
        return self._result or _make_result()

    async def analyze_image(self, image_url, analysis_types):
        return _make_result()

    def get_supported_analysis_types(self):
        return self._supported

    async def get_service_status(self):
        return {"ok": True}


# ===========================================================================
# CloudAIIntegrator.__init__
# ===========================================================================


class TestCloudAIIntegratorInit:
    def test_config_stored(self):
        cfg = {"google_cloud": {"enabled": False}}
        integrator = CloudAIIntegrator(cfg)
        assert integrator.config is cfg

    def test_providers_starts_empty(self):
        integrator = CloudAIIntegrator({})
        assert integrator.providers == {}

    def test_initialized_starts_false(self):
        integrator = CloudAIIntegrator({})
        assert integrator._initialized is False

    def test_fallback_order_has_three(self):
        integrator = CloudAIIntegrator({})
        assert len(integrator.fallback_order) == 3

    def test_fallback_order_google_first(self):
        integrator = CloudAIIntegrator({})
        assert integrator.fallback_order[0] == CloudAIProvider.GOOGLE_CLOUD

    def test_fallback_order_aws_second(self):
        integrator = CloudAIIntegrator({})
        assert integrator.fallback_order[1] == CloudAIProvider.AWS_REKOGNITION

    def test_fallback_order_azure_third(self):
        integrator = CloudAIIntegrator({})
        assert integrator.fallback_order[2] == CloudAIProvider.AZURE_VISION


# ===========================================================================
# CloudAIIntegrator.initialize (idempotent, no providers enabled)
# ===========================================================================


class TestCloudAIIntegratorInitialize:
    async def test_initialize_sets_initialized(self):
        integrator = CloudAIIntegrator({})
        await integrator.initialize()
        assert integrator._initialized is True

    async def test_initialize_idempotent(self):
        integrator = CloudAIIntegrator({})
        await integrator.initialize()
        # Inject a fake provider to detect if init re-runs
        integrator.providers[CloudAIProvider.GOOGLE_CLOUD] = _FakeProvider()
        await integrator.initialize()  # Should not clear providers
        assert CloudAIProvider.GOOGLE_CLOUD in integrator.providers

    async def test_initialize_no_providers_when_none_enabled(self):
        integrator = CloudAIIntegrator({
            "google_cloud": {"enabled": False},
            "aws_rekognition": {"enabled": False},
            "azure_vision": {"enabled": False},
        })
        await integrator.initialize()
        assert len(integrator.providers) == 0

    async def test_google_enabled_but_missing_deps_skipped(self):
        # enabled=True but no actual provider module — ImportError caught gracefully
        integrator = CloudAIIntegrator({"google_cloud": {"enabled": True}})
        await integrator.initialize()
        # Should not raise; provider simply not added
        assert integrator._initialized is True


# ===========================================================================
# CloudAIIntegrator.cleanup
# ===========================================================================


class TestCloudAIIntegratorCleanup:
    async def test_cleanup_clears_providers(self):
        integrator = CloudAIIntegrator({})
        p = _FakeProvider()
        integrator.providers[CloudAIProvider.GOOGLE_CLOUD] = p
        integrator._initialized = True
        await integrator.cleanup()
        assert integrator.providers == {}

    async def test_cleanup_sets_initialized_false(self):
        integrator = CloudAIIntegrator({})
        integrator._initialized = True
        await integrator.cleanup()
        assert integrator._initialized is False

    async def test_cleanup_calls_provider_cleanup(self):
        integrator = CloudAIIntegrator({})
        p = _FakeProvider()
        integrator.providers[CloudAIProvider.GOOGLE_CLOUD] = p
        integrator._initialized = True
        await integrator.cleanup()
        assert p.cleanup_called is True

    async def test_cleanup_continues_if_provider_cleanup_raises(self):
        class _FailProvider(_FakeProvider):
            async def cleanup(self):
                raise RuntimeError("cleanup failed")

        integrator = CloudAIIntegrator({})
        integrator.providers[CloudAIProvider.GOOGLE_CLOUD] = _FailProvider()
        integrator.providers[CloudAIProvider.AWS_REKOGNITION] = _FakeProvider()
        integrator._initialized = True
        await integrator.cleanup()  # Should not raise
        assert integrator.providers == {}

    async def test_cleanup_with_no_providers(self):
        integrator = CloudAIIntegrator({})
        integrator._initialized = True
        await integrator.cleanup()
        assert integrator._initialized is False


# ===========================================================================
# CloudAIIntegrator async context manager
# ===========================================================================


class TestCloudAIIntegratorContextManager:
    async def test_aenter_returns_self(self):
        integrator = CloudAIIntegrator({})
        result = await integrator.__aenter__()
        assert result is integrator

    async def test_aenter_sets_initialized(self):
        integrator = CloudAIIntegrator({})
        await integrator.__aenter__()
        assert integrator._initialized is True

    async def test_aexit_clears_initialized(self):
        integrator = CloudAIIntegrator({})
        await integrator.__aenter__()
        await integrator.__aexit__(None, None, None)
        assert integrator._initialized is False


# ===========================================================================
# CloudAIIntegrator.analyze_video
# ===========================================================================


class TestCloudAIIntegratorAnalyzeVideo:
    async def test_raises_when_no_providers(self):
        integrator = CloudAIIntegrator({})
        integrator._initialized = True
        with pytest.raises(CloudAIError):
            await integrator.analyze_video("http://example.com/v.mp4", [AnalysisType.OCR])

    async def test_uses_preferred_provider_first(self):
        integrator = CloudAIIntegrator({})
        integrator._initialized = True
        result_aws = _make_result(provider=CloudAIProvider.AWS_REKOGNITION)
        result_gcp = _make_result(provider=CloudAIProvider.GOOGLE_CLOUD)
        integrator.providers[CloudAIProvider.GOOGLE_CLOUD] = _FakeProvider(result=result_gcp)
        integrator.providers[CloudAIProvider.AWS_REKOGNITION] = _FakeProvider(result=result_aws)

        result = await integrator.analyze_video(
            "http://example.com/v.mp4",
            [AnalysisType.OCR],
            preferred_provider=CloudAIProvider.AWS_REKOGNITION,
        )
        assert result.provider == CloudAIProvider.AWS_REKOGNITION

    async def test_fallback_on_provider_failure(self):
        integrator = CloudAIIntegrator({})
        integrator._initialized = True
        result_aws = _make_result(provider=CloudAIProvider.AWS_REKOGNITION)
        integrator.providers[CloudAIProvider.GOOGLE_CLOUD] = _FakeProvider(
            raise_on_analyze=RuntimeError("gcp down")
        )
        integrator.providers[CloudAIProvider.AWS_REKOGNITION] = _FakeProvider(result=result_aws)

        result = await integrator.analyze_video("http://example.com/v.mp4", [AnalysisType.OCR])
        assert result.provider == CloudAIProvider.AWS_REKOGNITION

    async def test_no_fallback_skips_other_providers(self):
        integrator = CloudAIIntegrator({})
        integrator._initialized = True
        integrator.providers[CloudAIProvider.GOOGLE_CLOUD] = _FakeProvider(
            raise_on_analyze=RuntimeError("gcp down")
        )
        integrator.providers[CloudAIProvider.AWS_REKOGNITION] = _FakeProvider()

        with pytest.raises(CloudAIError):
            await integrator.analyze_video(
                "http://example.com/v.mp4",
                [AnalysisType.OCR],
                preferred_provider=CloudAIProvider.GOOGLE_CLOUD,
                use_fallback=False,
            )

    async def test_skips_provider_with_unsupported_types(self):
        integrator = CloudAIIntegrator({})
        integrator._initialized = True
        # Provider only supports OCR, request asks for FACE_DETECTION
        integrator.providers[CloudAIProvider.GOOGLE_CLOUD] = _FakeProvider(
            supported_types=[AnalysisType.OCR]
        )
        with pytest.raises(CloudAIError):
            await integrator.analyze_video(
                "http://example.com/v.mp4",
                [AnalysisType.FACE_DETECTION],
            )

    async def test_auto_initializes_when_not_initialized(self):
        integrator = CloudAIIntegrator({})
        # Do NOT set _initialized; analyze_video should call initialize()
        integrator.providers[CloudAIProvider.GOOGLE_CLOUD] = _FakeProvider()
        # After initialize() (no-op since _initialized=False), providers might be cleared
        # but we set them AFTER so we need _initialized = True trick via patching
        integrator._initialized = False
        # patch initialize so it doesn't wipe our fake providers
        original_init = integrator.initialize

        async def _patched_init():
            integrator._initialized = True  # just flip the flag

        integrator.initialize = _patched_init
        result = await integrator.analyze_video("http://example.com/v.mp4", [AnalysisType.OCR])
        assert result is not None

    async def test_error_code_all_providers_failed(self):
        integrator = CloudAIIntegrator({})
        integrator._initialized = True
        integrator.providers[CloudAIProvider.GOOGLE_CLOUD] = _FakeProvider(
            raise_on_analyze=RuntimeError("fail")
        )
        with pytest.raises(CloudAIError) as exc_info:
            await integrator.analyze_video("http://example.com/v.mp4", [AnalysisType.OCR])
        assert exc_info.value.error_code == "ALL_PROVIDERS_FAILED"


# ===========================================================================
# CloudAIIntegrator._safe_analyze
# ===========================================================================


class TestCloudAIIntegratorSafeAnalyze:
    async def test_returns_result_on_success(self):
        integrator = CloudAIIntegrator({})
        expected = _make_result()
        provider = _FakeProvider(result=expected)
        result = await integrator._safe_analyze(
            provider, "http://example.com/v.mp4",
            [AnalysisType.OCR], CloudAIProvider.GOOGLE_CLOUD
        )
        assert result is not None

    async def test_returns_none_on_exception(self):
        integrator = CloudAIIntegrator({})
        provider = _FakeProvider(raise_on_analyze=RuntimeError("fail"))
        result = await integrator._safe_analyze(
            provider, "http://example.com/v.mp4",
            [AnalysisType.OCR], CloudAIProvider.GOOGLE_CLOUD
        )
        assert result is None

    async def test_sets_provider_on_result(self):
        integrator = CloudAIIntegrator({})
        provider = _FakeProvider(result=_make_result(provider=CloudAIProvider.GOOGLE_CLOUD))
        result = await integrator._safe_analyze(
            provider, "http://example.com/v.mp4",
            [AnalysisType.OCR], CloudAIProvider.AWS_REKOGNITION
        )
        assert result.provider == CloudAIProvider.AWS_REKOGNITION


# ===========================================================================
# CloudAIIntegrator.aggregate_results
# ===========================================================================


class TestCloudAIIntegratorAggregateResults:
    def test_raises_on_empty_list(self):
        integrator = CloudAIIntegrator({})
        with pytest.raises(ValueError):
            integrator.aggregate_results([])

    def test_returns_single_result_as_is(self):
        integrator = CloudAIIntegrator({})
        r = _make_result()
        result = integrator.aggregate_results([r])
        assert result is r

    def test_aggregates_objects_from_multiple_providers(self):
        integrator = CloudAIIntegrator({})
        r1 = _make_result(objects=[DetectionResult(label="cat", confidence=0.9)])
        r2 = _make_result(objects=[DetectionResult(label="dog", confidence=0.8)])
        result = integrator.aggregate_results([r1, r2])
        labels = {d.label for d in result.objects}
        assert "cat" in labels
        assert "dog" in labels

    def test_aggregates_labels(self):
        integrator = CloudAIIntegrator({})
        r1 = _make_result(labels=[DetectionResult(label="sports", confidence=0.7)])
        r2 = _make_result(labels=[DetectionResult(label="outdoor", confidence=0.6)])
        result = integrator.aggregate_results([r1, r2])
        assert len(result.labels) == 2

    def test_cost_estimate_is_sum(self):
        integrator = CloudAIIntegrator({})
        r1 = _make_result(cost_estimate=1.0)
        r2 = _make_result(cost_estimate=2.0)
        result = integrator.aggregate_results([r1, r2])
        assert result.cost_estimate == pytest.approx(3.0)

    def test_processing_time_is_max(self):
        integrator = CloudAIIntegrator({})
        r1 = _make_result(processing_time=1.0)
        r2 = _make_result(processing_time=3.0)
        result = integrator.aggregate_results([r1, r2])
        assert result.processing_time == pytest.approx(3.0)

    def test_raw_response_lists_providers(self):
        integrator = CloudAIIntegrator({})
        r1 = _make_result(provider=CloudAIProvider.GOOGLE_CLOUD)
        r2 = _make_result(provider=CloudAIProvider.AWS_REKOGNITION)
        result = integrator.aggregate_results([r1, r2])
        assert "aggregated_from" in result.raw_response

    def test_video_id_from_first_result(self):
        integrator = CloudAIIntegrator({})
        r1 = _make_result(video_id="first")
        r2 = _make_result(video_id="second")
        result = integrator.aggregate_results([r1, r2])
        assert result.video_id == "first"


# ===========================================================================
# CloudAIIntegrator._merge_detections
# ===========================================================================


class TestCloudAIIntegratorMergeDetections:
    def test_empty_returns_empty(self):
        integrator = CloudAIIntegrator({})
        assert integrator._merge_detections([]) == []

    def test_single_detection_returned(self):
        integrator = CloudAIIntegrator({})
        d = DetectionResult(label="car", confidence=0.9)
        result = integrator._merge_detections([d])
        assert len(result) == 1

    def test_duplicate_labels_merged(self):
        integrator = CloudAIIntegrator({})
        d1 = DetectionResult(label="car", confidence=0.8)
        d2 = DetectionResult(label="car", confidence=0.6)
        result = integrator._merge_detections([d1, d2])
        assert len(result) == 1

    def test_duplicate_confidence_boosted(self):
        integrator = CloudAIIntegrator({})
        d1 = DetectionResult(label="car", confidence=0.8)
        d2 = DetectionResult(label="car", confidence=0.8)
        result = integrator._merge_detections([d1, d2])
        # averaged (0.8 + 0.8)/2 * 1.1 = 0.88
        assert result[0].confidence > 0.8

    def test_confidence_capped_at_1(self):
        integrator = CloudAIIntegrator({})
        d1 = DetectionResult(label="car", confidence=1.0)
        d2 = DetectionResult(label="car", confidence=1.0)
        result = integrator._merge_detections([d1, d2])
        assert result[0].confidence <= 1.0

    def test_different_labels_kept_separate(self):
        integrator = CloudAIIntegrator({})
        detections = [
            DetectionResult(label="cat", confidence=0.9),
            DetectionResult(label="dog", confidence=0.8),
            DetectionResult(label="bird", confidence=0.7),
        ]
        result = integrator._merge_detections(detections)
        assert len(result) == 3

    def test_sorted_by_confidence_descending(self):
        integrator = CloudAIIntegrator({})
        detections = [
            DetectionResult(label="a", confidence=0.3),
            DetectionResult(label="b", confidence=0.9),
            DetectionResult(label="c", confidence=0.6),
        ]
        result = integrator._merge_detections(detections)
        confidences = [d.confidence for d in result]
        assert confidences == sorted(confidences, reverse=True)

    def test_case_insensitive_label_matching(self):
        integrator = CloudAIIntegrator({})
        d1 = DetectionResult(label="CAR", confidence=0.9)
        d2 = DetectionResult(label="car", confidence=0.8)
        result = integrator._merge_detections([d1, d2])
        assert len(result) == 1


# ===========================================================================
# CloudAIIntegrator.multi_provider_analysis
# ===========================================================================


class TestCloudAIIntegratorMultiProviderAnalysis:
    async def test_returns_empty_when_no_providers(self):
        integrator = CloudAIIntegrator({})
        integrator._initialized = True
        results = await integrator.multi_provider_analysis("http://example.com/v.mp4", [AnalysisType.OCR])
        assert results == []

    async def test_returns_results_from_all_providers(self):
        integrator = CloudAIIntegrator({})
        integrator._initialized = True
        integrator.providers[CloudAIProvider.GOOGLE_CLOUD] = _FakeProvider(
            result=_make_result(provider=CloudAIProvider.GOOGLE_CLOUD)
        )
        integrator.providers[CloudAIProvider.AWS_REKOGNITION] = _FakeProvider(
            result=_make_result(provider=CloudAIProvider.AWS_REKOGNITION)
        )
        results = await integrator.multi_provider_analysis("http://example.com/v.mp4", [AnalysisType.OCR])
        assert len(results) == 2

    async def test_failed_providers_excluded_from_results(self):
        integrator = CloudAIIntegrator({})
        integrator._initialized = True
        integrator.providers[CloudAIProvider.GOOGLE_CLOUD] = _FakeProvider(
            raise_on_analyze=RuntimeError("fail")
        )
        integrator.providers[CloudAIProvider.AWS_REKOGNITION] = _FakeProvider(
            result=_make_result(provider=CloudAIProvider.AWS_REKOGNITION)
        )
        results = await integrator.multi_provider_analysis("http://example.com/v.mp4", [AnalysisType.OCR])
        # Failed provider returns None, which is not a VideoAnalysisResult
        assert all(isinstance(r, VideoAnalysisResult) for r in results)

    async def test_skips_providers_with_no_supported_types(self):
        integrator = CloudAIIntegrator({})
        integrator._initialized = True
        integrator.providers[CloudAIProvider.GOOGLE_CLOUD] = _FakeProvider(
            supported_types=[AnalysisType.OCR]
        )
        # FACE_DETECTION not supported by OCR-only provider
        results = await integrator.multi_provider_analysis(
            "http://example.com/v.mp4", [AnalysisType.FACE_DETECTION]
        )
        assert results == []


# ===========================================================================
# CloudAIIntegrator.get_provider_status
# ===========================================================================


class TestCloudAIIntegratorGetProviderStatus:
    async def test_empty_when_no_providers(self):
        integrator = CloudAIIntegrator({})
        status = await integrator.get_provider_status()
        assert status == {}

    async def test_available_true_on_success(self):
        integrator = CloudAIIntegrator({})
        integrator.providers[CloudAIProvider.GOOGLE_CLOUD] = _FakeProvider()
        status = await integrator.get_provider_status()
        assert status["google_cloud"]["available"] is True

    async def test_available_false_on_exception(self):
        class _FailStatusProvider(_FakeProvider):
            async def get_service_status(self):
                raise RuntimeError("unreachable")

        integrator = CloudAIIntegrator({})
        integrator.providers[CloudAIProvider.GOOGLE_CLOUD] = _FailStatusProvider()
        status = await integrator.get_provider_status()
        assert status["google_cloud"]["available"] is False

    async def test_error_message_included_on_failure(self):
        class _FailStatusProvider(_FakeProvider):
            async def get_service_status(self):
                raise RuntimeError("network error")

        integrator = CloudAIIntegrator({})
        integrator.providers[CloudAIProvider.GOOGLE_CLOUD] = _FailStatusProvider()
        status = await integrator.get_provider_status()
        assert "error" in status["google_cloud"]
        assert "network error" in status["google_cloud"]["error"]


# ===========================================================================
# Provider init helpers (disabled/enabled paths)
# ===========================================================================


class TestCloudAIIntegratorProviderHelpers:
    async def test_google_cloud_skipped_when_disabled(self):
        integrator = CloudAIIntegrator({"google_cloud": {"enabled": False}})
        await integrator._initialize_google_cloud()
        assert CloudAIProvider.GOOGLE_CLOUD not in integrator.providers

    async def test_aws_rekognition_skipped_when_disabled(self):
        integrator = CloudAIIntegrator({"aws_rekognition": {"enabled": False}})
        await integrator._initialize_aws_rekognition()
        assert CloudAIProvider.AWS_REKOGNITION not in integrator.providers

    async def test_azure_vision_skipped_when_disabled(self):
        integrator = CloudAIIntegrator({"azure_vision": {"enabled": False}})
        await integrator._initialize_azure_vision()
        assert CloudAIProvider.AZURE_VISION not in integrator.providers

    async def test_google_cloud_import_error_handled_gracefully(self):
        # enabled=True, but provider module not available → ImportError silently skipped
        integrator = CloudAIIntegrator({"google_cloud": {"enabled": True}})
        await integrator._initialize_google_cloud()
        # No exception; provider just not added
        assert integrator._initialized is False

    async def test_aws_rekognition_import_error_handled_gracefully(self):
        integrator = CloudAIIntegrator({"aws_rekognition": {"enabled": True}})
        await integrator._initialize_aws_rekognition()
        assert CloudAIProvider.AWS_REKOGNITION not in integrator.providers

    async def test_azure_vision_import_error_handled_gracefully(self):
        integrator = CloudAIIntegrator({"azure_vision": {"enabled": True}})
        await integrator._initialize_azure_vision()
        assert CloudAIProvider.AZURE_VISION not in integrator.providers

    async def test_apple_fastvlm_skipped_when_disabled(self):
        integrator = CloudAIIntegrator({"apple_fastvlm": {"enabled": False}})
        await integrator._initialize_apple_fastvlm()
        # No APPLE_FASTVLM in CloudAIProvider enum, but method should not raise
        assert len(integrator.providers) == 0

    async def test_apple_fastvlm_import_error_handled_gracefully(self):
        integrator = CloudAIIntegrator({"apple_fastvlm": {"enabled": True}})
        await integrator._initialize_apple_fastvlm()
        assert len(integrator.providers) == 0
