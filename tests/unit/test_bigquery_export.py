"""Tests for BigQuery Export."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from uvai.ml.bigquery_export import (
    _get_bq_client,
    _insert_rows,
    _insert_via_rest,
    export_action_feedback,
    export_model_checkpoint,
    export_pipeline_run,
    export_transcript_outcome,
)


@patch("uvai.ml.bigquery_export._get_bq_client")
def test_insert_rows_success(mock_get_bq_client):
    """Test successful insertion via BigQuery client."""
    mock_client = MagicMock()
    mock_client.insert_rows_json.return_value = []
    mock_get_bq_client.return_value = mock_client

    success = _insert_rows("test_table", [{"col": "val"}])

    assert success is True
    mock_client.insert_rows_json.assert_called_once()


@patch("uvai.ml.bigquery_export._get_bq_client")
def test_insert_rows_failure(mock_get_bq_client):
    """Test failed insertion via BigQuery client."""
    mock_client = MagicMock()
    mock_client.insert_rows_json.return_value = [{"index": 0, "errors": ["err"]}]
    mock_get_bq_client.return_value = mock_client

    success = _insert_rows("test_table", [{"col": "val"}])

    assert success is False
    mock_client.insert_rows_json.assert_called_once()


@patch("uvai.ml.bigquery_export._get_bq_client")
def test_insert_rows_exception(mock_get_bq_client):
    """Test exception during insertion via BigQuery client."""
    mock_client = MagicMock()
    mock_client.insert_rows_json.side_effect = Exception("Test Error")
    mock_get_bq_client.return_value = mock_client

    success = _insert_rows("test_table", [{"col": "val"}])

    assert success is False


@patch("uvai.ml.bigquery_export._get_bq_client")
def test_insert_rows_no_client(mock_get_bq_client):
    """Test insertion when BigQuery client is None."""
    mock_get_bq_client.return_value = None

    success = _insert_rows("test_table", [{"col": "val"}])

    assert success is False


@patch("urllib.request.urlopen")
@patch("urllib.request.Request")
def test_insert_via_rest_success(mock_request, mock_urlopen):
    """Test successful insertion via REST API."""
    # Mock responses
    token_resp = MagicMock()
    token_resp.read.return_value = json.dumps({"access_token": "fake_token"}).encode()

    insert_resp = MagicMock()
    insert_resp.read.return_value = json.dumps({}).encode()

    # Configure urlopen to return the right response in order
    mock_context = MagicMock()
    mock_context.__enter__.side_effect = [token_resp, insert_resp]
    mock_urlopen.return_value = mock_context

    success = _insert_via_rest("test_table", [{"col": "val"}])

    assert success is True
    assert mock_request.call_count == 2
    assert mock_urlopen.call_count == 2


@patch("urllib.request.urlopen")
@patch("urllib.request.Request")
def test_insert_via_rest_token_failure(mock_request, mock_urlopen):
    """Test insertion failure due to missing token."""
    token_resp = MagicMock()
    token_resp.read.return_value = json.dumps({}).encode()

    mock_context = MagicMock()
    mock_context.__enter__.return_value = token_resp
    mock_urlopen.return_value = mock_context

    success = _insert_via_rest("test_table", [{"col": "val"}])

    assert success is False
    assert mock_request.call_count == 1


@patch("urllib.request.urlopen")
@patch("urllib.request.Request")
def test_insert_via_rest_insert_errors(mock_request, mock_urlopen):
    """Test insertion failure due to REST API errors."""
    token_resp = MagicMock()
    token_resp.read.return_value = json.dumps({"access_token": "fake_token"}).encode()

    insert_resp = MagicMock()
    insert_resp.read.return_value = json.dumps({"insertErrors": [{"index": 0}]}).encode()

    mock_context = MagicMock()
    mock_context.__enter__.side_effect = [token_resp, insert_resp]
    mock_urlopen.return_value = mock_context

    success = _insert_via_rest("test_table", [{"col": "val"}])

    assert success is False


@patch("urllib.request.urlopen")
@patch("urllib.request.Request")
def test_insert_via_rest_exception(mock_request, mock_urlopen):
    """Test exception during REST insertion."""
    mock_urlopen.side_effect = Exception("REST Error")

    success = _insert_via_rest("test_table", [{"col": "val"}])

    assert success is False


@patch("uvai.ml.bigquery_export._insert_rows")
def test_export_transcript_outcome_success(mock_insert_rows):
    mock_insert_rows.return_value = True

    success = export_transcript_outcome(
        outcome={
            "video_url": "https://test.com",
            "metadata": {"duration_seconds": 60, "has_captions": True},
            "actual_source": "youtube",
            "actual_quality": 0.9,
            "success": True
        }
    )

    assert success is True
    mock_insert_rows.assert_called_once()
    assert mock_insert_rows.call_args[0][0] == "transcript_quality_outcomes"
    assert "video_url" in mock_insert_rows.call_args[0][1][0]


@patch("uvai.ml.bigquery_export._insert_rows")
@patch("uvai.ml.bigquery_export._insert_via_rest")
def test_export_transcript_outcome_fallback(mock_insert_via_rest, mock_insert_rows):
    mock_insert_rows.return_value = False
    mock_insert_via_rest.return_value = True

    success = export_transcript_outcome(
        outcome={
            "video_url": "https://test.com",
            "metadata": {"duration_seconds": 60},
            "actual_source": "youtube",
            "actual_quality": 0.9,
            "success": True
        }
    )

    assert success is True
    mock_insert_rows.assert_called_once()
    mock_insert_via_rest.assert_called_once()


@patch("uvai.ml.bigquery_export._insert_rows")
def test_export_action_feedback_success(mock_insert_rows):
    mock_insert_rows.return_value = True

    success = export_action_feedback(
        action_text="Test action",
        clicked=True,
        completed=False
    )

    assert success is True
    mock_insert_rows.assert_called_once()
    assert mock_insert_rows.call_args[0][0] == "action_ranking_feedback"


@patch("uvai.ml.bigquery_export._insert_rows")
@patch("uvai.ml.bigquery_export._insert_via_rest")
def test_export_action_feedback_fallback(mock_insert_via_rest, mock_insert_rows):
    mock_insert_rows.return_value = False
    mock_insert_via_rest.return_value = True

    success = export_action_feedback(
        action_text="Test action",
        clicked=True,
        completed=False
    )

    assert success is True
    mock_insert_rows.assert_called_once()
    mock_insert_via_rest.assert_called_once()


@patch("uvai.ml.bigquery_export._insert_rows")
def test_export_model_checkpoint_success(mock_insert_rows):
    mock_insert_rows.return_value = True

    success = export_model_checkpoint(
        scorer_state={"version": "1.0"},
        ranker_state={"version": "1.0"}
    )

    assert success is True
    mock_insert_rows.assert_called_once()
    assert mock_insert_rows.call_args[0][0] == "model_checkpoints"


@patch("uvai.ml.bigquery_export._insert_rows")
@patch("uvai.ml.bigquery_export._insert_via_rest")
def test_export_model_checkpoint_fallback(mock_insert_via_rest, mock_insert_rows):
    mock_insert_rows.return_value = False
    mock_insert_via_rest.return_value = True

    success = export_model_checkpoint(
        scorer_state={"version": "1.0"},
        ranker_state={"version": "1.0"}
    )

    assert success is True
    mock_insert_rows.assert_called_once()
    mock_insert_via_rest.assert_called_once()


@patch("uvai.ml.bigquery_export._insert_rows")
def test_export_pipeline_run_success(mock_insert_rows):
    mock_insert_rows.return_value = True

    success = export_pipeline_run(
        video_url="https://test.com",
        success=True
    )

    assert success is True
    mock_insert_rows.assert_called_once()
    assert mock_insert_rows.call_args[0][0] == "pipeline_runs"


@patch("uvai.ml.bigquery_export._insert_rows")
@patch("uvai.ml.bigquery_export._insert_via_rest")
def test_export_pipeline_run_fallback(mock_insert_via_rest, mock_insert_rows):
    mock_insert_rows.return_value = False
    mock_insert_via_rest.return_value = True

    success = export_pipeline_run(
        video_url="https://test.com",
        success=True
    )

    assert success is True
    mock_insert_rows.assert_called_once()
    mock_insert_via_rest.assert_called_once()
