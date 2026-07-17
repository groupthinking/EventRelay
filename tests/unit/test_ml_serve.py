import pytest
from unittest.mock import MagicMock, AsyncMock, patch
import json
import sys
import os
from pathlib import Path

# Add src to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

# We mock 'ray' because ray serve might not be importable or has side effects
def mock_deployment(*args, **kwargs):
    def decorator(cls):
        # Ray's serve.deployment binds to the class, giving it a 'bind' method
        cls.bind = MagicMock()
        return cls
    return decorator

mock_ray = MagicMock()
mock_serve = MagicMock()
mock_serve.deployment = mock_deployment
mock_ray.serve = mock_serve
sys.modules['ray'] = mock_ray
sys.modules['ray.serve'] = mock_serve

from uvai.ml.serve import UVAIMLRouter
from starlette.requests import Request

class MockRequest:
    def __init__(self, method, path, json_data=None, json_exception=None):
        self.method = method
        class URL:
            def __init__(self, p):
                self.path = p
            def rstrip(self, s):
                return self.path.rstrip(s) if self.path.endswith(s) else self.path
        self.url = URL(path)
        if json_exception:
            self.json = AsyncMock(side_effect=json_exception)
        elif json_data is not None:
            self.json = AsyncMock(return_value=json_data)
        else:
            self.json = AsyncMock(return_value={})

@pytest.fixture
def mock_scorer():
    scorer = MagicMock()
    scorer.get_model_info.remote = AsyncMock(return_value={"name": "scorer", "version": "1.0"})
    scorer.predict.remote = AsyncMock(return_value={"quality_score": 0.9, "recommended_source": "speech_v2"})
    scorer.record_outcome.remote = AsyncMock(return_value={"recorded": True})
    scorer.get_serialized_state.remote = AsyncMock(return_value={"training_samples": 10})
    return scorer

@pytest.fixture
def mock_ranker():
    ranker = MagicMock()
    ranker.get_model_info.remote = AsyncMock(return_value={"name": "ranker", "version": "1.0"})
    ranker.rank.remote = AsyncMock(return_value={"ranked_actions": []})
    ranker.record_feedback.remote = AsyncMock(return_value={"recorded": True})
    ranker.get_serialized_state.remote = AsyncMock(return_value={"training_samples": 20})
    return ranker

@pytest.fixture
def router(mock_scorer, mock_ranker):
    return UVAIMLRouter(scorer=mock_scorer, ranker=mock_ranker)


@pytest.mark.asyncio
async def test_health_endpoint(router):
    request = MockRequest("GET", "/health")
    response = await router(request)
    assert response.status_code == 200
    body = json.loads(response.body)
    assert body["status"] == "healthy"
    assert "uptime_seconds" in body

@pytest.mark.asyncio
async def test_health_endpoint_empty_path(router):
    request = MockRequest("GET", "/")
    response = await router(request)
    assert response.status_code == 200
    body = json.loads(response.body)
    assert body["status"] == "healthy"

@pytest.mark.asyncio
async def test_models_metadata(router):
    request = MockRequest("GET", "/models")
    response = await router(request)
    assert response.status_code == 200
    body = json.loads(response.body)
    assert "transcript_quality_scorer" in body["models"]
    assert "action_priority_ranker" in body["models"]
    assert body["models"]["transcript_quality_scorer"]["name"] == "scorer"

@pytest.mark.asyncio
async def test_invalid_json_body(router):
    request = MockRequest("POST", "/score-transcript", json_exception=ValueError("Invalid JSON"))
    response = await router(request)
    assert response.status_code == 400
    body = json.loads(response.body)
    assert body["error"] == "Invalid JSON body"

@pytest.mark.asyncio
async def test_score_transcript_missing_metadata(router):
    request = MockRequest("POST", "/score-transcript", json_data={})
    response = await router(request)
    assert response.status_code == 400
    body = json.loads(response.body)
    assert body["error"] == "Missing 'metadata' dict"

@pytest.mark.asyncio
async def test_score_transcript_success(router, mock_scorer):
    request = MockRequest("POST", "/score-transcript", json_data={"metadata": {"foo": "bar"}})
    response = await router(request)
    assert response.status_code == 200
    body = json.loads(response.body)
    assert body["quality_score"] == 0.9
    mock_scorer.predict.remote.assert_called_once_with({"foo": "bar"})

@pytest.mark.asyncio
async def test_score_transcript_outcome(router, mock_scorer):
    json_data = {"metadata": {"foo": "bar"}, "success": True}
    request = MockRequest("POST", "/score-transcript/outcome", json_data=json_data)
    response = await router(request)
    assert response.status_code == 200
    body = json.loads(response.body)
    assert body["recorded"] is True
    mock_scorer.record_outcome.remote.assert_called_once_with(json_data)

@pytest.mark.asyncio
async def test_rank_actions_missing_actions(router):
    request = MockRequest("POST", "/rank-actions", json_data={})
    response = await router(request)
    assert response.status_code == 400
    body = json.loads(response.body)
    assert body["error"] == "Missing 'actions' list"

@pytest.mark.asyncio
async def test_rank_actions_success(router, mock_ranker):
    request = MockRequest("POST", "/rank-actions", json_data={"actions": ["action1", "action2"], "video_context": {"cat": "edu"}})
    response = await router(request)
    assert response.status_code == 200
    body = json.loads(response.body)
    assert body["ranked_actions"] == []
    mock_ranker.rank.remote.assert_called_once_with(["action1", "action2"], {"cat": "edu"})

@pytest.mark.asyncio
async def test_rank_actions_feedback(router, mock_ranker):
    json_data = {"action_text": "do it", "clicked": True}
    request = MockRequest("POST", "/rank-actions/feedback", json_data=json_data)
    response = await router(request)
    assert response.status_code == 200
    body = json.loads(response.body)
    assert body["recorded"] is True
    mock_ranker.record_feedback.remote.assert_called_once_with(json_data)

@pytest.mark.asyncio
@patch("uvai.ml.serve.save_checkpoint")
async def test_checkpoint_post_success(mock_save, router, mock_scorer, mock_ranker):
    with patch("uvai.ml.bigquery_export.export_model_checkpoint", create=True) as mock_export:
        request = MockRequest("POST", "/checkpoint")
        response = await router(request)
        assert response.status_code == 200
        body = json.loads(response.body)
        assert body["saved"] is True
        assert body["scorer_samples"] == 10
        assert body["ranker_samples"] == 20

        mock_save.assert_called_once_with({"training_samples": 10}, {"training_samples": 20})
        mock_export.assert_called_once_with({"training_samples": 10}, {"training_samples": 20})

@pytest.mark.asyncio
@patch("uvai.ml.serve.save_checkpoint", side_effect=Exception("Save failed"))
async def test_checkpoint_post_failure(mock_save, router):
    request = MockRequest("POST", "/checkpoint")
    response = await router(request)
    assert response.status_code == 500
    body = json.loads(response.body)
    # The internal exception text ("Save failed") must NOT leak to the client
    # (CWE-209); the 500 body is a static, sanitized message.
    assert body["error"] == "Internal server error"
    assert "Save failed" not in json.dumps(body)

@pytest.mark.asyncio
@patch("uvai.ml.serve.load_checkpoint", return_value={"scorer_state": {}, "ranker_state": {}})
async def test_checkpoint_get_success(mock_load, router):
    request = MockRequest("GET", "/checkpoint")
    response = await router(request)
    assert response.status_code == 200
    body = json.loads(response.body)
    assert "scorer_state" in body

@pytest.mark.asyncio
@patch("uvai.ml.serve.load_checkpoint", return_value=None)
async def test_checkpoint_get_not_found(mock_load, router):
    request = MockRequest("GET", "/checkpoint")
    response = await router(request)
    assert response.status_code == 404
    body = json.loads(response.body)
    assert body["error"] == "No checkpoint found"

@pytest.mark.asyncio
async def test_unknown_path(router):
    request = MockRequest("GET", "/unknown-path")
    response = await router(request)
    assert response.status_code == 404
    body = json.loads(response.body)
    assert body["error"] == "Unknown path: /unknown-path"
    assert "/health" in body["available_endpoints"]
