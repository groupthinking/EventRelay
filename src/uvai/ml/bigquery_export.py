"""BigQuery Training Data Export — Phase 2 Pipeline Integration.

Exports ML model training data (transcript quality outcomes, action ranking
feedback) to BigQuery for offline analysis, model retraining, and dashboard
reporting.

Tables:
    - {dataset}.transcript_quality_outcomes
    - {dataset}.action_ranking_feedback
    - {dataset}.model_checkpoints

Requires:
    - GOOGLE_CLOUD_PROJECT env var
    - TRAINING_BIGQUERY_DATASET env var (default: "uvai_ml_training")
    - Application Default Credentials or service account key
"""

from __future__ import annotations

import json
import logging
import os
import time
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "uvai-730bb")
DATASET_ID = os.getenv("TRAINING_BIGQUERY_DATASET", "uvai_ml_training")

# Table names
TRANSCRIPT_OUTCOMES_TABLE = "transcript_quality_outcomes"
ACTION_FEEDBACK_TABLE = "action_ranking_feedback"
MODEL_CHECKPOINTS_TABLE = "model_checkpoints"
PIPELINE_RUNS_TABLE = "pipeline_runs"


def _get_bq_client() -> Any:
    """Lazy-load BigQuery client."""
    try:
        from google.cloud import bigquery  # type: ignore[import-untyped]
        return bigquery.Client(project=PROJECT_ID)
    except ImportError:
        logger.debug("google-cloud-bigquery not installed; BigQuery export disabled")
        return None
    except Exception as exc:
        logger.debug("BigQuery client init failed: %s", exc)
        return None


def _insert_rows(table_id: str, rows: list[dict[str, Any]]) -> bool:
    """Insert rows into a BigQuery table. Returns True on success."""
    client = _get_bq_client()
    if client is None:
        return False

    table_ref = f"{PROJECT_ID}.{DATASET_ID}.{table_id}"
    try:
        errors = client.insert_rows_json(table_ref, rows)
        if errors:
            logger.warning("BigQuery insert errors for %s: %s", table_ref, errors)
            return False
        logger.info("Exported %d rows to %s", len(rows), table_ref)
        return True
    except Exception as exc:
        logger.warning("BigQuery export failed for %s: %s", table_ref, exc)
        return False


def _insert_via_rest(table_id: str, rows: list[dict[str, Any]]) -> bool:
    """Fallback: insert via REST API using metadata server token (for Cloud Run)."""
    try:
        import urllib.request
        import urllib.error

        # Get access token from metadata server
        token_url = (
            "http://metadata.google.internal/computeMetadata/v1/"
            "instance/service-accounts/default/token"
        )
        req = urllib.request.Request(
            token_url,
            headers={"Metadata-Flavor": "Google"},
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            token_data = json.loads(resp.read().decode())
            access_token = token_data.get("access_token")

        if not access_token:
            return False

        insert_url = (
            f"https://bigquery.googleapis.com/bigquery/v2/projects/{PROJECT_ID}"
            f"/datasets/{DATASET_ID}/tables/{table_id}/insertAll"
        )

        body = json.dumps({
            "rows": [
                {"insertId": f"{time.time_ns()}_{i}", "json": row}
                for i, row in enumerate(rows)
            ]
        }).encode("utf-8")

        req = urllib.request.Request(
            insert_url,
            data=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {access_token}",
            },
            method="POST",
        )

        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read().decode())
            if result.get("insertErrors"):
                logger.warning("BigQuery REST insert errors: %s", result["insertErrors"])
                return False
            logger.info("Exported %d rows to %s via REST", len(rows), table_id)
            return True

    except Exception as exc:
        logger.debug("BigQuery REST export failed: %s", exc)
        return False


def export_transcript_outcome(
    outcome: dict[str, Any],
) -> bool:
    """Export a transcript quality outcome to BigQuery."""
    metadata = outcome.get("metadata") or {}
    row = {
        "video_url": outcome.get("video_url"),
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "actual_source": outcome.get("actual_source"),
        "actual_quality": outcome.get("actual_quality"),
        "success": outcome.get("success"),
        "predicted_source": outcome.get("predicted_source"),
        "predicted_quality": outcome.get("predicted_quality"),
        "duration_seconds": metadata.get("duration_seconds"),
        "has_captions": metadata.get("has_captions"),
        "language": metadata.get("language"),
        "category": metadata.get("category"),
        "subscriber_count": metadata.get("subscriber_count"),
        "view_count": metadata.get("view_count"),
    }

    success_flag = _insert_rows(TRANSCRIPT_OUTCOMES_TABLE, [row])
    if not success_flag:
        success_flag = _insert_via_rest(TRANSCRIPT_OUTCOMES_TABLE, [row])
    return success_flag


def export_action_feedback(
    action_text: str,
    clicked: bool,
    completed: bool,
    time_to_complete_seconds: float | None = None,
    priority_score: float | None = None,
    tier: str | None = None,
    video_url: str | None = None,
) -> bool:
    """Export action ranking feedback to BigQuery."""
    row = {
        "action_text": action_text,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "clicked": clicked,
        "completed": completed,
        "time_to_complete_seconds": time_to_complete_seconds,
        "priority_score": priority_score,
        "tier": tier,
        "video_url": video_url,
    }

    success = _insert_rows(ACTION_FEEDBACK_TABLE, [row])
    if not success:
        success = _insert_via_rest(ACTION_FEEDBACK_TABLE, [row])
    return success


def export_model_checkpoint(
    scorer_state: dict[str, Any],
    ranker_state: dict[str, Any],
) -> bool:
    """Export model checkpoint metadata to BigQuery for tracking."""
    row = {
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "scorer_version": scorer_state.get("version", "unknown"),
        "scorer_training_samples": scorer_state.get("training_samples", 0),
        "scorer_source_adjustments": json.dumps(
            scorer_state.get("source_adjustments", {})
        ),
        "ranker_version": ranker_state.get("version", "unknown"),
        "ranker_training_samples": ranker_state.get("training_samples", 0),
        "ranker_verb_weights": json.dumps(
            ranker_state.get("verb_feedback_weights", {})
        ),
        "ranker_global_bias": ranker_state.get("global_feedback_bias", 0.0),
    }

    success = _insert_rows(MODEL_CHECKPOINTS_TABLE, [row])
    if not success:
        success = _insert_via_rest(MODEL_CHECKPOINTS_TABLE, [row])
    return success


def export_pipeline_run(
    video_url: str,
    workflow_template: str | None = None,
    total_duration_seconds: float | None = None,
    stages_completed: list[str] | None = None,
    success: bool = True,
    error_message: str | None = None,
    transcript_quality_score: float | None = None,
    actions_generated: int | None = None,
) -> bool:
    """Export a complete pipeline run summary to BigQuery."""
    row = {
        "video_url": video_url,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "workflow_template": workflow_template,
        "total_duration_seconds": total_duration_seconds,
        "stages_completed": json.dumps(stages_completed or []),
        "success": success,
        "error_message": error_message,
        "transcript_quality_score": transcript_quality_score,
        "actions_generated": actions_generated,
    }

    success_flag = _insert_rows(PIPELINE_RUNS_TABLE, [row])
    if not success_flag:
        success_flag = _insert_via_rest(PIPELINE_RUNS_TABLE, [row])
    return success_flag
