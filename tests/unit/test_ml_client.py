"""Tests for UVAI ML Client."""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch
from urllib import error

import pytest

from uvai.ml.client import UVAIMLClient, get_uvai_ml_client


@pytest.fixture(autouse=True)
def reset_singleton() -> None:
    """Reset the singleton instance before each test."""
    import uvai.ml.client

    uvai.ml.client._uvai_ml_client = None


def test_init_base_url_from_arg() -> None:
    client = UVAIMLClient(base_url="http://test-server/")
    assert client.base_url == "http://test-server"


@patch.dict(os.environ, {"UVAI_ML_SERVICE_URL": "http://env-server/"})
def test_init_base_url_from_env() -> None:
    client = UVAIMLClient()
    assert client.base_url == "http://env-server"


@patch.dict(os.environ, clear=True)
def test_init_no_base_url() -> None:
    client = UVAIMLClient()
    assert client.base_url == ""


@pytest.mark.asyncio
async def test_score_transcript_remote_success() -> None:
    client = UVAIMLClient(base_url="http://test-server")
    mock_response = {"quality_score": 0.95, "recommended_source": "youtube_api"}

    with patch.object(client, "_post_json", return_value=mock_response) as mock_post:
        result = await client.score_transcript({"title": "Test Video"})
        assert result == mock_response
        mock_post.assert_called_once_with(
            "/score-transcript", {"metadata": {"title": "Test Video"}}
        )


@pytest.mark.asyncio
async def test_score_transcript_remote_fallback() -> None:
    client = UVAIMLClient(base_url="http://test-server")

    # Return None to simulate a failed request
    with patch.object(client, "_post_json", return_value=None):
        # We need to ensure that the fallback prediction works
        # This uses the underlying TranscriptQualityScorer
        result = await client.score_transcript(
            {
                "title": "Fallback Video",
                "has_captions": True,
                "duration_seconds": 60,
                "language": "en",
            }
        )
        assert "quality_score" in result
        assert "model" in result



@pytest.mark.asyncio
async def test_score_transcript_local_only() -> None:
    client = UVAIMLClient(base_url=None)

    mock_prediction = MagicMock()
    mock_prediction.quality_score = 0.85
    mock_prediction.recommended_source = "whisper_local"
    mock_prediction.confidence = 0.92
    mock_prediction.processing_estimate_seconds = 120.5
    mock_prediction.reasoning = ["High quality audio"]
    mock_prediction.feature_importances = {"audio_quality": 0.7}

    # Since we can't patch a property easily on the instance if it doesn't have a setter,
    # we can mock out the `predict` and just let `model_info` return its default dict
    with (
        patch.object(client, "_post_json") as mock_post,
        patch.object(
            client._scorer, "predict", return_value=mock_prediction
        ) as mock_predict,
    ):
        metadata = {
            "title": "Local Video",
            "has_captions": True,
            "duration_seconds": 60,
            "language": "en",
        }
        result = await client.score_transcript(metadata)

        assert result["quality_score"] == 0.85
        assert result["recommended_source"] == "whisper_local"
        assert result["confidence"] == 0.92
        assert result["processing_estimate_seconds"] == 120.5
        assert result["reasoning"] == ["High quality audio"]
        assert result["feature_importances"] == {"audio_quality": 0.7}
        assert "model" in result

        mock_post.assert_not_called()
        mock_predict.assert_called_once_with(metadata)


@pytest.mark.asyncio
async def test_record_transcript_outcome_remote() -> None:
    client = UVAIMLClient(base_url="http://test-server")
    mock_response = {"recorded": True}

    with patch.object(client, "_post_json", return_value=mock_response) as mock_post:
        result = await client.record_transcript_outcome(
            metadata={"title": "Test Video"},
            actual_source="youtube_api",
            actual_quality=0.9,
            success=True,
        )
        assert result == mock_response
        mock_post.assert_called_once()
        args = mock_post.call_args[0]
        assert args[0] == "/score-transcript/outcome"
        assert args[1]["actual_source"] == "youtube_api"
        assert args[1]["success"] is True


@pytest.mark.asyncio
async def test_record_transcript_outcome_local() -> None:
    client = UVAIMLClient(base_url=None)

    with patch.object(client, "_post_json") as mock_post:
        result = await client.record_transcript_outcome(
            metadata={
                "title": "Test Video",
                "has_captions": True,
                "duration_seconds": 60,
                "language": "en",
            },
            actual_source="youtube_api",
            actual_quality=0.9,
            success=True,
        )
        assert result["recorded"] is True
        assert "total_samples" in result
        mock_post.assert_not_called()


@pytest.mark.asyncio
async def test_rank_actions_remote() -> None:
    client = UVAIMLClient(base_url="http://test-server")
    mock_response = {"ranked_actions": []}

    with patch.object(client, "_post_json", return_value=mock_response) as mock_post:
        result = await client.rank_actions(
            ["Action 1", "Action 2"], video_context={"view_count": 100}
        )
        assert result == mock_response
        mock_post.assert_called_once_with(
            "/rank-actions",
            {"actions": ["Action 1", "Action 2"], "video_context": {"view_count": 100}},
        )


@pytest.mark.asyncio
async def test_rank_actions_local() -> None:
    client = UVAIMLClient(base_url=None)

    with patch.object(client, "_post_json") as mock_post:
        result = await client.rank_actions(["Action 1", "Action 2"])
        assert "ranked_actions" in result
        assert len(result["ranked_actions"]) == 2
        mock_post.assert_not_called()


@pytest.mark.asyncio
async def test_record_action_feedback_remote() -> None:
    client = UVAIMLClient(base_url="http://test-server")
    mock_response = {"recorded": True}

    with patch.object(client, "_post_json", return_value=mock_response) as mock_post:
        result = await client.record_action_feedback(
            action_text="Test Action",
            clicked=True,
            completed=False,
            time_to_complete_seconds=None,
        )
        assert result == mock_response
        mock_post.assert_called_once_with(
            "/rank-actions/feedback",
            {
                "action_text": "Test Action",
                "clicked": True,
                "completed": False,
                "time_to_complete_seconds": None,
            },
        )


@pytest.mark.asyncio
async def test_record_action_feedback_local() -> None:
    client = UVAIMLClient(base_url=None)

    with patch.object(client, "_post_json") as mock_post:
        result = await client.record_action_feedback(
            action_text="Test Action", clicked=True, completed=False
        )
        assert result["recorded"] is True
        mock_post.assert_not_called()


def test_post_json_success() -> None:
    client = UVAIMLClient(base_url="http://test-server", timeout=2.0)

    mock_response = MagicMock()
    mock_response.read.return_value = b'{"status": "ok"}'
    mock_response.__enter__.return_value = mock_response

    with patch(
        "uvai.ml.client.request.urlopen", return_value=mock_response
    ) as mock_urlopen:
        result = client._post_json("/test-endpoint", {"data": 123})

        assert result == {"status": "ok"}
        mock_urlopen.assert_called_once()
        req = mock_urlopen.call_args[0][0]
        assert req.full_url == "http://test-server/test-endpoint"
        assert req.method == "POST"
        assert req.data == b'{"data": 123}'
        assert req.headers["Content-type"] == "application/json"

        # Check timeout kwarg
        assert mock_urlopen.call_args[1]["timeout"] == 2.0


def test_post_json_exceptions() -> None:
    client = UVAIMLClient(base_url="http://test-server")

    # Test OSError
    with patch(
        "uvai.ml.client.request.urlopen", side_effect=OSError("connection refused")
    ):
        assert client._post_json("/test", {}) is None

    # Test ValueError (like invalid JSON decoding or invalid URL)
    with patch(
        "uvai.ml.client.request.urlopen", side_effect=ValueError("invalid json")
    ):
        assert client._post_json("/test", {}) is None

    # Test HTTPError
    mock_err = error.HTTPError(url="", hdrs=None, fp=None, code=500, msg="Server Error")  # type: ignore
    with patch("uvai.ml.client.request.urlopen", side_effect=mock_err):
        assert client._post_json("/test", {}) is None


def test_get_uvai_ml_client() -> None:
    # First call should create instance
    client1 = get_uvai_ml_client()
    assert isinstance(client1, UVAIMLClient)

    # Second call should return the exact same instance
    client2 = get_uvai_ml_client()
    assert client1 is client2
