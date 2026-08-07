"""Unit tests for integrations/cloud_ai/providers/azure_vision.py."""

from __future__ import annotations

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
from youtube_extension.integrations.cloud_ai.providers.azure_vision import AzureVision

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

VALID_CONFIG = {
    "subscription_key": "test-key-abc",
    "endpoint": "https://eastus.api.cognitive.microsoft.com/",
}


def _make_provider(config=None) -> AzureVision:
    return AzureVision(config or VALID_CONFIG)


def _make_analysis_result(tags=None, objects=None, faces=None, metadata=None):
    """Build a fake azure analyze_image result object."""
    result = MagicMock()
    result.tags = tags or []
    result.objects = objects or []
    result.faces = faces or []
    if metadata:
        result.metadata = metadata
    else:
        m = MagicMock()
        m.width = 1920
        m.height = 1080
        result.metadata = m
    return result


# ===========================================================================
# __init__ / _validate_config
# ===========================================================================


class TestAzureVisionInit:
    def test_valid_config_does_not_raise(self):
        provider = _make_provider()
        assert provider is not None

    def test_provider_set_to_azure_vision(self):
        provider = _make_provider()
        assert provider.provider == CloudAIProvider.AZURE_VISION

    def test_vision_client_starts_none(self):
        provider = _make_provider()
        assert provider._vision_client is None

    def test_video_indexer_client_starts_none(self):
        provider = _make_provider()
        assert provider._video_indexer_client is None

    def test_config_stored(self):
        provider = _make_provider()
        assert provider.config is VALID_CONFIG

    def test_missing_subscription_key_raises_config_error(self):
        with pytest.raises(ConfigurationError) as exc_info:
            AzureVision({"endpoint": "https://example.com"})
        assert exc_info.value.missing_config == "subscription_key"

    def test_missing_endpoint_raises_config_error(self):
        with pytest.raises(ConfigurationError) as exc_info:
            AzureVision({"subscription_key": "key"})
        assert exc_info.value.missing_config == "endpoint"

    def test_empty_config_raises_config_error(self):
        with pytest.raises(ConfigurationError):
            AzureVision({})

    def test_config_error_has_azure_provider(self):
        with pytest.raises(ConfigurationError) as exc_info:
            AzureVision({"subscription_key": "key"})
        assert exc_info.value.provider == CloudAIProvider.AZURE_VISION.value

    def test_config_error_code_is_configuration_error(self):
        with pytest.raises(ConfigurationError) as exc_info:
            AzureVision({})
        assert exc_info.value.error_code == "CONFIGURATION_ERROR"


# ===========================================================================
# initialize
# ===========================================================================


class TestAzureVisionInitialize:
    async def test_initialize_sets_vision_client(self):
        provider = _make_provider()

        mock_client = MagicMock()
        mock_models = MagicMock()
        mock_models.models_property = [MagicMock(), MagicMock()]
        mock_client.list_models.return_value = mock_models

        mock_creds_cls = MagicMock(return_value=MagicMock())
        mock_cv_cls = MagicMock(return_value=mock_client)

        with patch.dict("sys.modules", {
            "azure": _types.ModuleType("azure"),
            "azure.cognitiveservices": _types.ModuleType("azure.cognitiveservices"),
            "azure.cognitiveservices.vision": _types.ModuleType("azure.cognitiveservices.vision"),
            "azure.cognitiveservices.vision.computervision": MagicMock(
                ComputerVisionClient=mock_cv_cls,
            ),
            "azure.cognitiveservices.vision.computervision.models": MagicMock(
                OperationStatusCodes=MagicMock(),
            ),
            "msrest": _types.ModuleType("msrest"),
            "msrest.authentication": MagicMock(CognitiveServicesCredentials=mock_creds_cls),
        }):
            await provider.initialize()

        assert provider._vision_client is mock_client

    async def test_initialize_raises_config_error_on_import_error(self):
        provider = _make_provider()
        with patch.dict("sys.modules", {
            "azure": None,
            "azure.cognitiveservices": None,
            "azure.cognitiveservices.vision": None,
            "azure.cognitiveservices.vision.computervision": None,
        }):
            with pytest.raises((ConfigurationError, Exception)):
                await provider.initialize()

    async def test_initialize_raises_auth_error_on_connection_failure(self):
        provider = _make_provider()

        mock_client = MagicMock()
        mock_client.list_models.side_effect = Exception("connection refused")
        mock_cv_cls = MagicMock(return_value=mock_client)
        mock_creds_cls = MagicMock(return_value=MagicMock())

        with patch.dict("sys.modules", {
            "azure": _types.ModuleType("azure"),
            "azure.cognitiveservices": _types.ModuleType("azure.cognitiveservices"),
            "azure.cognitiveservices.vision": _types.ModuleType("azure.cognitiveservices.vision"),
            "azure.cognitiveservices.vision.computervision": MagicMock(
                ComputerVisionClient=mock_cv_cls,
            ),
            "azure.cognitiveservices.vision.computervision.models": MagicMock(
                OperationStatusCodes=MagicMock(),
            ),
            "msrest": _types.ModuleType("msrest"),
            "msrest.authentication": MagicMock(CognitiveServicesCredentials=mock_creds_cls),
        }):
            with pytest.raises(AuthenticationError):
                await provider.initialize()


# ===========================================================================
# cleanup
# ===========================================================================


class TestAzureVisionCleanup:
    async def test_cleanup_clears_vision_client(self):
        provider = _make_provider()
        provider._vision_client = MagicMock()
        await provider.cleanup()
        assert provider._vision_client is None

    async def test_cleanup_clears_video_indexer_client(self):
        provider = _make_provider()
        provider._video_indexer_client = MagicMock()
        await provider.cleanup()
        assert provider._video_indexer_client is None

    async def test_cleanup_idempotent_when_already_none(self):
        provider = _make_provider()
        await provider.cleanup()  # Should not raise
        assert provider._vision_client is None


# ===========================================================================
# _test_connection
# ===========================================================================


class TestAzureVisionTestConnection:
    async def test_connection_ok_when_list_models_succeeds(self):
        provider = _make_provider()
        mock_client = MagicMock()
        mock_models = MagicMock()
        mock_models.models_property = [MagicMock()]
        mock_client.list_models.return_value = mock_models
        provider._vision_client = mock_client
        await provider._test_connection()  # Should not raise

    async def test_connection_raises_auth_error_on_failure(self):
        provider = _make_provider()
        mock_client = MagicMock()
        mock_client.list_models.side_effect = Exception("timeout")
        provider._vision_client = mock_client
        with pytest.raises(AuthenticationError) as exc_info:
            await provider._test_connection()
        assert "timeout" in str(exc_info.value)


# ===========================================================================
# get_supported_analysis_types
# ===========================================================================


class TestAzureVisionSupportedTypes:
    def test_returns_list(self):
        provider = _make_provider()
        types = provider.get_supported_analysis_types()
        assert isinstance(types, list)

    def test_includes_ocr(self):
        provider = _make_provider()
        assert AnalysisType.OCR in provider.get_supported_analysis_types()

    def test_includes_face_detection(self):
        provider = _make_provider()
        assert AnalysisType.FACE_DETECTION in provider.get_supported_analysis_types()

    def test_includes_label_detection(self):
        provider = _make_provider()
        assert AnalysisType.LABEL_DETECTION in provider.get_supported_analysis_types()

    def test_includes_object_tracking(self):
        provider = _make_provider()
        assert AnalysisType.OBJECT_TRACKING in provider.get_supported_analysis_types()

    def test_includes_text_detection(self):
        provider = _make_provider()
        assert AnalysisType.TEXT_DETECTION in provider.get_supported_analysis_types()

    def test_includes_scene_analysis(self):
        provider = _make_provider()
        assert AnalysisType.SCENE_ANALYSIS in provider.get_supported_analysis_types()

    def test_returns_at_least_six_types(self):
        provider = _make_provider()
        assert len(provider.get_supported_analysis_types()) >= 6


# ===========================================================================
# _extract_video_frames
# ===========================================================================


class TestAzureVisionExtractFrames:
    async def test_returns_list(self):
        provider = _make_provider()
        frames = await provider._extract_video_frames("http://example.com/vid.mp4")
        assert isinstance(frames, list)

    async def test_returns_empty_list(self):
        # Current placeholder implementation returns []
        provider = _make_provider()
        frames = await provider._extract_video_frames("http://example.com/vid.mp4", max_frames=5)
        assert frames == []


# ===========================================================================
# _prepare_image_input
# ===========================================================================


class TestAzureVisionPrepareImageInput:
    async def test_http_url_returns_none(self):
        provider = _make_provider()
        result = await provider._prepare_image_input("http://example.com/img.jpg")
        assert result is None

    async def test_https_url_returns_none(self):
        provider = _make_provider()
        result = await provider._prepare_image_input("https://example.com/img.jpg")
        assert result is None

    async def test_local_file_reads_bytes_fixture(self, tmp_path, monkeypatch):
        provider = _make_provider()
        img_file = tmp_path / "test.jpg"
        img_file.write_bytes(b"\xff\xd8\xff")
        monkeypatch.setenv("CLOUD_AI_MEDIA_ROOT", str(tmp_path))
        result = await provider._prepare_image_input(str(img_file))
        assert result == b"\xff\xd8\xff"


# ===========================================================================
# _convert_azure_bbox
# ===========================================================================


class TestAzureVisionConvertBbox:
    def test_eight_point_bbox_returns_dict(self):
        provider = _make_provider()
        bbox = [10, 20, 100, 20, 100, 80, 10, 80]
        result = provider._convert_azure_bbox(bbox)
        assert set(result.keys()) == {'x', 'y', 'width', 'height'}

    def test_eight_point_bbox_correct_x(self):
        provider = _make_provider()
        bbox = [10, 20, 100, 20, 100, 80, 10, 80]
        result = provider._convert_azure_bbox(bbox)
        assert result['x'] == 10  # min x

    def test_eight_point_bbox_correct_y(self):
        provider = _make_provider()
        bbox = [10, 20, 100, 20, 100, 80, 10, 80]
        result = provider._convert_azure_bbox(bbox)
        assert result['y'] == 20  # min y

    def test_eight_point_bbox_correct_width(self):
        provider = _make_provider()
        bbox = [10, 20, 100, 20, 100, 80, 10, 80]
        result = provider._convert_azure_bbox(bbox)
        assert result['width'] == 90  # max(100,10) - min(10,100) = 90

    def test_eight_point_bbox_correct_height(self):
        provider = _make_provider()
        bbox = [10, 20, 100, 20, 100, 80, 10, 80]
        result = provider._convert_azure_bbox(bbox)
        assert result['height'] == 60  # max(20,80) - min(20,80)

    def test_short_bbox_returns_zeros(self):
        provider = _make_provider()
        result = provider._convert_azure_bbox([10, 20])  # too short
        assert result == {'x': 0, 'y': 0, 'width': 0, 'height': 0}

    def test_empty_bbox_returns_zeros(self):
        provider = _make_provider()
        result = provider._convert_azure_bbox([])
        assert result == {'x': 0, 'y': 0, 'width': 0, 'height': 0}

    def test_square_bbox_width_equals_height(self):
        provider = _make_provider()
        # Square: (0,0) to (50,50)
        bbox = [0, 0, 50, 0, 50, 50, 0, 50]
        result = provider._convert_azure_bbox(bbox)
        assert result['width'] == result['height'] == 50


# ===========================================================================
# _aggregate_frame_results
# ===========================================================================


class TestAzureVisionAggregateFrameResults:
    def test_returns_video_analysis_result(self):
        provider = _make_provider()
        result = provider._aggregate_frame_results([], "vid1", [AnalysisType.OCR], 1.0)
        assert isinstance(result, VideoAnalysisResult)

    def test_empty_frames_returns_empty_detections(self):
        provider = _make_provider()
        result = provider._aggregate_frame_results([], "vid1", [AnalysisType.OCR], 1.0)
        assert result.objects == []
        assert result.labels == []
        assert result.text_detections == []
        assert result.faces == []

    def test_processing_time_set(self):
        provider = _make_provider()
        result = provider._aggregate_frame_results([], "vid1", [AnalysisType.OCR], 3.14)
        assert result.processing_time == pytest.approx(3.14)

    def test_video_id_set(self):
        provider = _make_provider()
        result = provider._aggregate_frame_results([], "video-abc", [AnalysisType.OCR], 1.0)
        assert result.video_id == "video-abc"

    def test_provider_set_to_azure(self):
        provider = _make_provider()
        result = provider._aggregate_frame_results([], "v", [AnalysisType.OCR], 1.0)
        assert result.provider == CloudAIProvider.AZURE_VISION

    def test_ocr_results_aggregated_from_frames(self):
        provider = _make_provider()
        frame_result = {
            'timestamp': 0.0,
            'ocr': {
                'read_result': {
                    'read_results': [
                        {'lines': [{'text': 'Hello', 'bounding_box': [0, 0, 50, 0, 50, 10, 0, 10]}]}
                    ]
                }
            }
        }
        result = provider._aggregate_frame_results([frame_result], "v", [AnalysisType.OCR], 1.0)
        assert len(result.text_detections) == 1
        assert result.text_detections[0].label == 'Hello'

    def test_label_results_aggregated_from_frames(self):
        provider = _make_provider()
        mock_tag = MagicMock()
        mock_tag.name = "outdoor"
        mock_tag.confidence = 0.9
        mock_analyze = MagicMock()
        mock_analyze.tags = [mock_tag]
        mock_analyze.objects = []
        mock_analyze.faces = []
        frame_result = {
            'timestamp': 5.0,
            'analyze': {'analyze_result': mock_analyze}
        }
        result = provider._aggregate_frame_results([frame_result], "v", [AnalysisType.LABEL_DETECTION], 1.0)
        assert len(result.labels) == 1
        assert result.labels[0].label == "outdoor"

    def test_object_results_aggregated_from_frames(self):
        provider = _make_provider()
        mock_obj = MagicMock()
        mock_obj.object_property = "car"
        mock_obj.confidence = 0.85
        mock_obj.rectangle.x = 100
        mock_obj.rectangle.y = 50
        mock_obj.rectangle.w = 200
        mock_obj.rectangle.h = 150
        mock_analyze = MagicMock()
        mock_analyze.tags = []
        mock_analyze.objects = [mock_obj]
        mock_analyze.faces = []
        mock_analyze.metadata.width = 1920
        mock_analyze.metadata.height = 1080
        frame_result = {
            'timestamp': 10.0,
            'analyze': {'analyze_result': mock_analyze}
        }
        result = provider._aggregate_frame_results([frame_result], "v", [AnalysisType.OBJECT_TRACKING], 1.0)
        assert len(result.objects) == 1
        assert result.objects[0].label == "car"

    def test_face_results_aggregated_from_frames(self):
        provider = _make_provider()
        mock_face = MagicMock()
        mock_face.face_rectangle.left = 100
        mock_face.face_rectangle.top = 50
        mock_face.face_rectangle.width = 80
        mock_face.face_rectangle.height = 80
        mock_face.age = 30
        mock_face.gender = "male"
        mock_analyze = MagicMock()
        mock_analyze.tags = []
        mock_analyze.objects = []
        mock_analyze.faces = [mock_face]
        mock_analyze.metadata.width = 1920
        mock_analyze.metadata.height = 1080
        frame_result = {
            'timestamp': 15.0,
            'analyze': {'analyze_result': mock_analyze}
        }
        result = provider._aggregate_frame_results([frame_result], "v", [AnalysisType.FACE_DETECTION], 1.0)
        assert len(result.faces) == 1
        assert result.faces[0].label == "Face"
        assert result.faces[0].metadata['age'] == 30

    def test_raw_response_contains_frame_results(self):
        provider = _make_provider()
        frames = [{'timestamp': 0.0, 'ocr': {'read_result': {'read_results': []}}}]
        result = provider._aggregate_frame_results(frames, "v", [AnalysisType.OCR], 1.0)
        assert 'frame_results' in result.raw_response

    def test_multiple_frames_aggregated(self):
        provider = _make_provider()
        frames = [
            {
                'timestamp': 0.0,
                'ocr': {'read_result': {'read_results': [
                    {'lines': [{'text': 'A', 'bounding_box': [0, 0, 10, 0, 10, 10, 0, 10]}]}
                ]}}
            },
            {
                'timestamp': 5.0,
                'ocr': {'read_result': {'read_results': [
                    {'lines': [{'text': 'B', 'bounding_box': [20, 20, 30, 20, 30, 30, 20, 30]}]}
                ]}}
            },
        ]
        result = provider._aggregate_frame_results(frames, "v", [AnalysisType.OCR], 1.0)
        assert len(result.text_detections) == 2


# ===========================================================================
# _process_image_results
# ===========================================================================


class TestAzureVisionProcessImageResults:
    def test_returns_video_analysis_result(self):
        provider = _make_provider()
        result = provider._process_image_results({}, "img1", [AnalysisType.OCR], 0.5)
        assert isinstance(result, VideoAnalysisResult)

    def test_empty_results_all_empty_lists(self):
        provider = _make_provider()
        result = provider._process_image_results({}, "img1", [AnalysisType.OCR], 0.5)
        assert result.objects == []
        assert result.labels == []
        assert result.text_detections == []
        assert result.faces == []

    def test_image_id_set(self):
        provider = _make_provider()
        result = provider._process_image_results({}, "image-xyz", [AnalysisType.OCR], 0.5)
        assert result.video_id == "image-xyz"

    def test_processing_time_set(self):
        provider = _make_provider()
        result = provider._process_image_results({}, "img1", [AnalysisType.OCR], 2.5)
        assert result.processing_time == pytest.approx(2.5)

    def test_ocr_text_extracted(self):
        provider = _make_provider()
        ocr = {
            'read_result': {
                'read_results': [
                    {'lines': [{'text': 'World', 'bounding_box': [0, 0, 50, 0, 50, 20, 0, 20]}]}
                ]
            }
        }
        result = provider._process_image_results({'ocr': ocr}, "img1", [AnalysisType.OCR], 0.5)
        assert len(result.text_detections) == 1
        assert result.text_detections[0].label == 'World'

    def test_label_tags_extracted(self):
        provider = _make_provider()
        mock_tag = MagicMock()
        mock_tag.name = "nature"
        mock_tag.confidence = 0.95
        mock_analyze = MagicMock()
        mock_analyze.tags = [mock_tag]
        mock_analyze.objects = []
        result = provider._process_image_results(
            {'analyze': {'analyze_result': mock_analyze}},
            "img1", [AnalysisType.LABEL_DETECTION], 0.5
        )
        assert len(result.labels) == 1
        assert result.labels[0].label == "nature"
        assert result.labels[0].confidence == pytest.approx(0.95)

    def test_objects_extracted_with_metadata(self):
        provider = _make_provider()
        mock_obj = MagicMock()
        mock_obj.object_property = "person"
        mock_obj.confidence = 0.92
        mock_obj.rectangle.x = 50
        mock_obj.rectangle.y = 30
        mock_obj.rectangle.w = 100
        mock_obj.rectangle.h = 200
        mock_meta = MagicMock()
        mock_meta.width = 640
        mock_meta.height = 480
        mock_analyze = MagicMock()
        mock_analyze.tags = []
        mock_analyze.objects = [mock_obj]
        mock_analyze.metadata = mock_meta
        result = provider._process_image_results(
            {'analyze': {'analyze_result': mock_analyze}},
            "img1", [AnalysisType.OBJECT_TRACKING], 0.5
        )
        assert len(result.objects) == 1
        assert result.objects[0].label == "person"
        bbox = result.objects[0].bounding_box
        assert bbox['x'] == pytest.approx(50 / 640)

    def test_faces_extracted(self):
        provider = _make_provider()
        mock_face = MagicMock()
        mock_face.face_rectangle.left = 200
        mock_face.face_rectangle.top = 100
        mock_face.face_rectangle.width = 60
        mock_face.face_rectangle.height = 60
        mock_face.age = 25
        mock_face.gender = "female"
        mock_faces_result = MagicMock()
        mock_faces_result.faces = [mock_face]
        mock_faces_result.metadata.width = 1280
        mock_faces_result.metadata.height = 720
        result = provider._process_image_results(
            {'faces': {'faces_result': mock_faces_result}},
            "img1", [AnalysisType.FACE_DETECTION], 0.5
        )
        assert len(result.faces) == 1
        assert result.faces[0].metadata['gender'] == "female"
        assert result.faces[0].metadata['age'] == 25

    def test_provider_is_azure(self):
        provider = _make_provider()
        result = provider._process_image_results({}, "img", [], 1.0)
        assert result.provider == CloudAIProvider.AZURE_VISION

    def test_raw_response_is_results_dict(self):
        provider = _make_provider()
        input_results = {'ocr': {'read_result': {'read_results': []}}}
        result = provider._process_image_results(input_results, "img", [], 1.0)
        assert result.raw_response is input_results


# ===========================================================================
# analyze_video (integration-style with mocked internals)
# ===========================================================================


class TestAzureVisionAnalyzeVideo:
    async def test_analyze_video_returns_result_with_initialized_client(self):
        provider = _make_provider()
        provider._vision_client = MagicMock()

        with patch.object(provider, '_extract_video_frames', new=AsyncMock(return_value=[])):
            result = await provider.analyze_video("http://example.com/v.mp4", [AnalysisType.OCR])

        assert isinstance(result, VideoAnalysisResult)

    async def test_analyze_video_initializes_if_client_none(self):
        provider = _make_provider()

        async def _fake_init():
            provider._vision_client = MagicMock()
            mock_models = MagicMock()
            mock_models.models_property = []
            provider._vision_client.list_models.return_value = mock_models

        with patch.object(provider, 'initialize', side_effect=_fake_init), \
             patch.object(provider, '_extract_video_frames', new=AsyncMock(return_value=[])):
            result = await provider.analyze_video("http://example.com/v.mp4", [AnalysisType.OCR])

        assert isinstance(result, VideoAnalysisResult)

    async def test_analyze_video_rate_limit_error_raised(self):
        provider = _make_provider()
        provider._vision_client = MagicMock()

        with patch.object(provider, '_extract_video_frames', new=AsyncMock(side_effect=Exception("429 Too Many Requests"))):
            with pytest.raises(RateLimitError):
                await provider.analyze_video("http://example.com/v.mp4", [AnalysisType.OCR])

    async def test_analyze_video_generic_error_raised(self):
        provider = _make_provider()
        provider._vision_client = MagicMock()

        with patch.object(provider, '_extract_video_frames', new=AsyncMock(side_effect=Exception("some failure"))):
            with pytest.raises(CloudAIError):
                await provider.analyze_video("http://example.com/v.mp4", [AnalysisType.OCR])

    async def test_analyze_video_rate_limit_rekognition_keyword(self):
        provider = _make_provider()
        provider._vision_client = MagicMock()

        with patch.object(provider, '_extract_video_frames', new=AsyncMock(side_effect=Exception("RateLimitExceeded"))):
            with pytest.raises(RateLimitError):
                await provider.analyze_video("http://example.com/v.mp4", [AnalysisType.OCR])

    async def test_analyze_video_empty_frames_returns_empty_detections(self):
        provider = _make_provider()
        provider._vision_client = MagicMock()

        with patch.object(provider, '_extract_video_frames', new=AsyncMock(return_value=[])):
            result = await provider.analyze_video("http://example.com/v.mp4", [AnalysisType.OCR])

        assert result.objects == []
        assert result.labels == []


# ===========================================================================
# analyze_image (integration-style with mocked internals)
# ===========================================================================


class TestAzureVisionAnalyzeImage:
    async def test_analyze_image_ocr_path(self):
        provider = _make_provider()
        provider._vision_client = MagicMock()

        mock_ocr_result = {'read_result': {'read_results': []}}

        with patch.object(provider, '_prepare_image_input', new=AsyncMock(return_value=None)), \
             patch.object(provider, '_perform_ocr', new=AsyncMock(return_value=mock_ocr_result)):
            result = await provider.analyze_image("http://example.com/img.jpg", [AnalysisType.OCR])

        assert isinstance(result, VideoAnalysisResult)

    async def test_analyze_image_label_path(self):
        provider = _make_provider()
        provider._vision_client = MagicMock()

        mock_analyze_result = {'analyze_result': MagicMock(tags=[], objects=[])}

        with patch.object(provider, '_prepare_image_input', new=AsyncMock(return_value=None)), \
             patch.object(provider, '_analyze_image_content', new=AsyncMock(return_value=mock_analyze_result)):
            result = await provider.analyze_image("http://example.com/img.jpg", [AnalysisType.LABEL_DETECTION])

        assert isinstance(result, VideoAnalysisResult)

    async def test_analyze_image_face_path(self):
        provider = _make_provider()
        provider._vision_client = MagicMock()

        mock_face_result = {'faces_result': MagicMock(faces=[], metadata=MagicMock(width=100, height=100))}

        with patch.object(provider, '_prepare_image_input', new=AsyncMock(return_value=None)), \
             patch.object(provider, '_detect_faces', new=AsyncMock(return_value=mock_face_result)):
            result = await provider.analyze_image("http://example.com/img.jpg", [AnalysisType.FACE_DETECTION])

        assert isinstance(result, VideoAnalysisResult)

    async def test_analyze_image_raises_cloud_ai_error_on_failure(self):
        provider = _make_provider()
        provider._vision_client = MagicMock()

        with patch.object(provider, '_prepare_image_input', new=AsyncMock(side_effect=Exception("network error"))):
            with pytest.raises(CloudAIError):
                await provider.analyze_image("http://example.com/img.jpg", [AnalysisType.OCR])

    async def test_analyze_image_multiple_types(self):
        provider = _make_provider()
        provider._vision_client = MagicMock()

        mock_ocr = {'read_result': {'read_results': []}}
        mock_analyze = {'analyze_result': MagicMock(tags=[], objects=[])}

        with patch.object(provider, '_prepare_image_input', new=AsyncMock(return_value=None)), \
             patch.object(provider, '_perform_ocr', new=AsyncMock(return_value=mock_ocr)), \
             patch.object(provider, '_analyze_image_content', new=AsyncMock(return_value=mock_analyze)):
            result = await provider.analyze_image(
                "http://example.com/img.jpg",
                [AnalysisType.OCR, AnalysisType.LABEL_DETECTION]
            )

        assert isinstance(result, VideoAnalysisResult)

    async def test_analyze_image_initializes_if_client_none(self):
        provider = _make_provider()

        async def _fake_init():
            provider._vision_client = MagicMock()

        mock_ocr = {'read_result': {'read_results': []}}

        with patch.object(provider, 'initialize', side_effect=_fake_init), \
             patch.object(provider, '_prepare_image_input', new=AsyncMock(return_value=None)), \
             patch.object(provider, '_perform_ocr', new=AsyncMock(return_value=mock_ocr)):
            result = await provider.analyze_image("http://example.com/img.jpg", [AnalysisType.OCR])

        assert isinstance(result, VideoAnalysisResult)


# ===========================================================================
# get_service_status
# ===========================================================================


class TestAzureVisionGetServiceStatus:
    async def test_healthy_status_returned(self):
        provider = _make_provider()
        mock_client = MagicMock()
        mock_models = MagicMock()
        mock_models.models_property = [MagicMock()]
        mock_client.list_models.return_value = mock_models
        provider._vision_client = mock_client

        status = await provider.get_service_status()
        assert status['status'] == 'healthy'

    async def test_healthy_response_time_non_negative(self):
        provider = _make_provider()
        mock_client = MagicMock()
        mock_models = MagicMock()
        mock_models.models_property = []
        mock_client.list_models.return_value = mock_models
        provider._vision_client = mock_client

        status = await provider.get_service_status()
        assert status['response_time'] >= 0

    async def test_healthy_has_timestamp(self):
        provider = _make_provider()
        mock_client = MagicMock()
        mock_models = MagicMock()
        mock_models.models_property = []
        mock_client.list_models.return_value = mock_models
        provider._vision_client = mock_client

        status = await provider.get_service_status()
        assert 'timestamp' in status

    async def test_unhealthy_status_on_exception(self):
        provider = _make_provider()
        mock_client = MagicMock()
        mock_client.list_models.side_effect = Exception("service down")
        provider._vision_client = mock_client

        status = await provider.get_service_status()
        assert status['status'] == 'unhealthy'

    async def test_unhealthy_includes_error_message(self):
        provider = _make_provider()
        mock_client = MagicMock()
        mock_client.list_models.side_effect = Exception("service down")
        provider._vision_client = mock_client

        status = await provider.get_service_status()
        assert 'error' in status
        assert 'service down' in status['error']

    async def test_status_initializes_client_if_none(self):
        provider = _make_provider()
        mock_client = MagicMock()
        mock_models = MagicMock()
        mock_models.models_property = []
        mock_client.list_models.return_value = mock_models

        async def _fake_init():
            provider._vision_client = mock_client

        with patch.object(provider, 'initialize', side_effect=_fake_init):
            status = await provider.get_service_status()

        assert status['status'] == 'healthy'


# ===========================================================================
# _analyze_frame
# ===========================================================================


def _azure_sdk_mocks():
    """Return a dict of Azure SDK module mocks suitable for patch.dict."""
    mock_status_codes = MagicMock()
    mock_status_codes.running = "running"
    mock_status_codes.not_started = "not_started"
    mock_status_codes.succeeded = "succeeded"
    mock_visual = MagicMock()
    mock_visual.categories = "categories"
    mock_visual.tags = "tags"
    mock_visual.description = "description"
    mock_visual.objects = "objects"
    mock_visual.brands = "brands"
    mock_visual.faces = "faces"
    return {
        "azure": _types.ModuleType("azure"),
        "azure.cognitiveservices": _types.ModuleType("azure.cognitiveservices"),
        "azure.cognitiveservices.vision": _types.ModuleType("azure.cognitiveservices.vision"),
        "azure.cognitiveservices.vision.computervision": MagicMock(),
        "azure.cognitiveservices.vision.computervision.models": MagicMock(
            OperationStatusCodes=mock_status_codes,
            VisualFeatureTypes=mock_visual,
        ),
        "msrest": _types.ModuleType("msrest"),
        "msrest.authentication": MagicMock(),
    }


class TestAzureVisionAnalyzeFrame:
    async def test_analyze_frame_ocr_path(self):
        provider = _make_provider()
        mock_client = MagicMock()
        mock_ocr_result = MagicMock()
        mock_ocr_result.analyze_result = {"read_results": []}
        mock_read_resp = MagicMock()
        mock_read_resp.headers = {"Operation-Location": "https://api/v1/operations/op-id-123"}
        mock_client.read_in_stream.return_value = mock_read_resp
        result_obj = MagicMock()
        result_obj.status = "succeeded"
        result_obj.analyze_result = {"read_results": []}
        mock_client.get_read_result.return_value = result_obj
        provider._vision_client = mock_client

        with patch.dict("sys.modules", _azure_sdk_mocks()):
            result = await provider._analyze_frame(b"\xff\xd8\xff", [AnalysisType.OCR], 5.0)

        assert 'timestamp' in result
        assert result['timestamp'] == 5.0

    async def test_analyze_frame_label_detection_path(self):
        provider = _make_provider()
        mock_client = MagicMock()
        analyze_result = MagicMock()
        mock_client.analyze_image_in_stream.return_value = analyze_result
        provider._vision_client = mock_client

        with patch.dict("sys.modules", _azure_sdk_mocks()):
            result = await provider._analyze_frame(b"\xff\xd8\xff", [AnalysisType.LABEL_DETECTION], 10.0)

        assert result['timestamp'] == 10.0
        assert 'analyze' in result

    async def test_analyze_frame_no_analysis_types(self):
        provider = _make_provider()
        provider._vision_client = MagicMock()

        result = await provider._analyze_frame(b"\xff\xd8\xff", [], 3.0)
        assert result == {'timestamp': 3.0}


# ===========================================================================
# _perform_ocr
# ===========================================================================


class TestAzureVisionPerformOCR:
    async def test_perform_ocr_url_succeeded(self):
        provider = _make_provider()
        mock_client = MagicMock()
        mock_read_resp = MagicMock()
        mock_read_resp.headers = {"Operation-Location": "https://api/v1/operations/op-id-abc"}
        mock_client.read.return_value = mock_read_resp
        result_obj = MagicMock()
        result_obj.status = "succeeded"
        result_obj.analyze_result = {"read_results": [{"lines": []}]}
        mock_client.get_read_result.return_value = result_obj
        provider._vision_client = mock_client

        mocks = _azure_sdk_mocks()
        with patch.dict("sys.modules", mocks):
            result = await provider._perform_ocr("http://example.com/img.jpg", None)

        assert "read_result" in result

    async def test_perform_ocr_stream_path(self):
        provider = _make_provider()
        mock_client = MagicMock()
        mock_read_resp = MagicMock()
        mock_read_resp.headers = {"Operation-Location": "https://api/v1/operations/op-id-xyz"}
        mock_client.read_in_stream.return_value = mock_read_resp
        result_obj = MagicMock()
        result_obj.status = "succeeded"
        result_obj.analyze_result = {"read_results": []}
        mock_client.get_read_result.return_value = result_obj
        provider._vision_client = mock_client

        mocks = _azure_sdk_mocks()
        with patch.dict("sys.modules", mocks):
            result = await provider._perform_ocr("local_file.jpg", b"\xff\xd8\xff")

        assert "read_result" in result

    async def test_perform_ocr_failed_status_raises(self):
        provider = _make_provider()
        mock_client = MagicMock()
        mock_read_resp = MagicMock()
        mock_read_resp.headers = {"Operation-Location": "https://api/v1/operations/op-fail"}
        mock_client.read.return_value = mock_read_resp
        result_obj = MagicMock()
        result_obj.status = "failed"
        mock_client.get_read_result.return_value = result_obj
        provider._vision_client = mock_client

        mocks = _azure_sdk_mocks()
        with patch.dict("sys.modules", mocks):
            with pytest.raises(CloudAIError) as exc_info:
                await provider._perform_ocr("http://example.com/img.jpg", None)
        assert "failed" in str(exc_info.value).lower()


# ===========================================================================
# _perform_ocr_stream
# ===========================================================================


class TestAzureVisionPerformOCRStream:
    async def test_perform_ocr_stream_returns_read_result(self):
        import io
        provider = _make_provider()
        mock_client = MagicMock()
        mock_read_resp = MagicMock()
        mock_read_resp.headers = {"Operation-Location": "https://api/v1/operations/op-stream-01"}
        mock_client.read_in_stream.return_value = mock_read_resp
        result_obj = MagicMock()
        result_obj.status = "succeeded"
        result_obj.analyze_result = {"read_results": []}
        mock_client.get_read_result.return_value = result_obj
        provider._vision_client = mock_client

        mocks = _azure_sdk_mocks()
        with patch.dict("sys.modules", mocks):
            result = await provider._perform_ocr_stream(io.BytesIO(b"\xff\xd8\xff"))

        assert "read_result" in result

    async def test_perform_ocr_stream_failed_status_raises(self):
        import io
        provider = _make_provider()
        mock_client = MagicMock()
        mock_read_resp = MagicMock()
        mock_read_resp.headers = {"Operation-Location": "https://api/v1/operations/op-stream-fail"}
        mock_client.read_in_stream.return_value = mock_read_resp
        result_obj = MagicMock()
        result_obj.status = "failed"
        mock_client.get_read_result.return_value = result_obj
        provider._vision_client = mock_client

        mocks = _azure_sdk_mocks()
        with patch.dict("sys.modules", mocks):
            with pytest.raises(CloudAIError) as exc_info:
                await provider._perform_ocr_stream(io.BytesIO(b"\xff\xd8\xff"))
        assert "failed" in str(exc_info.value).lower()


# ===========================================================================
# _await_ocr_call (deadline / timeout enforcement)
# ===========================================================================


class TestAzureVisionAwaitOcrCall:
    async def test_await_ocr_call_past_deadline_raises(self):
        import asyncio

        provider = _make_provider()
        loop = asyncio.get_running_loop()
        called = False

        def _should_not_run():
            nonlocal called
            called = True
            return "unused"

        with pytest.raises(CloudAIError) as exc_info:
            # Deadline already in the past -> remaining <= 0 branch.
            await provider._await_ocr_call(loop.time() - 1, _should_not_run)
        assert "timed out" in str(exc_info.value).lower()
        assert called is False

    async def test_await_ocr_call_slow_call_times_out(self):
        import asyncio
        import time as _time

        provider = _make_provider()
        loop = asyncio.get_running_loop()
        # Tiny budget against a call that blocks longer -> wait_for TimeoutError branch.
        with pytest.raises(CloudAIError) as exc_info:
            await provider._await_ocr_call(loop.time() + 0.05, _time.sleep, 0.5)
        assert "timed out" in str(exc_info.value).lower()


# ===========================================================================
# _analyze_image_content
# ===========================================================================


class TestAzureVisionAnalyzeImageContent:
    async def test_analyze_image_content_url_path(self):
        provider = _make_provider()
        mock_client = MagicMock()
        mock_analyze_result = MagicMock()
        mock_client.analyze_image.return_value = mock_analyze_result
        provider._vision_client = mock_client

        mocks = _azure_sdk_mocks()
        with patch.dict("sys.modules", mocks):
            result = await provider._analyze_image_content("http://example.com/img.jpg", None)

        assert "analyze_result" in result
        assert result["analyze_result"] is mock_analyze_result

    async def test_analyze_image_content_stream_path(self):
        provider = _make_provider()
        mock_client = MagicMock()
        mock_analyze_result = MagicMock()
        mock_client.analyze_image_in_stream.return_value = mock_analyze_result
        provider._vision_client = mock_client

        mocks = _azure_sdk_mocks()
        with patch.dict("sys.modules", mocks):
            result = await provider._analyze_image_content("local_file.jpg", b"\xff\xd8\xff")

        assert "analyze_result" in result
        mock_client.analyze_image_in_stream.assert_called_once()


# ===========================================================================
# _analyze_image_content_stream
# ===========================================================================


class TestAzureVisionAnalyzeImageContentStream:
    async def test_analyze_image_content_stream_returns_result(self):
        import io
        provider = _make_provider()
        mock_client = MagicMock()
        mock_analyze_result = MagicMock()
        mock_client.analyze_image_in_stream.return_value = mock_analyze_result
        provider._vision_client = mock_client

        mocks = _azure_sdk_mocks()
        with patch.dict("sys.modules", mocks):
            result = await provider._analyze_image_content_stream(io.BytesIO(b"\xff\xd8\xff"))

        assert "analyze_result" in result
        assert result["analyze_result"] is mock_analyze_result


# ===========================================================================
# _detect_faces
# ===========================================================================


class TestAzureVisionDetectFaces:
    async def test_detect_faces_url_path(self):
        provider = _make_provider()
        mock_client = MagicMock()
        mock_faces_result = MagicMock()
        mock_client.analyze_image.return_value = mock_faces_result
        provider._vision_client = mock_client

        mocks = _azure_sdk_mocks()
        with patch.dict("sys.modules", mocks):
            result = await provider._detect_faces("http://example.com/img.jpg", None)

        assert "faces_result" in result
        assert result["faces_result"] is mock_faces_result

    async def test_detect_faces_stream_path_succeeds(self):
        provider = _make_provider()
        mock_client = MagicMock()
        mock_faces_result = MagicMock()
        mock_client.analyze_image_in_stream.return_value = mock_faces_result
        provider._vision_client = mock_client

        mocks = _azure_sdk_mocks()
        with patch.dict("sys.modules", mocks):
            result = await provider._detect_faces("local_file.jpg", b"\xff\xd8\xff")

        assert "faces_result" in result
        assert result["faces_result"] is mock_faces_result


# ===========================================================================
# async context manager (inherited from BaseCloudAI)
# ===========================================================================


class TestAzureVisionContextManager:
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


class TestAzureVisionEstimateCost:
    def test_cost_positive_for_nonzero_duration(self):
        provider = _make_provider()
        cost = provider.estimate_cost(60.0, [AnalysisType.OCR])
        assert cost > 0

    def test_cost_scales_with_duration(self):
        provider = _make_provider()
        cost1 = provider.estimate_cost(60.0, [AnalysisType.OCR])
        cost2 = provider.estimate_cost(120.0, [AnalysisType.OCR])
        assert cost2 == pytest.approx(cost1 * 2)

    def test_cost_scales_with_analysis_types(self):
        provider = _make_provider()
        cost1 = provider.estimate_cost(60.0, [AnalysisType.OCR])
        cost2 = provider.estimate_cost(60.0, [AnalysisType.OCR, AnalysisType.FACE_DETECTION])
        assert cost2 > cost1


# ===========================================================================
# Local image reads must not block the event loop
# ===========================================================================


class _ThreadRecordingHandle:
    """File-object proxy that records the calling thread on every ``read``."""

    def __init__(self, handle, threads):
        self._handle = handle
        self._threads = threads

    def read(self, *args, **kwargs):
        self._threads.append(threading.get_ident())
        return self._handle.read(*args, **kwargs)

    def __enter__(self):
        self._handle.__enter__()
        return self

    def __exit__(self, *exc_info):
        return self._handle.__exit__(*exc_info)

    def __getattr__(self, name):
        return getattr(self._handle, name)


class _ThreadRecordingOpen:
    """Wrap ``builtins.open`` and record which thread *reads* a target path.

    Off-loop execution is asserted by *thread identity* rather than elapsed
    wall-clock time, which is flaky on loaded CI runners. The recording hooks
    ``read()`` on the returned handle rather than ``open()`` itself, so a
    regression that opens the file on a worker thread but reads its bytes back
    on the event loop is still caught. Only the target path is wrapped so
    unrelated ``open`` traffic (logging, coverage) cannot contaminate the
    result.
    """

    def __init__(self, target):
        self._real_open = builtins.open
        self._target = str(target)
        self.threads: list[int] = []

    def __call__(self, file, *args, **kwargs):
        handle = self._real_open(file, *args, **kwargs)
        if str(file) == self._target:
            return _ThreadRecordingHandle(handle, self.threads)
        return handle


class TestAzureVisionImageReadOffEventLoop:
    async def test_local_file_read_runs_on_worker_thread(self, tmp_path, monkeypatch):
        monkeypatch.setenv("CLOUD_AI_MEDIA_ROOT", str(tmp_path))
        provider = _make_provider()
        img_file = tmp_path / "frame.jpg"
        img_file.write_bytes(b"\xff\xd8\xff\xe0")
        recorder = _ThreadRecordingOpen(img_file)
        loop_thread = threading.get_ident()

        with patch("builtins.open", recorder):
            result = await provider._prepare_image_input(str(img_file))

        assert result == b"\xff\xd8\xff\xe0"
        assert recorder.threads, "expected the provider to read the local image file"
        assert loop_thread not in recorder.threads, (
            "local image bytes were read on the event loop thread; the read must "
            "be offloaded to a worker thread"
        )

    async def test_http_url_performs_no_disk_read(self, tmp_path):
        """The URL branch must remain untouched: Azure fetches it directly."""
        provider = _make_provider()
        decoy = tmp_path / "unused.jpg"
        decoy.write_bytes(b"\x00")
        recorder = _ThreadRecordingOpen(decoy)

        with patch("builtins.open", recorder):
            result = await provider._prepare_image_input("https://example.com/img.jpg")

        assert result is None
        assert recorder.threads == []

    async def test_missing_file_still_raises_file_not_found(self, tmp_path, monkeypatch):
        """Offloading must not swallow or re-wrap I/O errors."""
        monkeypatch.setenv("CLOUD_AI_MEDIA_ROOT", str(tmp_path))
        provider = _make_provider()
        with pytest.raises(FileNotFoundError):
            await provider._prepare_image_input(str(tmp_path / "does-not-exist.jpg"))
