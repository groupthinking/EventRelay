"""Unit tests for integrations/cloud_ai/providers/google_cloud.py."""

from __future__ import annotations

import asyncio
import builtins
import sys
import threading
import types as _types
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

_SRC = Path(__file__).resolve().parents[2] / "src"
sys.path.insert(0, str(_SRC))

from youtube_extension.integrations.cloud_ai.base import (
    AnalysisType,
    CloudAIProvider,
    VideoAnalysisResult,
)
from youtube_extension.integrations.cloud_ai.exceptions import (
    AuthenticationError,
    CloudAIError,
    ConfigurationError,
    RateLimitError,
)
from youtube_extension.integrations.cloud_ai.providers.google_cloud import GoogleCloudAI

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

VALID_CONFIG = {
    "project_id": "my-gcp-project",
}


def _make_provider(config=None) -> GoogleCloudAI:
    return GoogleCloudAI(config or VALID_CONFIG)


def _make_vertex(x, y):
    v = MagicMock()
    v.x = x
    v.y = y
    return v


def _make_bounding_poly(vertices):
    bp = MagicMock()
    bp.vertices = vertices
    return bp


def _make_normalized_vertex(x, y):
    v = MagicMock()
    v.x = x
    v.y = y
    return v


def _make_vision_response(labels=None, text_annotations=None, logo_annotations=None,
                           localized_objects=None):
    """Build a fake google.cloud.vision annotate_image response."""
    resp = MagicMock()
    resp.label_annotations = labels or []
    resp.text_annotations = text_annotations or []
    resp.logo_annotations = logo_annotations or []
    resp.localized_object_annotations = localized_objects or []
    return resp


def _make_video_annotation_result(
    object_annotations=None,
    segment_label_annotations=None,
    text_annotations=None,
    logo_recognition_annotations=None,
    shot_annotations=None,
):
    ann = MagicMock()
    ann.object_annotations = object_annotations or []
    ann.segment_label_annotations = segment_label_annotations or []
    ann.text_annotations = text_annotations or []
    ann.logo_recognition_annotations = logo_recognition_annotations or []
    ann.shot_annotations = shot_annotations or []
    return ann


# ===========================================================================
# __init__ / _validate_config
# ===========================================================================


class TestGoogleCloudAIInit:
    def test_valid_config_does_not_raise(self):
        provider = _make_provider()
        assert provider is not None

    def test_provider_set_to_google_cloud(self):
        provider = _make_provider()
        assert provider.provider == CloudAIProvider.GOOGLE_CLOUD

    def test_video_client_starts_none(self):
        provider = _make_provider()
        assert provider._video_client is None

    def test_vision_client_starts_none(self):
        provider = _make_provider()
        assert provider._vision_client is None

    def test_config_stored(self):
        provider = _make_provider()
        assert provider.config is VALID_CONFIG

    def test_missing_project_id_raises_config_error(self):
        with pytest.raises(ConfigurationError) as exc_info:
            GoogleCloudAI({})
        assert exc_info.value.missing_config == "project_id"

    def test_config_error_has_google_provider(self):
        with pytest.raises(ConfigurationError) as exc_info:
            GoogleCloudAI({})
        assert exc_info.value.provider == CloudAIProvider.GOOGLE_CLOUD.value

    def test_config_error_code_is_configuration_error(self):
        with pytest.raises(ConfigurationError) as exc_info:
            GoogleCloudAI({})
        assert exc_info.value.error_code == "CONFIGURATION_ERROR"


# ===========================================================================
# initialize
# ===========================================================================


class TestGoogleCloudAIInitialize:
    async def test_initialize_sets_video_client(self):
        provider = _make_provider()
        mock_video_client = MagicMock()
        mock_vision_client = MagicMock()
        mock_videoint = MagicMock()
        mock_videoint.VideoIntelligenceServiceAsyncClient.return_value = mock_video_client
        mock_vision = MagicMock()
        mock_vision.ImageAnnotatorAsyncClient.return_value = mock_vision_client

        with patch.dict("sys.modules", {
            "google": _types.ModuleType("google"),
            "google.auth": MagicMock(),
            "google.cloud": _types.ModuleType("google.cloud"),
            "google.cloud.videointelligence": mock_videoint,
            "google.cloud.vision": mock_vision,
        }):
            await provider.initialize()

        assert provider._video_client is mock_video_client

    async def test_initialize_sets_vision_client(self):
        provider = _make_provider()
        mock_video_client = MagicMock()
        mock_vision_client = MagicMock()
        mock_videoint = MagicMock()
        mock_videoint.VideoIntelligenceServiceAsyncClient.return_value = mock_video_client
        mock_vision = MagicMock()
        mock_vision.ImageAnnotatorAsyncClient.return_value = mock_vision_client

        with patch.dict("sys.modules", {
            "google": _types.ModuleType("google"),
            "google.auth": MagicMock(),
            "google.cloud": _types.ModuleType("google.cloud"),
            "google.cloud.videointelligence": mock_videoint,
            "google.cloud.vision": mock_vision,
        }):
            await provider.initialize()

        assert provider._vision_client is mock_vision_client

    async def test_initialize_raises_config_error_on_import_error(self):
        provider = _make_provider()
        with patch.dict("sys.modules", {
            "google": None,
            "google.auth": None,
            "google.cloud": None,
            "google.cloud.videointelligence": None,
            "google.cloud.vision": None,
        }):
            with pytest.raises((ConfigurationError, Exception)):
                await provider.initialize()

    async def test_initialize_raises_auth_error_on_general_exception(self):
        provider = _make_provider()
        mock_videoint = MagicMock()
        mock_videoint.VideoIntelligenceServiceAsyncClient.side_effect = Exception("auth failure")
        mock_vision = MagicMock()

        with patch.dict("sys.modules", {
            "google": _types.ModuleType("google"),
            "google.auth": MagicMock(),
            "google.cloud": _types.ModuleType("google.cloud"),
            "google.cloud.videointelligence": mock_videoint,
            "google.cloud.vision": mock_vision,
        }):
            with pytest.raises(AuthenticationError):
                await provider.initialize()


# ===========================================================================
# cleanup
# ===========================================================================


class TestGoogleCloudAICleanup:
    async def test_cleanup_clears_video_client(self):
        provider = _make_provider()
        mock_client = MagicMock()
        mock_client.transport = MagicMock()
        mock_client.transport.close = AsyncMock()
        provider._video_client = mock_client
        await provider.cleanup()
        assert provider._video_client is None

    async def test_cleanup_clears_vision_client(self):
        provider = _make_provider()
        mock_client = MagicMock()
        mock_client.transport = MagicMock()
        mock_client.transport.close = AsyncMock()
        provider._vision_client = mock_client
        await provider.cleanup()
        assert provider._vision_client is None

    async def test_cleanup_calls_transport_close_on_video_client(self):
        provider = _make_provider()
        mock_client = MagicMock()
        mock_transport = MagicMock()
        mock_transport.close = AsyncMock()
        mock_client.transport = mock_transport
        provider._video_client = mock_client
        await provider.cleanup()
        mock_transport.close.assert_called_once()

    async def test_cleanup_calls_transport_close_on_vision_client(self):
        provider = _make_provider()
        mock_client = MagicMock()
        mock_transport = MagicMock()
        mock_transport.close = AsyncMock()
        mock_client.transport = mock_transport
        provider._vision_client = mock_client
        await provider.cleanup()
        mock_transport.close.assert_called_once()

    async def test_cleanup_idempotent_when_already_none(self):
        provider = _make_provider()
        await provider.cleanup()  # Should not raise
        assert provider._video_client is None
        assert provider._vision_client is None


# ===========================================================================
# get_supported_analysis_types
# ===========================================================================


class TestGoogleCloudAISupportedTypes:
    def test_returns_list(self):
        provider = _make_provider()
        types = provider.get_supported_analysis_types()
        assert isinstance(types, list)

    def test_includes_object_tracking(self):
        provider = _make_provider()
        assert AnalysisType.OBJECT_TRACKING in provider.get_supported_analysis_types()

    def test_includes_ocr(self):
        provider = _make_provider()
        assert AnalysisType.OCR in provider.get_supported_analysis_types()

    def test_includes_label_detection(self):
        provider = _make_provider()
        assert AnalysisType.LABEL_DETECTION in provider.get_supported_analysis_types()

    def test_includes_logo_recognition(self):
        provider = _make_provider()
        assert AnalysisType.LOGO_RECOGNITION in provider.get_supported_analysis_types()

    def test_includes_shot_detection(self):
        provider = _make_provider()
        assert AnalysisType.SHOT_DETECTION in provider.get_supported_analysis_types()

    def test_includes_text_detection(self):
        provider = _make_provider()
        assert AnalysisType.TEXT_DETECTION in provider.get_supported_analysis_types()

    def test_returns_at_least_six_types(self):
        provider = _make_provider()
        assert len(provider.get_supported_analysis_types()) >= 6


# ===========================================================================
# _prepare_video_features
# ===========================================================================


class TestGoogleCloudAIPrepareVideoFeatures:
    def _setup_mock_videoint(self):
        mock_feature = MagicMock()
        mock_feature.OBJECT_TRACKING = "OBJECT_TRACKING"
        mock_feature.TEXT_DETECTION = "TEXT_DETECTION"
        mock_feature.LABEL_DETECTION = "LABEL_DETECTION"
        mock_feature.LOGO_RECOGNITION = "LOGO_RECOGNITION"
        mock_feature.SHOT_CHANGE_DETECTION = "SHOT_CHANGE_DETECTION"
        mock_videoint = MagicMock()
        mock_videoint.Feature = mock_feature
        return mock_videoint

    def test_object_tracking_mapped(self):
        provider = _make_provider()
        mock_videoint = self._setup_mock_videoint()
        with patch.dict("sys.modules", {
            "google": _types.ModuleType("google"),
            "google.cloud": _types.ModuleType("google.cloud"),
            "google.cloud.videointelligence": mock_videoint,
        }):
            features = provider._prepare_video_features([AnalysisType.OBJECT_TRACKING])
        assert "OBJECT_TRACKING" in features

    def test_ocr_mapped_to_text_detection(self):
        provider = _make_provider()
        mock_videoint = self._setup_mock_videoint()
        with patch.dict("sys.modules", {
            "google": _types.ModuleType("google"),
            "google.cloud": _types.ModuleType("google.cloud"),
            "google.cloud.videointelligence": mock_videoint,
        }):
            features = provider._prepare_video_features([AnalysisType.OCR])
        assert "TEXT_DETECTION" in features

    def test_label_detection_mapped(self):
        provider = _make_provider()
        mock_videoint = self._setup_mock_videoint()
        with patch.dict("sys.modules", {
            "google": _types.ModuleType("google"),
            "google.cloud": _types.ModuleType("google.cloud"),
            "google.cloud.videointelligence": mock_videoint,
        }):
            features = provider._prepare_video_features([AnalysisType.LABEL_DETECTION])
        assert "LABEL_DETECTION" in features

    def test_logo_recognition_mapped(self):
        provider = _make_provider()
        mock_videoint = self._setup_mock_videoint()
        with patch.dict("sys.modules", {
            "google": _types.ModuleType("google"),
            "google.cloud": _types.ModuleType("google.cloud"),
            "google.cloud.videointelligence": mock_videoint,
        }):
            features = provider._prepare_video_features([AnalysisType.LOGO_RECOGNITION])
        assert "LOGO_RECOGNITION" in features

    def test_shot_detection_mapped(self):
        provider = _make_provider()
        mock_videoint = self._setup_mock_videoint()
        with patch.dict("sys.modules", {
            "google": _types.ModuleType("google"),
            "google.cloud": _types.ModuleType("google.cloud"),
            "google.cloud.videointelligence": mock_videoint,
        }):
            features = provider._prepare_video_features([AnalysisType.SHOT_DETECTION])
        assert "SHOT_CHANGE_DETECTION" in features

    def test_unsupported_type_not_in_features(self):
        provider = _make_provider()
        mock_videoint = self._setup_mock_videoint()
        with patch.dict("sys.modules", {
            "google": _types.ModuleType("google"),
            "google.cloud": _types.ModuleType("google.cloud"),
            "google.cloud.videointelligence": mock_videoint,
        }):
            features = provider._prepare_video_features([AnalysisType.FACE_DETECTION])
        assert features == []

    def test_multiple_types_mapped(self):
        provider = _make_provider()
        mock_videoint = self._setup_mock_videoint()
        with patch.dict("sys.modules", {
            "google": _types.ModuleType("google"),
            "google.cloud": _types.ModuleType("google.cloud"),
            "google.cloud.videointelligence": mock_videoint,
        }):
            features = provider._prepare_video_features(
                [AnalysisType.LABEL_DETECTION, AnalysisType.OBJECT_TRACKING]
            )
        assert len(features) == 2


# ===========================================================================
# _prepare_vision_features
# ===========================================================================


class TestGoogleCloudAIPrepareVisionFeatures:
    def _setup_mock_vision(self):
        mock_feature_type = MagicMock()
        mock_feature_type.TEXT_DETECTION = "TEXT_DETECTION"
        mock_feature_type.LABEL_DETECTION = "LABEL_DETECTION"
        mock_feature_type.LOGO_DETECTION = "LOGO_DETECTION"
        mock_feature_type.OBJECT_LOCALIZATION = "OBJECT_LOCALIZATION"
        mock_feature_type.DOCUMENT_TEXT_DETECTION = "DOCUMENT_TEXT_DETECTION"
        mock_feature = MagicMock()
        mock_feature.Type = mock_feature_type
        mock_vision = MagicMock()
        mock_vision.Feature = mock_feature
        return mock_vision

    def test_ocr_mapped(self):
        provider = _make_provider()
        mock_vision = self._setup_mock_vision()
        with patch.dict("sys.modules", {
            "google": _types.ModuleType("google"),
            "google.cloud": _types.ModuleType("google.cloud"),
            "google.cloud.vision": mock_vision,
        }):
            features = provider._prepare_vision_features([AnalysisType.OCR])
        assert len(features) == 1
        assert features[0]['type_'] == "TEXT_DETECTION"

    def test_label_detection_mapped(self):
        provider = _make_provider()
        mock_vision = self._setup_mock_vision()
        with patch.dict("sys.modules", {
            "google": _types.ModuleType("google"),
            "google.cloud": _types.ModuleType("google.cloud"),
            "google.cloud.vision": mock_vision,
        }):
            features = provider._prepare_vision_features([AnalysisType.LABEL_DETECTION])
        assert features[0]['type_'] == "LABEL_DETECTION"

    def test_logo_recognition_mapped(self):
        provider = _make_provider()
        mock_vision = self._setup_mock_vision()
        with patch.dict("sys.modules", {
            "google": _types.ModuleType("google"),
            "google.cloud": _types.ModuleType("google.cloud"),
            "google.cloud.vision": mock_vision,
        }):
            features = provider._prepare_vision_features([AnalysisType.LOGO_RECOGNITION])
        assert features[0]['type_'] == "LOGO_DETECTION"

    def test_object_tracking_mapped_to_localization(self):
        provider = _make_provider()
        mock_vision = self._setup_mock_vision()
        with patch.dict("sys.modules", {
            "google": _types.ModuleType("google"),
            "google.cloud": _types.ModuleType("google.cloud"),
            "google.cloud.vision": mock_vision,
        }):
            features = provider._prepare_vision_features([AnalysisType.OBJECT_TRACKING])
        assert features[0]['type_'] == "OBJECT_LOCALIZATION"

    def test_text_detection_mapped_to_document(self):
        provider = _make_provider()
        mock_vision = self._setup_mock_vision()
        with patch.dict("sys.modules", {
            "google": _types.ModuleType("google"),
            "google.cloud": _types.ModuleType("google.cloud"),
            "google.cloud.vision": mock_vision,
        }):
            features = provider._prepare_vision_features([AnalysisType.TEXT_DETECTION])
        assert features[0]['type_'] == "DOCUMENT_TEXT_DETECTION"

    def test_max_results_set_to_50(self):
        provider = _make_provider()
        mock_vision = self._setup_mock_vision()
        with patch.dict("sys.modules", {
            "google": _types.ModuleType("google"),
            "google.cloud": _types.ModuleType("google.cloud"),
            "google.cloud.vision": mock_vision,
        }):
            features = provider._prepare_vision_features([AnalysisType.OCR])
        assert features[0]['max_results'] == 50

    def test_unsupported_type_not_included(self):
        provider = _make_provider()
        mock_vision = self._setup_mock_vision()
        with patch.dict("sys.modules", {
            "google": _types.ModuleType("google"),
            "google.cloud": _types.ModuleType("google.cloud"),
            "google.cloud.vision": mock_vision,
        }):
            features = provider._prepare_vision_features([AnalysisType.FACE_DETECTION])
        assert features == []


# ===========================================================================
# _process_video_results
# ===========================================================================


class TestGoogleCloudAIProcessVideoResults:
    def _make_result_with_annotations(self, ann):
        result = MagicMock()
        result.annotation_results = [ann]
        return result

    def test_returns_video_analysis_result(self):
        provider = _make_provider()
        ann = _make_video_annotation_result()
        raw = self._make_result_with_annotations(ann)
        result = provider._process_video_results(raw, "vid1", [AnalysisType.LABEL_DETECTION], 2.0)
        assert isinstance(result, VideoAnalysisResult)

    def test_provider_is_google_cloud(self):
        provider = _make_provider()
        ann = _make_video_annotation_result()
        raw = self._make_result_with_annotations(ann)
        result = provider._process_video_results(raw, "vid1", [], 1.0)
        assert result.provider == CloudAIProvider.GOOGLE_CLOUD

    def test_video_id_set(self):
        provider = _make_provider()
        ann = _make_video_annotation_result()
        raw = self._make_result_with_annotations(ann)
        result = provider._process_video_results(raw, "my-video", [], 1.0)
        assert result.video_id == "my-video"

    def test_processing_time_set(self):
        provider = _make_provider()
        ann = _make_video_annotation_result()
        raw = self._make_result_with_annotations(ann)
        result = provider._process_video_results(raw, "vid1", [], 5.5)
        assert result.processing_time == pytest.approx(5.5)

    def test_empty_annotations_returns_empty_lists(self):
        provider = _make_provider()
        ann = _make_video_annotation_result()
        raw = self._make_result_with_annotations(ann)
        result = provider._process_video_results(raw, "vid1", [], 1.0)
        assert result.objects == []
        assert result.labels == []
        assert result.text_detections == []
        assert result.logos == []
        assert result.shots == []

    def test_object_annotations_processed(self):
        provider = _make_provider()
        mock_frame = MagicMock()
        mock_frame.time_offset.total_seconds.return_value = 2.5
        mock_frame.normalized_bounding_box.left = 0.1
        mock_frame.normalized_bounding_box.top = 0.2
        mock_frame.normalized_bounding_box.right = 0.4
        mock_frame.normalized_bounding_box.bottom = 0.6
        mock_obj = MagicMock()
        mock_obj.entity.description = "person"
        mock_obj.confidence = 0.95
        mock_obj.frames = [mock_frame]
        ann = _make_video_annotation_result(object_annotations=[mock_obj])
        raw = self._make_result_with_annotations(ann)
        result = provider._process_video_results(raw, "vid1", [AnalysisType.OBJECT_TRACKING], 1.0)
        assert len(result.objects) == 1
        assert result.objects[0].label == "person"
        assert result.objects[0].confidence == pytest.approx(0.95)
        assert result.objects[0].timestamp == pytest.approx(2.5)
        assert result.objects[0].bounding_box['x'] == pytest.approx(0.1)
        assert result.objects[0].bounding_box['width'] == pytest.approx(0.3)
        assert result.objects[0].bounding_box['height'] == pytest.approx(0.4)

    def test_label_annotations_processed(self):
        provider = _make_provider()
        mock_segment = MagicMock()
        mock_segment.confidence = 0.88
        mock_label = MagicMock()
        mock_label.entity.description = "outdoor"
        mock_label.segments = [mock_segment]
        ann = _make_video_annotation_result(segment_label_annotations=[mock_label])
        raw = self._make_result_with_annotations(ann)
        result = provider._process_video_results(raw, "vid1", [AnalysisType.LABEL_DETECTION], 1.0)
        assert len(result.labels) == 1
        assert result.labels[0].label == "outdoor"
        assert result.labels[0].confidence == pytest.approx(0.88)

    def test_label_no_segments_uses_zero_confidence(self):
        provider = _make_provider()
        mock_label = MagicMock()
        mock_label.entity.description = "indoor"
        mock_label.segments = []
        ann = _make_video_annotation_result(segment_label_annotations=[mock_label])
        raw = self._make_result_with_annotations(ann)
        result = provider._process_video_results(raw, "vid1", [], 1.0)
        assert result.labels[0].confidence == pytest.approx(0.0)

    def test_text_annotations_processed(self):
        provider = _make_provider()
        mock_seg = MagicMock()
        mock_seg.confidence = 0.97
        mock_seg.segment.start_time_offset.total_seconds.return_value = 3.0
        mock_text = MagicMock()
        mock_text.text = "Hello World"
        mock_text.segments = [mock_seg]
        ann = _make_video_annotation_result(text_annotations=[mock_text])
        raw = self._make_result_with_annotations(ann)
        result = provider._process_video_results(raw, "vid1", [AnalysisType.TEXT_DETECTION], 1.0)
        assert len(result.text_detections) == 1
        assert result.text_detections[0].label == "Hello World"
        assert result.text_detections[0].timestamp == pytest.approx(3.0)

    def test_logo_annotations_processed(self):
        provider = _make_provider()
        mock_track = MagicMock()
        mock_track.confidence = 0.92
        mock_track.segment.start_time_offset.total_seconds.return_value = 1.5
        mock_logo = MagicMock()
        mock_logo.entity.description = "Google"
        mock_logo.tracks = [mock_track]
        ann = _make_video_annotation_result(logo_recognition_annotations=[mock_logo])
        raw = self._make_result_with_annotations(ann)
        result = provider._process_video_results(raw, "vid1", [AnalysisType.LOGO_RECOGNITION], 1.0)
        assert len(result.logos) == 1
        assert result.logos[0].label == "Google"
        assert result.logos[0].confidence == pytest.approx(0.92)

    def test_shot_annotations_processed(self):
        provider = _make_provider()
        mock_shot = MagicMock()
        mock_shot.start_time_offset.total_seconds.return_value = 0.0
        mock_shot.end_time_offset.total_seconds.return_value = 5.0
        ann = _make_video_annotation_result(shot_annotations=[mock_shot])
        raw = self._make_result_with_annotations(ann)
        result = provider._process_video_results(raw, "vid1", [AnalysisType.SHOT_DETECTION], 1.0)
        assert len(result.shots) == 1
        assert result.shots[0]['start_time'] == pytest.approx(0.0)
        assert result.shots[0]['end_time'] == pytest.approx(5.0)

    def test_raw_response_contains_annotation_results(self):
        provider = _make_provider()
        ann = _make_video_annotation_result()
        raw = self._make_result_with_annotations(ann)
        result = provider._process_video_results(raw, "vid1", [], 1.0)
        assert 'annotation_results' in result.raw_response


# ===========================================================================
# _process_vision_results
# ===========================================================================


class TestGoogleCloudAIProcessVisionResults:
    def test_returns_video_analysis_result(self):
        provider = _make_provider()
        response = _make_vision_response()
        result = provider._process_vision_results(response, "img1", [AnalysisType.OCR], 0.5)
        assert isinstance(result, VideoAnalysisResult)

    def test_provider_is_google_cloud(self):
        provider = _make_provider()
        response = _make_vision_response()
        result = provider._process_vision_results(response, "img1", [], 1.0)
        assert result.provider == CloudAIProvider.GOOGLE_CLOUD

    def test_image_id_set(self):
        provider = _make_provider()
        response = _make_vision_response()
        result = provider._process_vision_results(response, "image-abc", [], 1.0)
        assert result.video_id == "image-abc"

    def test_processing_time_set(self):
        provider = _make_provider()
        response = _make_vision_response()
        result = provider._process_vision_results(response, "img1", [], 2.5)
        assert result.processing_time == pytest.approx(2.5)

    def test_empty_response_all_empty(self):
        provider = _make_provider()
        response = _make_vision_response()
        result = provider._process_vision_results(response, "img1", [], 1.0)
        assert result.labels == []
        assert result.text_detections == []
        assert result.logos == []
        assert result.objects == []

    def test_label_annotations_processed(self):
        provider = _make_provider()
        mock_label = MagicMock()
        mock_label.description = "sky"
        mock_label.score = 0.98
        response = _make_vision_response(labels=[mock_label])
        result = provider._process_vision_results(response, "img1", [AnalysisType.LABEL_DETECTION], 1.0)
        assert len(result.labels) == 1
        assert result.labels[0].label == "sky"
        assert result.labels[0].confidence == pytest.approx(0.98)

    def test_text_annotations_processed(self):
        provider = _make_provider()
        vertices = [
            _make_vertex(10, 20),
            _make_vertex(100, 20),
            _make_vertex(100, 50),
            _make_vertex(10, 50),
        ]
        mock_text = MagicMock()
        mock_text.description = "Hello"
        mock_text.bounding_poly = _make_bounding_poly(vertices)
        response = _make_vision_response(text_annotations=[mock_text])
        result = provider._process_vision_results(response, "img1", [AnalysisType.TEXT_DETECTION], 1.0)
        assert len(result.text_detections) == 1
        assert result.text_detections[0].label == "Hello"
        assert result.text_detections[0].confidence == pytest.approx(1.0)
        assert result.text_detections[0].bounding_box['x'] == 10
        assert result.text_detections[0].bounding_box['y'] == 20
        assert result.text_detections[0].bounding_box['width'] == 90
        assert result.text_detections[0].bounding_box['height'] == 30

    def test_logo_annotations_processed(self):
        provider = _make_provider()
        vertices = [
            _make_vertex(0, 0),
            _make_vertex(50, 0),
            _make_vertex(50, 30),
            _make_vertex(0, 30),
        ]
        mock_logo = MagicMock()
        mock_logo.description = "Amazon"
        mock_logo.score = 0.87
        mock_logo.bounding_poly = _make_bounding_poly(vertices)
        response = _make_vision_response(logo_annotations=[mock_logo])
        result = provider._process_vision_results(response, "img1", [AnalysisType.LOGO_RECOGNITION], 1.0)
        assert len(result.logos) == 1
        assert result.logos[0].label == "Amazon"
        assert result.logos[0].confidence == pytest.approx(0.87)

    def test_object_localizations_processed(self):
        provider = _make_provider()
        nv = [
            _make_normalized_vertex(0.1, 0.2),
            _make_normalized_vertex(0.4, 0.2),
            _make_normalized_vertex(0.4, 0.6),
            _make_normalized_vertex(0.1, 0.6),
        ]
        mock_norm_bp = MagicMock()
        mock_norm_bp.normalized_vertices = nv
        mock_obj = MagicMock()
        mock_obj.name = "cat"
        mock_obj.score = 0.91
        mock_obj.bounding_poly = mock_norm_bp
        response = _make_vision_response(localized_objects=[mock_obj])
        result = provider._process_vision_results(response, "img1", [AnalysisType.OBJECT_TRACKING], 1.0)
        assert len(result.objects) == 1
        assert result.objects[0].label == "cat"
        assert result.objects[0].confidence == pytest.approx(0.91)
        assert result.objects[0].bounding_box['x'] == pytest.approx(0.1)
        assert result.objects[0].bounding_box['y'] == pytest.approx(0.2)
        assert result.objects[0].bounding_box['width'] == pytest.approx(0.3)
        assert result.objects[0].bounding_box['height'] == pytest.approx(0.4)

    def test_raw_response_contains_vision_response(self):
        provider = _make_provider()
        response = _make_vision_response()
        result = provider._process_vision_results(response, "img1", [], 1.0)
        assert 'vision_response' in result.raw_response

    def test_faces_always_empty_for_vision(self):
        provider = _make_provider()
        response = _make_vision_response()
        result = provider._process_vision_results(response, "img1", [], 1.0)
        assert result.faces == []


# ===========================================================================
# analyze_video (integration-style)
# ===========================================================================


class TestGoogleCloudAIAnalyzeVideo:
    async def test_analyze_video_returns_result_with_initialized_client(self):
        provider = _make_provider()
        mock_video_client = AsyncMock()
        mock_ann = _make_video_annotation_result()
        mock_api_result = MagicMock()
        mock_api_result.annotation_results = [mock_ann]
        mock_operation = AsyncMock()
        mock_operation.result = AsyncMock(return_value=mock_api_result)
        mock_video_client.annotate_video = AsyncMock(return_value=mock_operation)
        provider._video_client = mock_video_client

        mock_videoint = MagicMock()
        mock_videoint.Feature.LABEL_DETECTION = "LABEL_DETECTION"
        with patch.dict("sys.modules", {
            "google": _types.ModuleType("google"),
            "google.cloud": _types.ModuleType("google.cloud"),
            "google.cloud.videointelligence": mock_videoint,
        }):
            result = await provider.analyze_video(
                "http://example.com/video.mp4", [AnalysisType.LABEL_DETECTION]
            )

        assert isinstance(result, VideoAnalysisResult)

    async def test_analyze_video_timeout_raises_cloud_ai_error(self):
        provider = _make_provider({"project_id": "p", "timeout": 1})
        mock_video_client = AsyncMock()
        mock_operation = AsyncMock()
        # Simulate timeout
        mock_operation.result = AsyncMock(side_effect=asyncio.TimeoutError())
        mock_video_client.annotate_video = AsyncMock(return_value=mock_operation)
        provider._video_client = mock_video_client

        mock_videoint = MagicMock()
        mock_videoint.Feature.LABEL_DETECTION = "LABEL_DETECTION"
        with patch.dict("sys.modules", {
            "google": _types.ModuleType("google"),
            "google.cloud": _types.ModuleType("google.cloud"),
            "google.cloud.videointelligence": mock_videoint,
        }):
            with pytest.raises(CloudAIError) as exc_info:
                await provider.analyze_video(
                    "http://example.com/video.mp4", [AnalysisType.LABEL_DETECTION]
                )
        assert "timed out" in str(exc_info.value).lower()

    async def test_analyze_video_quota_exceeded_raises_rate_limit_error(self):
        provider = _make_provider()
        mock_video_client = AsyncMock()
        mock_operation = AsyncMock()
        mock_operation.result = AsyncMock(side_effect=Exception("QUOTA_EXCEEDED: daily limit reached"))
        mock_video_client.annotate_video = AsyncMock(return_value=mock_operation)
        provider._video_client = mock_video_client

        mock_videoint = MagicMock()
        mock_videoint.Feature.LABEL_DETECTION = "LABEL_DETECTION"
        with patch.dict("sys.modules", {
            "google": _types.ModuleType("google"),
            "google.cloud": _types.ModuleType("google.cloud"),
            "google.cloud.videointelligence": mock_videoint,
        }):
            with pytest.raises(RateLimitError):
                await provider.analyze_video(
                    "http://example.com/video.mp4", [AnalysisType.LABEL_DETECTION]
                )

    async def test_analyze_video_generic_error_raises_cloud_ai_error(self):
        provider = _make_provider()
        mock_video_client = AsyncMock()
        mock_operation = AsyncMock()
        mock_operation.result = AsyncMock(side_effect=Exception("some generic failure"))
        mock_video_client.annotate_video = AsyncMock(return_value=mock_operation)
        provider._video_client = mock_video_client

        mock_videoint = MagicMock()
        mock_videoint.Feature.LABEL_DETECTION = "LABEL_DETECTION"
        with patch.dict("sys.modules", {
            "google": _types.ModuleType("google"),
            "google.cloud": _types.ModuleType("google.cloud"),
            "google.cloud.videointelligence": mock_videoint,
        }):
            with pytest.raises(CloudAIError):
                await provider.analyze_video(
                    "http://example.com/video.mp4", [AnalysisType.LABEL_DETECTION]
                )

    async def test_analyze_video_initializes_if_client_none(self):
        provider = _make_provider()
        mock_video_client = AsyncMock()
        mock_ann = _make_video_annotation_result()
        mock_api_result = MagicMock()
        mock_api_result.annotation_results = [mock_ann]
        mock_operation = AsyncMock()
        mock_operation.result = AsyncMock(return_value=mock_api_result)
        mock_video_client.annotate_video = AsyncMock(return_value=mock_operation)

        async def _fake_init():
            provider._video_client = mock_video_client

        mock_videoint = MagicMock()
        mock_videoint.Feature.LABEL_DETECTION = "LABEL_DETECTION"
        with patch.dict("sys.modules", {
            "google": _types.ModuleType("google"),
            "google.cloud": _types.ModuleType("google.cloud"),
            "google.cloud.videointelligence": mock_videoint,
        }), patch.object(provider, 'initialize', side_effect=_fake_init):
            result = await provider.analyze_video(
                "http://example.com/video.mp4", [AnalysisType.LABEL_DETECTION]
            )

        assert isinstance(result, VideoAnalysisResult)

    async def test_analyze_video_passes_location_id(self):
        provider = _make_provider({"project_id": "p", "location_id": "eu-west1"})
        mock_video_client = AsyncMock()
        mock_ann = _make_video_annotation_result()
        mock_api_result = MagicMock()
        mock_api_result.annotation_results = [mock_ann]
        mock_operation = AsyncMock()
        mock_operation.result = AsyncMock(return_value=mock_api_result)
        mock_video_client.annotate_video = AsyncMock(return_value=mock_operation)
        provider._video_client = mock_video_client

        mock_videoint = MagicMock()
        mock_videoint.Feature.LABEL_DETECTION = "LABEL_DETECTION"
        with patch.dict("sys.modules", {
            "google": _types.ModuleType("google"),
            "google.cloud": _types.ModuleType("google.cloud"),
            "google.cloud.videointelligence": mock_videoint,
        }):
            await provider.analyze_video(
                "http://example.com/video.mp4", [AnalysisType.LABEL_DETECTION]
            )

        call_kwargs = mock_video_client.annotate_video.call_args[1]
        req = call_kwargs.get('request', {})
        assert req.get('location_id') == "eu-west1"


# ===========================================================================
# analyze_image (integration-style)
# ===========================================================================


class TestGoogleCloudAIAnalyzeImage:
    def _setup_vision_modules(self, mock_response):
        mock_image_cls = MagicMock()
        mock_image_instance = MagicMock()
        mock_image_instance.source = MagicMock()
        mock_image_cls.return_value = mock_image_instance
        mock_feature_type = MagicMock()
        mock_feature_type.LABEL_DETECTION = "LABEL_DETECTION"
        mock_feature_cls = MagicMock()
        mock_feature_cls.Type = mock_feature_type
        mock_vision = MagicMock()
        mock_vision.Image = mock_image_cls
        mock_vision.Feature = mock_feature_cls
        return mock_vision

    async def test_analyze_image_returns_result(self):
        provider = _make_provider()
        mock_response = _make_vision_response()
        mock_vision_client = AsyncMock()
        mock_vision_client.annotate_image = AsyncMock(return_value=mock_response)
        provider._vision_client = mock_vision_client
        mock_vision = self._setup_vision_modules(mock_response)

        with patch.dict("sys.modules", {
            "google": _types.ModuleType("google"),
            "google.cloud": _types.ModuleType("google.cloud"),
            "google.cloud.vision": mock_vision,
        }):
            result = await provider.analyze_image(
                "http://example.com/img.jpg", [AnalysisType.LABEL_DETECTION]
            )

        assert isinstance(result, VideoAnalysisResult)

    async def test_analyze_image_raises_cloud_ai_error_on_failure(self):
        provider = _make_provider()
        mock_vision_client = AsyncMock()
        mock_vision_client.annotate_image = AsyncMock(side_effect=Exception("api error"))
        provider._vision_client = mock_vision_client
        mock_vision = self._setup_vision_modules(MagicMock())

        with patch.dict("sys.modules", {
            "google": _types.ModuleType("google"),
            "google.cloud": _types.ModuleType("google.cloud"),
            "google.cloud.vision": mock_vision,
        }):
            with pytest.raises(CloudAIError):
                await provider.analyze_image("http://example.com/img.jpg", [AnalysisType.LABEL_DETECTION])

    async def test_analyze_image_initializes_if_client_none(self):
        provider = _make_provider()
        mock_response = _make_vision_response()
        mock_vision_client = AsyncMock()
        mock_vision_client.annotate_image = AsyncMock(return_value=mock_response)
        mock_vision = self._setup_vision_modules(mock_response)

        async def _fake_init():
            provider._vision_client = mock_vision_client

        with patch.dict("sys.modules", {
            "google": _types.ModuleType("google"),
            "google.cloud": _types.ModuleType("google.cloud"),
            "google.cloud.vision": mock_vision,
        }), patch.object(provider, 'initialize', side_effect=_fake_init):
            result = await provider.analyze_image(
                "http://example.com/img.jpg", [AnalysisType.LABEL_DETECTION]
            )

        assert isinstance(result, VideoAnalysisResult)

    async def test_analyze_image_sets_uri_for_http(self):
        provider = _make_provider()
        mock_response = _make_vision_response()
        mock_vision_client = AsyncMock()
        mock_vision_client.annotate_image = AsyncMock(return_value=mock_response)
        provider._vision_client = mock_vision_client
        mock_vision = self._setup_vision_modules(mock_response)

        with patch.dict("sys.modules", {
            "google": _types.ModuleType("google"),
            "google.cloud": _types.ModuleType("google.cloud"),
            "google.cloud.vision": mock_vision,
        }):
            await provider.analyze_image("https://example.com/img.jpg", [AnalysisType.LABEL_DETECTION])

        # The image.source.image_uri should be set
        image_instance = mock_vision.Image.return_value
        assert image_instance.source.image_uri == "https://example.com/img.jpg"


# ===========================================================================
# get_service_status
# ===========================================================================


class TestGoogleCloudAIGetServiceStatus:
    async def test_healthy_status_returned(self):
        provider = _make_provider()
        mock_vision_client = AsyncMock()
        mock_vision_client.annotate_image = AsyncMock(side_effect=Exception("empty image"))
        provider._vision_client = mock_vision_client
        mock_vision = MagicMock()
        mock_image_instance = MagicMock()
        mock_vision.Image.return_value = mock_image_instance
        mock_vision.Feature.Type.LABEL_DETECTION = "LABEL_DETECTION"

        with patch.dict("sys.modules", {
            "google": _types.ModuleType("google"),
            "google.cloud": _types.ModuleType("google.cloud"),
            "google.cloud.vision": mock_vision,
        }):
            status = await provider.get_service_status()

        assert status['status'] == 'healthy'

    async def test_healthy_has_response_time(self):
        provider = _make_provider()
        mock_vision_client = AsyncMock()
        mock_vision_client.annotate_image = AsyncMock(return_value=_make_vision_response())
        provider._vision_client = mock_vision_client
        mock_vision = MagicMock()
        mock_vision.Image.return_value = MagicMock()
        mock_vision.Feature.Type.LABEL_DETECTION = "LABEL_DETECTION"

        with patch.dict("sys.modules", {
            "google": _types.ModuleType("google"),
            "google.cloud": _types.ModuleType("google.cloud"),
            "google.cloud.vision": mock_vision,
        }):
            status = await provider.get_service_status()

        assert status['response_time'] >= 0

    async def test_unhealthy_when_initialize_fails(self):
        provider = _make_provider()

        async def _bad_init():
            raise Exception("cannot authenticate")

        mock_vision = MagicMock()
        mock_vision.Image.return_value = MagicMock()
        mock_vision.Feature.Type.LABEL_DETECTION = "LABEL_DETECTION"

        with patch.dict("sys.modules", {
            "google": _types.ModuleType("google"),
            "google.cloud": _types.ModuleType("google.cloud"),
            "google.cloud.vision": mock_vision,
        }), patch.object(provider, 'initialize', side_effect=_bad_init):
            status = await provider.get_service_status()

        assert status['status'] == 'unhealthy'
        assert 'error' in status
        assert 'cannot authenticate' in status['error']


# ===========================================================================
# async context manager (inherited)
# ===========================================================================


class TestGoogleCloudAIContextManager:
    async def test_aenter_calls_initialize(self):
        provider = _make_provider()
        with patch.object(provider, 'initialize', new=AsyncMock()) as mock_init:
            await provider.__aenter__()
            mock_init.assert_called_once()

    async def test_aenter_returns_provider(self):
        provider = _make_provider()
        with patch.object(provider, 'initialize', new=AsyncMock()):
            result = await provider.__aenter__()
        assert result is provider

    async def test_aexit_calls_cleanup(self):
        provider = _make_provider()
        with patch.object(provider, 'initialize', new=AsyncMock()), \
             patch.object(provider, 'cleanup', new=AsyncMock()) as mock_cleanup:
            await provider.__aenter__()
            await provider.__aexit__(None, None, None)
            mock_cleanup.assert_called_once()


# ===========================================================================
# estimate_cost (inherited from BaseCloudAI)
# ===========================================================================


class TestGoogleCloudAIEstimateCost:
    def test_cost_positive_for_nonzero_duration(self):
        provider = _make_provider()
        cost = provider.estimate_cost(60.0, [AnalysisType.LABEL_DETECTION])
        assert cost > 0

    def test_cost_scales_with_analysis_types(self):
        provider = _make_provider()
        cost1 = provider.estimate_cost(60.0, [AnalysisType.LABEL_DETECTION])
        cost2 = provider.estimate_cost(60.0, [AnalysisType.LABEL_DETECTION, AnalysisType.OCR])
        assert cost2 > cost1

    def test_zero_duration_zero_cost(self):
        provider = _make_provider()
        cost = provider.estimate_cost(0.0, [AnalysisType.LABEL_DETECTION])
        assert cost == pytest.approx(0.0)


# ===========================================================================
# Local image reads must not block the event loop
# ===========================================================================


class _ThreadRecordingOpen:
    """Wrap ``builtins.open`` and record which thread opened a target path.

    Off-loop execution is asserted by *thread identity* rather than elapsed
    wall-clock time, which is flaky on loaded CI runners. Only calls for the
    target path are recorded so unrelated ``open`` traffic (logging, coverage)
    cannot contaminate the result.
    """

    def __init__(self, target):
        self._real_open = builtins.open
        self._target = str(target)
        self.threads: list[int] = []

    def __call__(self, file, *args, **kwargs):
        if str(file) == self._target:
            self.threads.append(threading.get_ident())
        return self._real_open(file, *args, **kwargs)


class TestGoogleCloudImageReadOffEventLoop:
    def _vision_modules(self):
        mock_image_instance = MagicMock()
        mock_image_instance.source = MagicMock()
        mock_image_cls = MagicMock(return_value=mock_image_instance)
        mock_feature_type = MagicMock()
        mock_feature_type.LABEL_DETECTION = "LABEL_DETECTION"
        mock_feature_cls = MagicMock()
        mock_feature_cls.Type = mock_feature_type
        mock_vision = MagicMock()
        mock_vision.Image = mock_image_cls
        mock_vision.Feature = mock_feature_cls
        return mock_vision

    def _patched_modules(self, mock_vision):
        return patch.dict("sys.modules", {
            "google": _types.ModuleType("google"),
            "google.cloud": _types.ModuleType("google.cloud"),
            "google.cloud.vision": mock_vision,
        })

    def _client(self):
        client = AsyncMock()
        client.annotate_image = AsyncMock(return_value=_make_vision_response())
        return client

    async def test_local_file_read_runs_on_worker_thread(self, tmp_path):
        provider = _make_provider()
        provider._vision_client = self._client()
        img_file = tmp_path / "frame.jpg"
        img_file.write_bytes(b"\x89PNG\r\n")
        mock_vision = self._vision_modules()
        recorder = _ThreadRecordingOpen(img_file)
        loop_thread = threading.get_ident()

        with self._patched_modules(mock_vision), patch("builtins.open", recorder):
            await provider.analyze_image(str(img_file), [AnalysisType.LABEL_DETECTION])

        assert mock_vision.Image.return_value.content == b"\x89PNG\r\n"
        assert recorder.threads, "expected the provider to open the local image file"
        assert loop_thread not in recorder.threads, (
            "local image bytes were read on the event loop thread; the read must "
            "be offloaded to a worker thread"
        )

    async def test_http_url_performs_no_disk_read(self, tmp_path):
        """The URI branch must remain untouched: Vision fetches it directly."""
        provider = _make_provider()
        provider._vision_client = self._client()
        decoy = tmp_path / "unused.jpg"
        decoy.write_bytes(b"\x00")
        mock_vision = self._vision_modules()
        recorder = _ThreadRecordingOpen(decoy)

        with self._patched_modules(mock_vision), patch("builtins.open", recorder):
            await provider.analyze_image(
                "https://example.com/img.jpg", [AnalysisType.LABEL_DETECTION]
            )

        assert recorder.threads == []
        assert mock_vision.Image.return_value.source.image_uri == "https://example.com/img.jpg"
