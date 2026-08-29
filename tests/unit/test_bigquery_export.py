"""Tests for BigQuery export functionality.

Focused unit coverage for :mod:`uvai.ml.bigquery_export`.

Every Google Cloud, network, and metadata-server boundary is mocked, so these
tests never reach an external service and run deterministically offline.
"""

from __future__ import annotations

import builtins
import json
from datetime import datetime
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from uvai.ml import bigquery_export
from uvai.ml.bigquery_export import (
    ACTION_FEEDBACK_TABLE,
    MODEL_CHECKPOINTS_TABLE,
    PIPELINE_RUNS_TABLE,
    TRANSCRIPT_OUTCOMES_TABLE,
    _get_bq_client,
    _insert_rows,
    _insert_via_rest,
    export_action_feedback,
    export_model_checkpoint,
    export_pipeline_run,
    export_transcript_outcome,
)

MODULE = "uvai.ml.bigquery_export"


def _fake_http_response(payload: dict[str, Any]) -> MagicMock:
    """Build a urlopen() context-manager double returning ``payload`` as JSON."""
    resp = MagicMock()
    resp.read.return_value = json.dumps(payload).encode("utf-8")
    ctx = MagicMock()
    ctx.__enter__.return_value = resp
    ctx.__exit__.return_value = False
    return ctx


def _assert_iso_utc(value: str) -> None:
    """The exported timestamp must be a timezone-aware ISO-8601 UTC string."""
    parsed = datetime.fromisoformat(value)
    assert parsed.tzinfo is not None, "exported_at must be timezone-aware"
    offset = parsed.utcoffset()
    assert offset is not None and offset.total_seconds() == 0, "exported_at must be UTC"


class TestGetBqClient:
    """`_get_bq_client` degrades to None instead of raising."""

    def test_returns_none_when_bigquery_not_installed(self) -> None:
        """ImportError is swallowed regardless of interpreter import state.

        Poisoning ``sys.modules["google.cloud.bigquery"]`` alone is not enough:
        ``from google.cloud import bigquery`` resolves by ``getattr`` on an
        already-imported ``google.cloud``, so a real or mocked parent package
        left behind by another test bypasses the poisoned entry entirely.
        Denying the import at ``__import__`` level is order-independent.
        """
        real_import = builtins.__import__

        def _deny_bigquery(name: str, *args: Any, **kwargs: Any) -> Any:
            fromlist = args[2] if len(args) > 2 else kwargs.get("fromlist") or ()
            if name == "google.cloud.bigquery" or (
                name == "google.cloud" and "bigquery" in fromlist
            ):
                raise ImportError("No module named 'google.cloud.bigquery'")
            return real_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=_deny_bigquery):
            assert _get_bq_client() is None

    def test_returns_none_when_client_construction_raises(self) -> None:
        bigquery = MagicMock()
        bigquery.Client.side_effect = RuntimeError("no credentials")
        google_cloud = MagicMock(bigquery=bigquery)
        with patch.dict(
            "sys.modules",
            {
                "google": MagicMock(cloud=google_cloud),
                "google.cloud": google_cloud,
                "google.cloud.bigquery": bigquery,
            },
        ):
            assert _get_bq_client() is None

    def test_returns_client_and_passes_project_id(self) -> None:
        sentinel = object()
        bigquery = MagicMock()
        bigquery.Client.return_value = sentinel
        google_cloud = MagicMock(bigquery=bigquery)
        with patch.dict(
            "sys.modules",
            {
                "google": MagicMock(cloud=google_cloud),
                "google.cloud": google_cloud,
                "google.cloud.bigquery": bigquery,
            },
        ):
            assert _get_bq_client() is sentinel
        bigquery.Client.assert_called_once_with(project=bigquery_export.PROJECT_ID)


class TestInsertRows:
    """`_insert_rows` returns a bool and never propagates client failures."""

    def test_returns_false_when_client_unavailable(self) -> None:
        with patch(f"{MODULE}._get_bq_client", return_value=None):
            assert _insert_rows("some_table", [{"a": 1}]) is False

    def test_returns_true_when_no_errors_reported(self) -> None:
        client = MagicMock()
        client.insert_rows_json.return_value = []
        with patch(f"{MODULE}._get_bq_client", return_value=client):
            assert _insert_rows("some_table", [{"a": 1}]) is True

    def test_builds_fully_qualified_table_reference(self) -> None:
        client = MagicMock()
        client.insert_rows_json.return_value = []
        rows = [{"a": 1}]
        with patch(f"{MODULE}._get_bq_client", return_value=client):
            _insert_rows("some_table", rows)
        expected = (
            f"{bigquery_export.PROJECT_ID}.{bigquery_export.DATASET_ID}.some_table"
        )
        client.insert_rows_json.assert_called_once_with(expected, rows)

    def test_returns_false_when_backend_reports_row_errors(self) -> None:
        client = MagicMock()
        client.insert_rows_json.return_value = [{"index": 0, "errors": ["bad row"]}]
        with patch(f"{MODULE}._get_bq_client", return_value=client):
            assert _insert_rows("some_table", [{"a": 1}]) is False

    def test_returns_false_when_insert_raises(self) -> None:
        client = MagicMock()
        client.insert_rows_json.side_effect = RuntimeError("network down")
        with patch(f"{MODULE}._get_bq_client", return_value=client):
            assert _insert_rows("some_table", [{"a": 1}]) is False

    def test_empty_row_list_is_forwarded_verbatim(self) -> None:
        """Empty input is not special-cased; it is still handed to the client."""
        client = MagicMock()
        client.insert_rows_json.return_value = []
        with patch(f"{MODULE}._get_bq_client", return_value=client):
            assert _insert_rows("some_table", []) is True
        assert client.insert_rows_json.call_args[0][1] == []


class TestInsertViaRest:
    """`_insert_via_rest` is the Cloud Run metadata-server fallback."""

    def test_returns_false_when_token_missing(self) -> None:
        with patch("urllib.request.urlopen", return_value=_fake_http_response({})):
            assert _insert_via_rest("t", [{"a": 1}]) is False

    def test_returns_false_when_token_is_empty_string(self) -> None:
        with patch(
            "urllib.request.urlopen",
            return_value=_fake_http_response({"access_token": ""}),
        ):
            assert _insert_via_rest("t", [{"a": 1}]) is False

    def test_returns_true_on_successful_insert(self) -> None:
        responses = [
            _fake_http_response({"access_token": "tok"}),
            _fake_http_response({"kind": "bigquery#tableDataInsertAllResponse"}),
        ]
        with patch("urllib.request.urlopen", side_effect=responses):
            assert _insert_via_rest("t", [{"a": 1}]) is True

    def test_returns_false_when_insert_errors_present(self) -> None:
        responses = [
            _fake_http_response({"access_token": "tok"}),
            _fake_http_response({"insertErrors": [{"index": 0}]}),
        ]
        with patch("urllib.request.urlopen", side_effect=responses):
            assert _insert_via_rest("t", [{"a": 1}]) is False

    def test_returns_false_when_network_raises(self) -> None:
        with patch("urllib.request.urlopen", side_effect=OSError("unreachable")):
            assert _insert_via_rest("t", [{"a": 1}]) is False

    def test_requests_token_from_metadata_server_with_required_header(self) -> None:
        responses = [
            _fake_http_response({"access_token": "tok"}),
            _fake_http_response({}),
        ]
        with patch("urllib.request.urlopen", side_effect=responses) as urlopen:
            _insert_via_rest("t", [{"a": 1}])
        token_req = urlopen.call_args_list[0][0][0]
        assert token_req.full_url.startswith("http://metadata.google.internal/")
        # urllib normalizes header names to title-case.
        assert token_req.get_header("Metadata-flavor") == "Google"

    def test_sends_bearer_token_and_targets_insert_all_endpoint(self) -> None:
        responses = [
            _fake_http_response({"access_token": "tok"}),
            _fake_http_response({}),
        ]
        with patch("urllib.request.urlopen", side_effect=responses) as urlopen:
            _insert_via_rest("my_table", [{"a": 1}])
        insert_req = urlopen.call_args_list[1][0][0]
        assert insert_req.get_header("Authorization") == "Bearer tok"
        assert insert_req.get_header("Content-type") == "application/json"
        assert insert_req.get_method() == "POST"
        assert insert_req.full_url == (
            "https://bigquery.googleapis.com/bigquery/v2/projects/"
            f"{bigquery_export.PROJECT_ID}/datasets/"
            f"{bigquery_export.DATASET_ID}/tables/my_table/insertAll"
        )

    def test_wraps_each_row_with_a_unique_insert_id(self) -> None:
        responses = [
            _fake_http_response({"access_token": "tok"}),
            _fake_http_response({}),
        ]
        rows = [{"a": 1}, {"b": 2}, {"c": 3}]
        with patch("urllib.request.urlopen", side_effect=responses) as urlopen:
            _insert_via_rest("t", rows)
        body = json.loads(urlopen.call_args_list[1][0][0].data.decode("utf-8"))
        assert [entry["json"] for entry in body["rows"]] == rows
        insert_ids = [entry["insertId"] for entry in body["rows"]]
        assert len(set(insert_ids)) == len(rows), "insertIds must be unique"


class TestExportTranscriptOutcome:
    """Serialization and fallback wiring for `export_transcript_outcome`."""

    METADATA = {
        "duration_seconds": 321.0,
        "has_captions": True,
        "language": "en",
        "category": "Education",
        "subscriber_count": 1000,
        "view_count": 50_000,
    }

    def test_returns_true_and_skips_rest_when_primary_insert_succeeds(self) -> None:
        with (
            patch(f"{MODULE}._insert_rows", return_value=True) as rows,
            patch(f"{MODULE}._insert_via_rest") as rest,
        ):
            result = export_transcript_outcome(
                video_url="https://youtu.be/auJzb1D-fag",
                metadata=self.METADATA,
                actual_source="captions",
                actual_quality=0.93,
                success=True,
            )
        assert result is True
        rows.assert_called_once()
        rest.assert_not_called()

    def test_falls_back_to_rest_when_primary_insert_fails(self) -> None:
        with (
            patch(f"{MODULE}._insert_rows", return_value=False),
            patch(f"{MODULE}._insert_via_rest", return_value=True) as rest,
        ):
            result = export_transcript_outcome(
                video_url="https://youtu.be/auJzb1D-fag",
                metadata=self.METADATA,
                actual_source="captions",
                actual_quality=0.93,
                success=True,
            )
        assert result is True
        rest.assert_called_once()

    def test_returns_false_when_both_paths_fail(self) -> None:
        with (
            patch(f"{MODULE}._insert_rows", return_value=False),
            patch(f"{MODULE}._insert_via_rest", return_value=False),
        ):
            assert (
                export_transcript_outcome(
                    video_url="https://youtu.be/auJzb1D-fag",
                    metadata=self.METADATA,
                    actual_source="captions",
                    actual_quality=0.93,
                    success=True,
                )
                is False
            )

    def test_serializes_all_fields_and_targets_outcomes_table(self) -> None:
        with patch(f"{MODULE}._insert_rows", return_value=True) as rows:
            export_transcript_outcome(
                video_url="https://youtu.be/auJzb1D-fag",
                metadata=self.METADATA,
                actual_source="captions",
                actual_quality=0.93,
                success=True,
                predicted_source="whisper",
                predicted_quality=0.81,
            )
        table_id, payload = rows.call_args[0]
        assert table_id == TRANSCRIPT_OUTCOMES_TABLE
        assert len(payload) == 1
        row = payload[0]
        _assert_iso_utc(row.pop("exported_at"))
        assert row == {
            "video_url": "https://youtu.be/auJzb1D-fag",
            "actual_source": "captions",
            "actual_quality": 0.93,
            "success": True,
            "predicted_source": "whisper",
            "predicted_quality": 0.81,
            "duration_seconds": 321.0,
            "has_captions": True,
            "language": "en",
            "category": "Education",
            "subscriber_count": 1000,
            "view_count": 50_000,
        }

    def test_absent_metadata_keys_serialize_as_none(self) -> None:
        with patch(f"{MODULE}._insert_rows", return_value=True) as rows:
            export_transcript_outcome(
                video_url="https://youtu.be/auJzb1D-fag",
                metadata={},
                actual_source="whisper",
                actual_quality=0.4,
                success=False,
            )
        row = rows.call_args[0][1][0]
        for key in (
            "duration_seconds",
            "has_captions",
            "language",
            "category",
            "subscriber_count",
            "view_count",
            "predicted_source",
            "predicted_quality",
        ):
            assert row[key] is None, f"{key} should default to None"

    def test_falsy_quality_and_failure_flags_are_preserved(self) -> None:
        """0.0 and False must survive serialization rather than becoming None."""
        with patch(f"{MODULE}._insert_rows", return_value=True) as rows:
            export_transcript_outcome(
                video_url="https://youtu.be/auJzb1D-fag",
                metadata={"has_captions": False},
                actual_source="none",
                actual_quality=0.0,
                success=False,
                predicted_quality=0.0,
            )
        row = rows.call_args[0][1][0]
        assert row["actual_quality"] == 0.0
        assert row["success"] is False
        assert row["has_captions"] is False
        assert row["predicted_quality"] == 0.0


class TestExportActionFeedback:
    def test_serializes_and_targets_feedback_table(self) -> None:
        with patch(f"{MODULE}._insert_rows", return_value=True) as rows:
            assert (
                export_action_feedback(
                    action_text="Draft the summary",
                    clicked=True,
                    completed=False,
                    time_to_complete_seconds=12.5,
                    priority_score=0.7,
                    tier="high",
                    video_url="https://youtu.be/auJzb1D-fag",
                )
                is True
            )
        table_id, payload = rows.call_args[0]
        assert table_id == ACTION_FEEDBACK_TABLE
        row = payload[0]
        _assert_iso_utc(row.pop("exported_at"))
        assert row == {
            "action_text": "Draft the summary",
            "clicked": True,
            "completed": False,
            "time_to_complete_seconds": 12.5,
            "priority_score": 0.7,
            "tier": "high",
            "video_url": "https://youtu.be/auJzb1D-fag",
        }

    def test_falls_back_to_rest(self) -> None:
        with (
            patch(f"{MODULE}._insert_rows", return_value=False),
            patch(f"{MODULE}._insert_via_rest", return_value=True) as rest,
        ):
            assert export_action_feedback("a", clicked=False, completed=False) is True
        rest.assert_called_once()


class TestExportModelCheckpoint:
    SCORER = {
        "version": "1.2.0",
        "training_samples": 10,
        "source_adjustments": {"captions": 0.1},
    }
    RANKER = {
        "version": "0.9.0",
        "training_samples": 20,
        "verb_feedback_weights": {"draft": 0.5},
        "global_feedback_bias": 0.25,
    }

    def test_json_encodes_nested_state_and_targets_checkpoints_table(self) -> None:
        with patch(f"{MODULE}._insert_rows", return_value=True) as rows:
            assert export_model_checkpoint(self.SCORER, self.RANKER) is True
        table_id, payload = rows.call_args[0]
        assert table_id == MODEL_CHECKPOINTS_TABLE
        row = payload[0]
        _assert_iso_utc(row.pop("exported_at"))
        # Nested dicts must be JSON strings, not raw dicts, for BigQuery.
        assert json.loads(row["scorer_source_adjustments"]) == {"captions": 0.1}
        assert json.loads(row["ranker_verb_weights"]) == {"draft": 0.5}
        assert row["scorer_version"] == "1.2.0"
        assert row["ranker_global_bias"] == 0.25

    def test_missing_state_keys_use_documented_defaults(self) -> None:
        with patch(f"{MODULE}._insert_rows", return_value=True) as rows:
            export_model_checkpoint({}, {})
        row = rows.call_args[0][1][0]
        assert row["scorer_version"] == "unknown"
        assert row["ranker_version"] == "unknown"
        assert row["scorer_training_samples"] == 0
        assert row["ranker_training_samples"] == 0
        assert row["ranker_global_bias"] == 0.0
        assert json.loads(row["scorer_source_adjustments"]) == {}


class TestExportPipelineRun:
    def test_serializes_stage_list_as_json_and_targets_runs_table(self) -> None:
        with patch(f"{MODULE}._insert_rows", return_value=True) as rows:
            assert (
                export_pipeline_run(
                    video_url="https://youtu.be/auJzb1D-fag",
                    workflow_template="default",
                    total_duration_seconds=42.0,
                    stages_completed=["capture", "analyze"],
                    success=True,
                    transcript_quality_score=0.88,
                    actions_generated=3,
                )
                is True
            )
        table_id, payload = rows.call_args[0]
        assert table_id == PIPELINE_RUNS_TABLE
        row = payload[0]
        _assert_iso_utc(row.pop("exported_at"))
        assert json.loads(row["stages_completed"]) == ["capture", "analyze"]
        assert row["error_message"] is None
        assert row["actions_generated"] == 3

    def test_omitted_stage_list_becomes_empty_json_array(self) -> None:
        with patch(f"{MODULE}._insert_rows", return_value=True) as rows:
            export_pipeline_run(video_url="https://youtu.be/auJzb1D-fag")
        row = rows.call_args[0][1][0]
        assert json.loads(row["stages_completed"]) == []
        assert row["success"] is True

    def test_failure_details_are_recorded(self) -> None:
        with patch(f"{MODULE}._insert_rows", return_value=True) as rows:
            export_pipeline_run(
                video_url="https://youtu.be/auJzb1D-fag",
                success=False,
                error_message="transcript unavailable",
            )
        row = rows.call_args[0][1][0]
        assert row["success"] is False
        assert row["error_message"] == "transcript unavailable"


@pytest.mark.parametrize(
    ("exporter", "kwargs", "table"),
    [
        (
            export_transcript_outcome,
            {
                "video_url": "https://youtu.be/auJzb1D-fag",
                "metadata": {},
                "actual_source": "captions",
                "actual_quality": 0.5,
                "success": True,
            },
            TRANSCRIPT_OUTCOMES_TABLE,
        ),
        (
            export_action_feedback,
            {"action_text": "a", "clicked": True, "completed": True},
            ACTION_FEEDBACK_TABLE,
        ),
        (
            export_model_checkpoint,
            {"scorer_state": {}, "ranker_state": {}},
            MODEL_CHECKPOINTS_TABLE,
        ),
        (
            export_pipeline_run,
            {"video_url": "https://youtu.be/auJzb1D-fag"},
            PIPELINE_RUNS_TABLE,
        ),
    ],
)
class TestExporterContract:
    """Behavior every public exporter shares."""

    def test_returns_false_when_both_transports_fail(
        self, exporter: Any, kwargs: dict[str, Any], table: str
    ) -> None:
        with (
            patch(f"{MODULE}._insert_rows", return_value=False),
            patch(f"{MODULE}._insert_via_rest", return_value=False),
        ):
            assert exporter(**kwargs) is False

    def test_rest_fallback_retries_the_identical_row(
        self, exporter: Any, kwargs: dict[str, Any], table: str
    ) -> None:
        """The retry must reuse the same row object, not rebuild it.

        Rebuilding would mint a fresh ``exported_at``, so the fallback would
        record a different event time than the attempt it is retrying.
        """
        with (
            patch(f"{MODULE}._insert_rows", return_value=False) as rows,
            patch(f"{MODULE}._insert_via_rest", return_value=True) as rest,
        ):
            exporter(**kwargs)
        assert rows.call_args[0][0] == table
        assert rest.call_args[0][0] == table
        assert rest.call_args[0][1][0] is rows.call_args[0][1][0]

    def test_emits_exactly_one_row_stamped_in_utc(
        self, exporter: Any, kwargs: dict[str, Any], table: str
    ) -> None:
        with patch(f"{MODULE}._insert_rows", return_value=True) as rows:
            exporter(**kwargs)
        payload = rows.call_args[0][1]
        assert len(payload) == 1
        _assert_iso_utc(payload[0]["exported_at"])
