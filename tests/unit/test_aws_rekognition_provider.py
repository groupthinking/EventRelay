"""Unit tests for integrations/cloud_ai/providers/aws_rekognition.py."""

from __future__ import annotations

import sys
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
    CloudAIError,
    ConfigurationError,
    RateLimitError,
)
from youtube_extension.integrations.cloud_ai.providers.aws_rekognition import (
    AWSRekognition,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

VALID_CONFIG = {
    "aws_access_key_id": "test-access-key-id",
    "aws_secret_access_key": "test-secret-access-key",
    "region": "us-east-1",
}


def _make_provider(config=None) -> AWSRekognition:
    return AWSRekognition(config or VALID_CONFIG)


def _make_rekognition_client(
    describe_side_effect=None,
    detect_labels_response=None,
    detect_faces_response=None,
    detect_text_response=None,
    detect_moderation_response=None,
) -> MagicMock:
    client = MagicMock()
    if describe_side_effect is not None:
        client.describe_collection.side_effect = describe_side_effect
    else:
        # Default: simulate ResourceNotFoundException so _test_connection passes
        client.describe_collection.side_effect = Exception("ResourceNotFoundException: collection not found")
    client.detect_labels.return_value = detect_labels_response or {"Labels": []}
    client.detect_faces.return_value = detect_faces_response or {"FaceDetails": []}
    client.detect_text.return_value = detect_text_response or {"TextDetections": []}
    client.detect_moderation_labels.return_value = detect_moderation_response or {"ModerationLabels": []}
    return client


# ===========================================================================
# __init__ / _validate_config
# ===========================================================================


class TestAWSRekognitionInit:
    def test_valid_config_does_not_raise(self):
        provider = _make_provider()
        assert provider is not None

    def test_provider_set_to_aws_rekognition(self):
        provider = _make_provider()
        assert provider.provider == CloudAIProvider.AWS_REKOGNITION

    def test_rekognition_client_starts_none(self):
        provider = _make_provider()
        assert provider._rekognition_client is None

    def test_s3_client_starts_none(self):
        provider = _make_provider()
        assert provider._s3_client is None

    def test_config_stored(self):
        provider = _make_provider()
        assert provider.config is VALID_CONFIG

    def test_missing_access_key_raises_config_error(self):
        with pytest.raises(ConfigurationError) as exc_info:
            AWSRekognition({"aws_secret_access_key": "secret", "region": "us-east-1"})
        assert exc_info.value.missing_config == "aws_access_key_id"

    def test_missing_secret_key_raises_config_error(self):
        with pytest.raises(ConfigurationError) as exc_info:
            AWSRekognition({"aws_access_key_id": "key", "region": "us-east-1"})
        assert exc_info.value.missing_config == "aws_secret_access_key"

    def test_missing_region_raises_config_error(self):
        with pytest.raises(ConfigurationError) as exc_info:
            AWSRekognition({"aws_access_key_id": "key", "aws_secret_access_key": "secret"})
        assert exc_info.value.missing_config == "region"

    def test_empty_config_raises_config_error(self):
        with pytest.raises(ConfigurationError):
            AWSRekognition({})

    def test_config_error_has_aws_provider(self):
        with pytest.raises(ConfigurationError) as exc_info:
            AWSRekognition({})
        assert exc_info.value.provider == CloudAIProvider.AWS_REKOGNITION.value

    def test_config_error_code_is_configuration_error(self):
        with pytest.raises(ConfigurationError) as exc_info:
            AWSRekognition({})
        assert exc_info.value.error_code == "CONFIGURATION_ERROR"


# ===========================================================================
# initialize
# ===========================================================================


class TestAWSRekognitionInitialize:
    async def test_initialize_sets_rekognition_client(self):
        provider = _make_provider()
        mock_client = _make_rekognition_client()
        mock_session = MagicMock()
        mock_session.client.return_value = mock_client
        mock_boto3 = MagicMock()
        mock_boto3.Session.return_value = mock_session

        with patch.dict("sys.modules", {"boto3": mock_boto3, "botocore": MagicMock(),
                                         "botocore.exceptions": MagicMock(
                                             ClientError=Exception, NoCredentialsError=Exception
                                         )}):
            await provider.initialize()

        assert provider._rekognition_client is not None

    async def test_initialize_sets_s3_client(self):
        provider = _make_provider()
        mock_client = _make_rekognition_client()
        mock_session = MagicMock()
        mock_session.client.return_value = mock_client
        mock_boto3 = MagicMock()
        mock_boto3.Session.return_value = mock_session

        with patch.dict("sys.modules", {"boto3": mock_boto3, "botocore": MagicMock(),
                                         "botocore.exceptions": MagicMock(
                                             ClientError=Exception, NoCredentialsError=Exception
                                         )}):
            await provider.initialize()

        assert provider._s3_client is not None

    async def test_initialize_raises_config_error_on_import_error(self):
        provider = _make_provider()
        with patch.dict("sys.modules", {"boto3": None}):
            with pytest.raises((ConfigurationError, Exception)):
                await provider.initialize()

    async def test_initialize_uses_correct_region(self):
        provider = _make_provider()
        mock_client = _make_rekognition_client()
        mock_session = MagicMock()
        mock_session.client.return_value = mock_client
        mock_boto3 = MagicMock()
        mock_boto3.Session.return_value = mock_session

        with patch.dict("sys.modules", {"boto3": mock_boto3, "botocore": MagicMock(),
                                         "botocore.exceptions": MagicMock(
                                             ClientError=Exception, NoCredentialsError=Exception
                                         )}):
            await provider.initialize()

        mock_boto3.Session.assert_called_once_with(
            aws_access_key_id=VALID_CONFIG["aws_access_key_id"],
            aws_secret_access_key=VALID_CONFIG["aws_secret_access_key"],
            region_name=VALID_CONFIG["region"],
        )


# ===========================================================================
# cleanup
# ===========================================================================


class TestAWSRekognitionCleanup:
    async def test_cleanup_clears_rekognition_client(self):
        provider = _make_provider()
        provider._rekognition_client = MagicMock()
        await provider.cleanup()
        assert provider._rekognition_client is None

    async def test_cleanup_clears_s3_client(self):
        provider = _make_provider()
        provider._s3_client = MagicMock()
        await provider.cleanup()
        assert provider._s3_client is None

    async def test_cleanup_idempotent(self):
        provider = _make_provider()
        await provider.cleanup()  # Should not raise
        assert provider._rekognition_client is None
        assert provider._s3_client is None


# ===========================================================================
# _test_connection
# ===========================================================================


class TestAWSRekognitionTestConnection:
    async def test_connection_ok_with_resource_not_found_error(self):
        provider = _make_provider()
        mock_client = _make_rekognition_client(
            describe_side_effect=Exception("ResourceNotFoundException: No collection found")
        )
        provider._rekognition_client = mock_client
        await provider._test_connection()  # Should not raise

    async def test_connection_raises_on_unexpected_error(self):
        provider = _make_provider()
        mock_client = _make_rekognition_client(
            describe_side_effect=Exception("AccessDenied: you are not authorized")
        )
        provider._rekognition_client = mock_client
        with pytest.raises(Exception):
            await provider._test_connection()

    async def test_connection_succeeds_if_no_exception(self):
        provider = _make_provider()
        mock_client = MagicMock()
        mock_client.describe_collection.return_value = {"CollectionARN": "arn:aws:..."}
        provider._rekognition_client = mock_client
        await provider._test_connection()  # Should not raise


# ===========================================================================
# get_supported_analysis_types
# ===========================================================================


class TestAWSRekognitionSupportedTypes:
    def test_returns_list(self):
        provider = _make_provider()
        types = provider.get_supported_analysis_types()
        assert isinstance(types, list)

    def test_includes_object_tracking(self):
        provider = _make_provider()
        assert AnalysisType.OBJECT_TRACKING in provider.get_supported_analysis_types()

    def test_includes_face_detection(self):
        provider = _make_provider()
        assert AnalysisType.FACE_DETECTION in provider.get_supported_analysis_types()

    def test_includes_text_detection(self):
        provider = _make_provider()
        assert AnalysisType.TEXT_DETECTION in provider.get_supported_analysis_types()

    def test_includes_content_moderation(self):
        provider = _make_provider()
        assert AnalysisType.CONTENT_MODERATION in provider.get_supported_analysis_types()

    def test_includes_label_detection(self):
        provider = _make_provider()
        assert AnalysisType.LABEL_DETECTION in provider.get_supported_analysis_types()

    def test_includes_scene_analysis(self):
        provider = _make_provider()
        assert AnalysisType.SCENE_ANALYSIS in provider.get_supported_analysis_types()

    def test_returns_at_least_six_types(self):
        provider = _make_provider()
        assert len(provider.get_supported_analysis_types()) >= 6


# ===========================================================================
# _ensure_video_in_s3
# ===========================================================================


class TestAWSRekognitionEnsureVideoInS3:
    async def test_s3_url_parsed_correctly(self):
        provider = _make_provider()
        bucket, key = await provider._ensure_video_in_s3("s3://my-bucket/path/to/video.mp4")
        assert bucket == "my-bucket"
        assert key == "path/to/video.mp4"

    async def test_s3_url_simple_key(self):
        provider = _make_provider()
        bucket, key = await provider._ensure_video_in_s3("s3://bucket/video.mp4")
        assert bucket == "bucket"
        assert key == "video.mp4"

    async def test_non_s3_url_uses_default_bucket(self):
        provider = _make_provider()
        bucket, key = await provider._ensure_video_in_s3("http://example.com/video.mp4")
        assert bucket == "rekognition-video-analysis"  # default
        assert "video.mp4" in key

    async def test_non_s3_url_with_custom_bucket_config(self):
        config = {**VALID_CONFIG, "s3_bucket": "custom-bucket"}
        provider = AWSRekognition(config)
        bucket, key = await provider._ensure_video_in_s3("http://example.com/video.mp4")
        assert bucket == "custom-bucket"

    async def test_s3_key_with_nested_path(self):
        provider = _make_provider()
        bucket, key = await provider._ensure_video_in_s3("s3://my-bucket/dir1/dir2/clip.mp4")
        assert bucket == "my-bucket"
        assert key == "dir1/dir2/clip.mp4"


# ===========================================================================
# _prepare_image_input
# ===========================================================================


class TestAWSRekognitionPrepareImageInput:
    async def test_s3_url_returns_s3_object(self):
        provider = _make_provider()
        result = await provider._prepare_image_input("s3://my-bucket/image.jpg")
        assert 'S3Object' in result
        assert result['S3Object']['Bucket'] == "my-bucket"
        assert result['S3Object']['Name'] == "image.jpg"

    async def test_s3_url_with_nested_key(self):
        provider = _make_provider()
        result = await provider._prepare_image_input("s3://bucket/folder/image.jpg")
        assert result['S3Object']['Name'] == "folder/image.jpg"

    async def test_local_file_returns_bytes(self, tmp_path):
        img_file = tmp_path / "test.jpg"
        img_file.write_bytes(b"\xff\xd8\xff\xe0")
        provider = _make_provider()
        result = await provider._prepare_image_input(str(img_file))
        assert result == {'Bytes': b"\xff\xd8\xff\xe0"}

    async def test_http_url_fetches_bytes(self):
        provider = _make_provider()
        mock_response = MagicMock()
        mock_response.content = b"fake image bytes"
        mock_client_instance = AsyncMock()
        mock_client_instance.get = AsyncMock(return_value=mock_response)
        mock_client_cls = MagicMock()
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_httpx = MagicMock()
        mock_httpx.AsyncClient = mock_client_cls

        with patch.dict("sys.modules", {"httpx": mock_httpx}):
            result = await provider._prepare_image_input("http://example.com/image.jpg")

        assert result == {'Bytes': b"fake image bytes"}

    async def test_https_url_fetches_bytes(self):
        provider = _make_provider()
        mock_response = MagicMock()
        mock_response.content = b"secure image bytes"
        mock_client_instance = AsyncMock()
        mock_client_instance.get = AsyncMock(return_value=mock_response)
        mock_client_cls = MagicMock()
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_httpx = MagicMock()
        mock_httpx.AsyncClient = mock_client_cls

        with patch.dict("sys.modules", {"httpx": mock_httpx}):
            result = await provider._prepare_image_input("https://example.com/image.jpg")

        assert result == {'Bytes': b"secure image bytes"}


# ===========================================================================
# _start_video_analysis
# ===========================================================================


class TestAWSRekognitionStartVideoAnalysis:
    async def test_label_detection_starts_job(self):
        provider = _make_provider()
        mock_client = MagicMock()
        mock_client.start_label_detection.return_value = {"JobId": "job-labels-123"}
        provider._rekognition_client = mock_client

        job_ids = await provider._start_video_analysis(
            "my-bucket", "video.mp4", [AnalysisType.LABEL_DETECTION]
        )
        assert 'labels' in job_ids
        assert job_ids['labels'] == "job-labels-123"

    async def test_face_detection_starts_job(self):
        provider = _make_provider()
        mock_client = MagicMock()
        mock_client.start_face_detection.return_value = {"JobId": "job-faces-456"}
        provider._rekognition_client = mock_client

        job_ids = await provider._start_video_analysis(
            "my-bucket", "video.mp4", [AnalysisType.FACE_DETECTION]
        )
        assert 'faces' in job_ids
        assert job_ids['faces'] == "job-faces-456"

    async def test_text_detection_starts_job(self):
        provider = _make_provider()
        mock_client = MagicMock()
        mock_client.start_text_detection.return_value = {"JobId": "job-text-789"}
        provider._rekognition_client = mock_client

        job_ids = await provider._start_video_analysis(
            "my-bucket", "video.mp4", [AnalysisType.TEXT_DETECTION]
        )
        assert 'text' in job_ids

    async def test_content_moderation_starts_job(self):
        provider = _make_provider()
        mock_client = MagicMock()
        mock_client.start_content_moderation.return_value = {"JobId": "job-mod-000"}
        provider._rekognition_client = mock_client

        job_ids = await provider._start_video_analysis(
            "my-bucket", "video.mp4", [AnalysisType.CONTENT_MODERATION]
        )
        assert 'moderation' in job_ids

    async def test_multiple_types_start_multiple_jobs(self):
        provider = _make_provider()
        mock_client = MagicMock()
        mock_client.start_label_detection.return_value = {"JobId": "j1"}
        mock_client.start_face_detection.return_value = {"JobId": "j2"}
        provider._rekognition_client = mock_client

        job_ids = await provider._start_video_analysis(
            "my-bucket", "video.mp4", [AnalysisType.LABEL_DETECTION, AnalysisType.FACE_DETECTION]
        )
        assert 'labels' in job_ids
        assert 'faces' in job_ids

    async def test_unsupported_type_not_in_job_ids(self):
        provider = _make_provider()
        mock_client = MagicMock()
        provider._rekognition_client = mock_client

        job_ids = await provider._start_video_analysis(
            "my-bucket", "video.mp4", [AnalysisType.SCENE_ANALYSIS]
        )
        # SCENE_ANALYSIS has no specific start method
        assert job_ids == {}

    async def test_video_s3_input_correct(self):
        provider = _make_provider()
        mock_client = MagicMock()
        mock_client.start_label_detection.return_value = {"JobId": "j1"}
        provider._rekognition_client = mock_client

        await provider._start_video_analysis(
            "test-bucket", "test-video.mp4", [AnalysisType.LABEL_DETECTION]
        )

        call_args = mock_client.start_label_detection.call_args
        video_arg = call_args[1].get('Video') or call_args[0][0]
        assert video_arg['S3Object']['Bucket'] == "test-bucket"
        assert video_arg['S3Object']['Name'] == "test-video.mp4"


# ===========================================================================
# _wait_for_job_completion
# ===========================================================================


class TestAWSRekognitionWaitForJobCompletion:
    async def test_labels_job_succeeds_immediately(self):
        provider = _make_provider()
        mock_client = MagicMock()
        mock_client.get_label_detection.return_value = {
            'JobStatus': 'SUCCEEDED',
            'Labels': []
        }
        provider._rekognition_client = mock_client

        result = await provider._wait_for_job_completion("job-123", "labels")
        assert result['JobStatus'] == 'SUCCEEDED'

    async def test_faces_job_succeeds_immediately(self):
        provider = _make_provider()
        mock_client = MagicMock()
        mock_client.get_face_detection.return_value = {
            'JobStatus': 'SUCCEEDED',
            'Faces': []
        }
        provider._rekognition_client = mock_client

        result = await provider._wait_for_job_completion("job-456", "faces")
        assert result['JobStatus'] == 'SUCCEEDED'

    async def test_text_job_succeeds_immediately(self):
        provider = _make_provider()
        mock_client = MagicMock()
        mock_client.get_text_detection.return_value = {
            'JobStatus': 'SUCCEEDED',
            'TextDetections': []
        }
        provider._rekognition_client = mock_client

        result = await provider._wait_for_job_completion("job-789", "text")
        assert result['JobStatus'] == 'SUCCEEDED'

    async def test_moderation_job_succeeds_immediately(self):
        provider = _make_provider()
        mock_client = MagicMock()
        mock_client.get_content_moderation.return_value = {
            'JobStatus': 'SUCCEEDED',
            'ModerationLabels': []
        }
        provider._rekognition_client = mock_client

        result = await provider._wait_for_job_completion("job-000", "moderation")
        assert result['JobStatus'] == 'SUCCEEDED'

    async def test_failed_job_raises_cloud_ai_error(self):
        provider = _make_provider()
        mock_client = MagicMock()
        mock_client.get_label_detection.return_value = {
            'JobStatus': 'FAILED',
            'StatusMessage': 'Internal error'
        }
        provider._rekognition_client = mock_client

        with pytest.raises(CloudAIError) as exc_info:
            await provider._wait_for_job_completion("job-fail", "labels")
        assert "failed" in str(exc_info.value).lower()

    async def test_unknown_analysis_type_raises_error(self):
        provider = _make_provider()
        provider._rekognition_client = MagicMock()

        with pytest.raises(CloudAIError):
            await provider._wait_for_job_completion("job-xxx", "unknown_type")

    async def test_timeout_raises_cloud_ai_error(self):
        provider = AWSRekognition({**VALID_CONFIG, "max_wait_time": 0})
        mock_client = MagicMock()
        mock_client.get_label_detection.return_value = {'JobStatus': 'IN_PROGRESS'}
        provider._rekognition_client = mock_client

        with pytest.raises(CloudAIError) as exc_info:
            await provider._wait_for_job_completion("job-slow", "labels")
        assert "timed out" in str(exc_info.value).lower()

    async def test_api_exception_wraps_as_cloud_ai_error(self):
        provider = _make_provider()
        mock_client = MagicMock()
        mock_client.get_label_detection.side_effect = Exception("network failure")
        provider._rekognition_client = mock_client

        with pytest.raises(CloudAIError):
            await provider._wait_for_job_completion("job-err", "labels")


# ===========================================================================
# _process_image_results
# ===========================================================================


class TestAWSRekognitionProcessImageResults:
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
        result = provider._process_image_results({}, "img-abc", [], 1.0)
        assert result.video_id == "img-abc"

    def test_processing_time_set(self):
        provider = _make_provider()
        result = provider._process_image_results({}, "img1", [], 2.5)
        assert result.processing_time == pytest.approx(2.5)

    def test_provider_is_aws_rekognition(self):
        provider = _make_provider()
        result = provider._process_image_results({}, "img1", [], 1.0)
        assert result.provider == CloudAIProvider.AWS_REKOGNITION

    def test_labels_processed(self):
        provider = _make_provider()
        results = {
            'labels': {
                'Labels': [
                    {'Name': 'Dog', 'Confidence': 95.5, 'Categories': []},
                    {'Name': 'Animal', 'Confidence': 80.2, 'Categories': []},
                ]
            }
        }
        result = provider._process_image_results(results, "img1", [AnalysisType.LABEL_DETECTION], 1.0)
        assert len(result.labels) == 2
        assert result.labels[0].label == 'Dog'
        assert result.labels[0].confidence == pytest.approx(0.955)

    def test_faces_processed(self):
        provider = _make_provider()
        results = {
            'faces': {
                'FaceDetails': [
                    {
                        'BoundingBox': {'Left': 0.1, 'Top': 0.2, 'Width': 0.15, 'Height': 0.2},
                        'Confidence': 99.8,
                        'Emotions': [{'Type': 'HAPPY', 'Confidence': 97.0}],
                        'AgeRange': {'Low': 25, 'High': 35},
                        'Gender': {'Value': 'Male', 'Confidence': 99.0},
                        'Landmarks': [],
                    }
                ]
            }
        }
        result = provider._process_image_results(results, "img1", [AnalysisType.FACE_DETECTION], 1.0)
        assert len(result.faces) == 1
        assert result.faces[0].label == "Face"
        assert result.faces[0].confidence == pytest.approx(0.998)
        assert result.faces[0].bounding_box['x'] == pytest.approx(0.1)
        assert result.faces[0].bounding_box['y'] == pytest.approx(0.2)

    def test_text_processed_words_only(self):
        provider = _make_provider()
        results = {
            'text': {
                'TextDetections': [
                    {
                        'DetectedText': 'Hello',
                        'Type': 'WORD',
                        'Confidence': 99.0,
                        'Timestamp': 1000,
                        'Geometry': {'BoundingBox': {'Left': 0.1, 'Top': 0.1, 'Width': 0.1, 'Height': 0.05}}
                    },
                    {
                        'DetectedText': 'Hello World',
                        'Type': 'LINE',  # Should be excluded
                        'Confidence': 99.0,
                        'Timestamp': 1000,
                        'Geometry': {'BoundingBox': {'Left': 0.1, 'Top': 0.1, 'Width': 0.2, 'Height': 0.05}}
                    }
                ]
            }
        }
        result = provider._process_image_results(results, "img1", [AnalysisType.TEXT_DETECTION], 1.0)
        assert len(result.text_detections) == 1
        assert result.text_detections[0].label == 'Hello'

    def test_labels_confidence_normalized(self):
        provider = _make_provider()
        results = {
            'labels': {
                'Labels': [{'Name': 'Cat', 'Confidence': 75.0, 'Categories': []}]
            }
        }
        result = provider._process_image_results(results, "img1", [AnalysisType.LABEL_DETECTION], 1.0)
        assert result.labels[0].confidence == pytest.approx(0.75)

    def test_face_metadata_has_emotions(self):
        provider = _make_provider()
        results = {
            'faces': {
                'FaceDetails': [
                    {
                        'BoundingBox': {'Left': 0.1, 'Top': 0.2, 'Width': 0.15, 'Height': 0.2},
                        'Confidence': 90.0,
                        'Emotions': [{'Type': 'SAD', 'Confidence': 60.0}],
                        'AgeRange': {},
                        'Gender': {},
                        'Landmarks': [],
                    }
                ]
            }
        }
        result = provider._process_image_results(results, "img1", [AnalysisType.FACE_DETECTION], 1.0)
        emotions = result.faces[0].metadata['emotions']
        assert len(emotions) == 1
        assert emotions[0]['Type'] == 'SAD'


# ===========================================================================
# _process_video_results
# ===========================================================================


class TestAWSRekognitionProcessVideoResults:
    def test_returns_video_analysis_result(self):
        provider = _make_provider()
        result = provider._process_video_results({}, "vid1", [AnalysisType.LABEL_DETECTION], 2.0)
        assert isinstance(result, VideoAnalysisResult)

    def test_provider_is_aws_rekognition(self):
        provider = _make_provider()
        result = provider._process_video_results({}, "vid1", [], 1.0)
        assert result.provider == CloudAIProvider.AWS_REKOGNITION

    def test_labels_from_video_detection(self):
        provider = _make_provider()
        results = {
            'labels': {
                'Labels': [
                    {
                        'Timestamp': 2000,  # 2 seconds in ms
                        'Label': {'Name': 'Car', 'Confidence': 88.0}
                    }
                ]
            }
        }
        result = provider._process_video_results(results, "vid1", [AnalysisType.LABEL_DETECTION], 1.0)
        assert len(result.labels) == 1
        assert result.labels[0].label == 'Car'
        assert result.labels[0].timestamp == pytest.approx(2.0)  # converted from ms
        assert result.labels[0].confidence == pytest.approx(0.88)

    def test_faces_from_video_detection(self):
        provider = _make_provider()
        results = {
            'faces': {
                'Faces': [
                    {
                        'Timestamp': 5000,
                        'Face': {
                            'BoundingBox': {'Left': 0.2, 'Top': 0.1, 'Width': 0.1, 'Height': 0.2},
                            'Confidence': 97.5,
                            'Emotions': [],
                            'AgeRange': {'Low': 20, 'High': 30},
                            'Gender': {'Value': 'Female'},
                        }
                    }
                ]
            }
        }
        result = provider._process_video_results(results, "vid1", [AnalysisType.FACE_DETECTION], 1.0)
        assert len(result.faces) == 1
        assert result.faces[0].timestamp == pytest.approx(5.0)
        assert result.faces[0].bounding_box['x'] == pytest.approx(0.2)

    def test_text_from_video_words_only(self):
        provider = _make_provider()
        results = {
            'text': {
                'TextDetections': [
                    {
                        'DetectedText': 'Speed',
                        'Type': 'WORD',
                        'Confidence': 99.0,
                        'Timestamp': 3000,
                        'Geometry': {'BoundingBox': {'Left': 0.5, 'Top': 0.5, 'Width': 0.1, 'Height': 0.05}}
                    },
                    {
                        'DetectedText': 'Speed limit',
                        'Type': 'LINE',
                        'Confidence': 99.0,
                        'Timestamp': 3000,
                        'Geometry': {'BoundingBox': {'Left': 0.5, 'Top': 0.5, 'Width': 0.2, 'Height': 0.05}}
                    },
                ]
            }
        }
        result = provider._process_video_results(results, "vid1", [AnalysisType.TEXT_DETECTION], 1.0)
        assert len(result.text_detections) == 1
        assert result.text_detections[0].label == 'Speed'

    def test_raw_response_stored(self):
        provider = _make_provider()
        raw = {'labels': {'Labels': []}}
        result = provider._process_video_results(raw, "vid1", [], 1.0)
        assert result.raw_response is raw


# ===========================================================================
# analyze_image (integration-style)
# ===========================================================================


class TestAWSRekognitionAnalyzeImage:
    async def test_analyze_image_labels_calls_detect_labels(self):
        provider = _make_provider()
        mock_client = _make_rekognition_client()
        mock_client.detect_labels.return_value = {"Labels": []}
        provider._rekognition_client = mock_client

        with patch.object(provider, '_prepare_image_input', new=AsyncMock(return_value={"Bytes": b"img"})):
            result = await provider.analyze_image("http://example.com/img.jpg", [AnalysisType.LABEL_DETECTION])

        mock_client.detect_labels.assert_called_once()
        assert isinstance(result, VideoAnalysisResult)

    async def test_analyze_image_face_calls_detect_faces(self):
        provider = _make_provider()
        mock_client = _make_rekognition_client()
        mock_client.detect_faces.return_value = {"FaceDetails": []}
        provider._rekognition_client = mock_client

        with patch.object(provider, '_prepare_image_input', new=AsyncMock(return_value={"Bytes": b"img"})):
            result = await provider.analyze_image("http://example.com/img.jpg", [AnalysisType.FACE_DETECTION])

        mock_client.detect_faces.assert_called_once()
        assert isinstance(result, VideoAnalysisResult)

    async def test_analyze_image_text_calls_detect_text(self):
        provider = _make_provider()
        mock_client = _make_rekognition_client()
        mock_client.detect_text.return_value = {"TextDetections": []}
        provider._rekognition_client = mock_client

        with patch.object(provider, '_prepare_image_input', new=AsyncMock(return_value={"Bytes": b"img"})):
            result = await provider.analyze_image("http://example.com/img.jpg", [AnalysisType.TEXT_DETECTION])

        mock_client.detect_text.assert_called_once()

    async def test_analyze_image_moderation_calls_detect_moderation(self):
        provider = _make_provider()
        mock_client = _make_rekognition_client()
        mock_client.detect_moderation_labels.return_value = {"ModerationLabels": []}
        provider._rekognition_client = mock_client

        with patch.object(provider, '_prepare_image_input', new=AsyncMock(return_value={"Bytes": b"img"})):
            await provider.analyze_image("http://example.com/img.jpg", [AnalysisType.CONTENT_MODERATION])

        mock_client.detect_moderation_labels.assert_called_once()

    async def test_analyze_image_initializes_if_client_none(self):
        provider = _make_provider()
        mock_client = _make_rekognition_client()
        mock_client.detect_labels.return_value = {"Labels": []}

        async def _fake_init():
            provider._rekognition_client = mock_client

        with patch.object(provider, 'initialize', side_effect=_fake_init), \
             patch.object(provider, '_prepare_image_input', new=AsyncMock(return_value={"Bytes": b"img"})):
            result = await provider.analyze_image("http://example.com/img.jpg", [AnalysisType.LABEL_DETECTION])

        assert isinstance(result, VideoAnalysisResult)

    async def test_analyze_image_raises_cloud_ai_error_on_failure(self):
        provider = _make_provider()
        provider._rekognition_client = MagicMock()

        with patch.object(provider, '_prepare_image_input', new=AsyncMock(side_effect=Exception("network err"))):
            with pytest.raises(CloudAIError):
                await provider.analyze_image("http://example.com/img.jpg", [AnalysisType.LABEL_DETECTION])


# ===========================================================================
# analyze_video (integration-style)
# ===========================================================================


class TestAWSRekognitionAnalyzeVideo:
    async def test_analyze_video_returns_result(self):
        provider = _make_provider()
        provider._rekognition_client = MagicMock()

        with patch.object(provider, '_ensure_video_in_s3', new=AsyncMock(return_value=("bucket", "key"))), \
             patch.object(provider, '_start_video_analysis', new=AsyncMock(return_value={"labels": "job-1"})), \
             patch.object(provider, '_collect_video_results', new=AsyncMock(return_value={"labels": {"Labels": []}})):
            result = await provider.analyze_video("s3://bucket/video.mp4", [AnalysisType.LABEL_DETECTION])

        assert isinstance(result, VideoAnalysisResult)

    async def test_analyze_video_throttling_raises_rate_limit_error(self):
        provider = _make_provider()
        provider._rekognition_client = MagicMock()

        with patch.object(provider, '_ensure_video_in_s3',
                          new=AsyncMock(side_effect=Exception("ThrottlingException: rate exceeded"))):
            with pytest.raises(RateLimitError):
                await provider.analyze_video("s3://bucket/v.mp4", [AnalysisType.LABEL_DETECTION])

    async def test_analyze_video_generic_error_raises_cloud_ai_error(self):
        provider = _make_provider()
        provider._rekognition_client = MagicMock()

        with patch.object(provider, '_ensure_video_in_s3',
                          new=AsyncMock(side_effect=Exception("some other failure"))):
            with pytest.raises(CloudAIError):
                await provider.analyze_video("s3://bucket/v.mp4", [AnalysisType.LABEL_DETECTION])

    async def test_analyze_video_initializes_if_not_set(self):
        provider = _make_provider()
        mock_client = MagicMock()

        async def _fake_init():
            provider._rekognition_client = mock_client

        with patch.object(provider, 'initialize', side_effect=_fake_init), \
             patch.object(provider, '_ensure_video_in_s3', new=AsyncMock(return_value=("b", "k"))), \
             patch.object(provider, '_start_video_analysis', new=AsyncMock(return_value={})), \
             patch.object(provider, '_collect_video_results', new=AsyncMock(return_value={})):
            result = await provider.analyze_video("s3://b/v.mp4", [AnalysisType.LABEL_DETECTION])

        assert isinstance(result, VideoAnalysisResult)


# ===========================================================================
# get_service_status
# ===========================================================================


class TestAWSRekognitionGetServiceStatus:
    async def test_healthy_status_when_resource_not_found(self):
        provider = _make_provider()
        mock_client = _make_rekognition_client(
            describe_side_effect=Exception("ResourceNotFoundException")
        )
        provider._rekognition_client = mock_client

        status = await provider.get_service_status()
        assert status['status'] == 'healthy'

    async def test_healthy_has_response_time(self):
        provider = _make_provider()
        mock_client = _make_rekognition_client(
            describe_side_effect=Exception("ResourceNotFoundException")
        )
        provider._rekognition_client = mock_client

        status = await provider.get_service_status()
        assert status['response_time'] >= 0

    async def test_healthy_has_timestamp(self):
        provider = _make_provider()
        mock_client = _make_rekognition_client(
            describe_side_effect=Exception("ResourceNotFoundException")
        )
        provider._rekognition_client = mock_client

        status = await provider.get_service_status()
        assert 'timestamp' in status

    async def test_unhealthy_on_unexpected_exception(self):
        provider = _make_provider()
        mock_client = MagicMock()
        # Make initialize fail
        mock_client.describe_collection.side_effect = Exception("AccessDenied")
        provider._rekognition_client = mock_client

        # Override initialize to re-raise
        async def _bad_init():
            raise Exception("cannot connect")

        with patch.object(provider, 'initialize', side_effect=_bad_init):
            provider._rekognition_client = None  # force initialize to be called
            status = await provider.get_service_status()

        assert status['status'] == 'unhealthy'
        assert 'error' in status


# ===========================================================================
# async context manager (inherited)
# ===========================================================================


class TestAWSRekognitionContextManager:
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


class TestAWSRekognitionEstimateCost:
    def test_cost_positive_for_nonzero_duration(self):
        provider = _make_provider()
        cost = provider.estimate_cost(60.0, [AnalysisType.LABEL_DETECTION])
        assert cost > 0

    def test_cost_scales_with_duration(self):
        provider = _make_provider()
        cost1 = provider.estimate_cost(60.0, [AnalysisType.LABEL_DETECTION])
        cost2 = provider.estimate_cost(120.0, [AnalysisType.LABEL_DETECTION])
        assert cost2 == pytest.approx(cost1 * 2)


# ===========================================================================
# Event-loop responsiveness: every boto3 call must run off the loop
# ===========================================================================

async def _count_heartbeats(coro, tick: float = 0.005) -> tuple[object, int]:
    """Run ``coro`` while a heartbeat task ticks; return (result, ticks).

    If the awaited work performs blocking I/O directly on the event loop the
    heartbeat never gets scheduled and ``ticks`` stays at 0.
    """
    import asyncio
    import contextlib

    ticks = 0
    stop = False

    async def _beat():
        nonlocal ticks
        while not stop:
            await asyncio.sleep(tick)
            ticks += 1

    beat = asyncio.create_task(_beat())
    await asyncio.sleep(0)  # let the heartbeat reach its first await first
    try:
        result = await coro
    finally:
        stop = True
        beat.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await beat
    return result, ticks


def _slow(return_value, delay: float = 0.12):
    """A synchronous callable that blocks for ``delay`` seconds."""
    import time

    def _call(*_args, **_kwargs):
        time.sleep(delay)
        return return_value

    return _call


class TestRekognitionDoesNotBlockEventLoop:
    async def test_analyze_image_does_not_stall_the_event_loop(self):
        provider = _make_provider()
        mock_client = _make_rekognition_client()
        mock_client.detect_labels.side_effect = _slow({"Labels": []})
        provider._rekognition_client = mock_client

        with patch.object(provider, '_prepare_image_input',
                          new=AsyncMock(return_value={"Bytes": b"img"})):
            result, ticks = await _count_heartbeats(
                provider.analyze_image("http://e.com/i.jpg", [AnalysisType.LABEL_DETECTION])
            )

        assert isinstance(result, VideoAnalysisResult)
        assert ticks > 0, "detect_labels blocked the event loop"

    async def test_every_detection_type_runs_off_the_loop(self):
        provider = _make_provider()
        mock_client = _make_rekognition_client()
        # four blocking calls back to back
        mock_client.detect_labels.side_effect = _slow({"Labels": []}, 0.06)
        mock_client.detect_faces.side_effect = _slow({"FaceDetails": []}, 0.06)
        mock_client.detect_text.side_effect = _slow({"TextDetections": []}, 0.06)
        mock_client.detect_moderation_labels.side_effect = _slow({"ModerationLabels": []}, 0.06)
        provider._rekognition_client = mock_client

        with patch.object(provider, '_prepare_image_input',
                          new=AsyncMock(return_value={"Bytes": b"img"})):
            _result, ticks = await _count_heartbeats(
                provider.analyze_image(
                    "http://e.com/i.jpg",
                    [AnalysisType.LABEL_DETECTION, AnalysisType.FACE_DETECTION,
                     AnalysisType.TEXT_DETECTION, AnalysisType.CONTENT_MODERATION],
                )
            )

        mock_client.detect_labels.assert_called_once()
        mock_client.detect_moderation_labels.assert_called_once()
        assert ticks > 0, "the detect_* chain blocked the event loop"

    async def test_job_polling_does_not_stall_the_event_loop(self):
        provider = _make_provider()
        mock_client = MagicMock()
        mock_client.get_label_detection.side_effect = _slow(
            {'JobStatus': 'SUCCEEDED', 'Labels': []}
        )
        provider._rekognition_client = mock_client

        result, ticks = await _count_heartbeats(
            provider._wait_for_job_completion("job-1", "labels")
        )

        assert result['JobStatus'] == 'SUCCEEDED'
        assert ticks > 0, "get_label_detection blocked the event loop"

    async def test_start_video_analysis_does_not_stall_the_event_loop(self):
        provider = _make_provider()
        mock_client = MagicMock()
        mock_client.start_label_detection.side_effect = _slow({'JobId': 'j-1'})
        provider._rekognition_client = mock_client

        result, ticks = await _count_heartbeats(
            provider._start_video_analysis(
                "my-bucket", "video.mp4", [AnalysisType.LABEL_DETECTION]
            )
        )

        assert result == {'labels': 'j-1'}
        assert ticks > 0, "start_label_detection blocked the event loop"

    async def test_local_image_read_runs_off_the_event_loop_thread(self, tmp_path):
        """
        Deterministic counterpart to the heartbeat tests.

        The local read is far too fast to time reliably on a loaded runner, so
        instead of measuring elapsed ticks this asserts the property directly:
        the read must execute on a worker thread, not on the thread running the
        event loop. This is immune to scheduler load and needs no sleeps.
        """
        import threading

        from youtube_extension.integrations.cloud_ai.providers import (
            aws_rekognition as _rek_mod,
        )

        image = tmp_path / "frame.jpg"
        image.write_bytes(b"BINARY-IMAGE-PAYLOAD")
        provider = _make_provider()

        loop_thread_id = threading.get_ident()
        observed: dict[str, int] = {}
        real_read = _rek_mod._read_file_bytes

        def _recording_read(path):
            observed['thread_id'] = threading.get_ident()
            return real_read(path)

        with patch.object(_rek_mod, '_read_file_bytes', _recording_read):
            result = await provider._prepare_image_input(str(image))

        assert result == {'Bytes': b"BINARY-IMAGE-PAYLOAD"}
        assert 'thread_id' in observed, "_read_file_bytes was never called"
        assert observed['thread_id'] != loop_thread_id, (
            "the local image read ran on the event loop thread instead of "
            "being dispatched to a worker thread"
        )

    async def test_local_image_bytes_are_read_correctly(self, tmp_path):
        """Guard: offloading must not change what is returned."""
        image = tmp_path / "frame.png"
        payload = bytes(range(256)) * 8
        image.write_bytes(payload)
        provider = _make_provider()

        result = await provider._prepare_image_input(str(image))

        assert result == {'Bytes': payload}
