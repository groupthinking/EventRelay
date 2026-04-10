"""Phase 2 — Weight Persistence & Gradient Checkpoint Manager.

Persists learned model weights (source adjustments, verb feedback weights,
global bias) to disk and optionally to GCS, enabling continuity across
Ray Serve restarts and rolling deployments.

Checkpoint format:
    {
        "version": "2.0.0",
        "timestamp": "2026-04-01T...",
        "scorer": {
            "source_adjustments": {...},
            "training_samples": 42,
            "version": "1.1.0-online"
        },
        "ranker": {
            "verb_feedback_weights": {...},
            "global_feedback_bias": 0.01,
            "training_samples": 38,
            "version": "1.1.0-online"
        }
    }
"""

from __future__ import annotations

import json
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

CHECKPOINT_DIR = Path(
    os.getenv("UVAI_CHECKPOINT_DIR", "/tmp/uvai-ml-checkpoints")
)
CHECKPOINT_FILE = CHECKPOINT_DIR / "latest.json"
CHECKPOINT_HISTORY_DIR = CHECKPOINT_DIR / "history"
MAX_HISTORY = int(os.getenv("UVAI_MAX_CHECKPOINT_HISTORY", "50"))
GCS_BUCKET = os.getenv("UVAI_GCS_CHECKPOINT_BUCKET")
GCS_PREFIX = os.getenv("UVAI_GCS_CHECKPOINT_PREFIX", "ml-checkpoints/")


def _ensure_dirs() -> None:
    """Create checkpoint directories if they don't exist."""
    CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
    CHECKPOINT_HISTORY_DIR.mkdir(parents=True, exist_ok=True)


def save_checkpoint(
    scorer_state: dict[str, Any],
    ranker_state: dict[str, Any],
) -> Path:
    """Persist current model weights to disk (and optionally GCS).

    Args:
        scorer_state: TranscriptQualityScorer serialized state.
        ranker_state: ActionPriorityRanker serialized state.

    Returns:
        Path to the saved checkpoint file.
    """
    _ensure_dirs()

    now = datetime.now(timezone.utc)
    checkpoint = {
        "version": "2.0.0",
        "timestamp": now.isoformat(),
        "epoch_seconds": time.time(),
        "scorer": scorer_state,
        "ranker": ranker_state,
    }

    payload = json.dumps(checkpoint, indent=2, default=str)

    # Write latest checkpoint (atomic via temp + rename)
    tmp_path = CHECKPOINT_FILE.with_suffix(".tmp")
    tmp_path.write_text(payload, encoding="utf-8")
    tmp_path.rename(CHECKPOINT_FILE)

    # Write timestamped copy for history
    ts_name = now.strftime("%Y%m%dT%H%M%SZ") + ".json"
    history_path = CHECKPOINT_HISTORY_DIR / ts_name
    history_path.write_text(payload, encoding="utf-8")

    # Prune old history files
    _prune_history()

    # Upload to GCS if configured
    if GCS_BUCKET:
        _upload_to_gcs(payload, ts_name)

    total_samples = (
        scorer_state.get("training_samples", 0)
        + ranker_state.get("training_samples", 0)
    )
    logger.info(
        "Checkpoint saved: %s (total training samples: %d)",
        CHECKPOINT_FILE,
        total_samples,
    )

    return CHECKPOINT_FILE


def load_checkpoint() -> dict[str, Any] | None:
    """Load the latest checkpoint from disk.

    Returns:
        Checkpoint dict or None if no checkpoint exists.
    """
    if not CHECKPOINT_FILE.exists():
        logger.info("No checkpoint found at %s", CHECKPOINT_FILE)
        return None

    try:
        raw = CHECKPOINT_FILE.read_text(encoding="utf-8")
        checkpoint = json.loads(raw)
        logger.info(
            "Loaded checkpoint from %s (saved at %s, scorer samples=%d, ranker samples=%d)",
            CHECKPOINT_FILE,
            checkpoint.get("timestamp", "unknown"),
            checkpoint.get("scorer", {}).get("training_samples", 0),
            checkpoint.get("ranker", {}).get("training_samples", 0),
        )
        return checkpoint
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Failed to load checkpoint: %s", exc)
        return None


def restore_scorer(
    scorer: Any,
    checkpoint: dict[str, Any],
) -> None:
    """Restore TranscriptQualityScorer state from a checkpoint.

    Args:
        scorer: TranscriptQualityScorer instance.
        checkpoint: Full checkpoint dict.
    """
    state = checkpoint.get("scorer")
    if not state:
        return

    if "source_adjustments" in state:
        scorer._source_adjustments = dict(state["source_adjustments"])
        scorer._weights = dict(state["source_adjustments"])

    if "training_samples" in state:
        scorer._training_samples = int(state["training_samples"])

    if "version" in state:
        scorer._version = str(state["version"])

    logger.info(
        "Restored scorer: %d training samples, version=%s",
        scorer._training_samples,
        scorer._version,
    )


def restore_ranker(
    ranker: Any,
    checkpoint: dict[str, Any],
) -> None:
    """Restore ActionPriorityRanker state from a checkpoint.

    Args:
        ranker: ActionPriorityRanker instance.
        checkpoint: Full checkpoint dict.
    """
    state = checkpoint.get("ranker")
    if not state:
        return

    if "verb_feedback_weights" in state:
        ranker._verb_feedback_weights = dict(state["verb_feedback_weights"])

    if "global_feedback_bias" in state:
        ranker._global_feedback_bias = float(state["global_feedback_bias"])

    if "training_samples" in state:
        ranker._training_samples = int(state["training_samples"])

    if "version" in state:
        ranker._version = str(state["version"])

    logger.info(
        "Restored ranker: %d training samples, version=%s",
        ranker._training_samples,
        ranker._version,
    )


def serialize_scorer(scorer: Any) -> dict[str, Any]:
    """Extract serializable state from TranscriptQualityScorer."""
    return {
        "source_adjustments": dict(getattr(scorer, "_source_adjustments", {})),
        "training_samples": getattr(scorer, "_training_samples", 0),
        "version": getattr(scorer, "_version", "unknown"),
    }


def serialize_ranker(ranker: Any) -> dict[str, Any]:
    """Extract serializable state from ActionPriorityRanker."""
    return {
        "verb_feedback_weights": dict(
            getattr(ranker, "_verb_feedback_weights", {})
        ),
        "global_feedback_bias": getattr(ranker, "_global_feedback_bias", 0.0),
        "training_samples": getattr(ranker, "_training_samples", 0),
        "version": getattr(ranker, "_version", "unknown"),
    }


def _prune_history() -> None:
    """Keep only the most recent MAX_HISTORY checkpoint files."""
    try:
        files = sorted(
            CHECKPOINT_HISTORY_DIR.glob("*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        for old_file in files[MAX_HISTORY:]:
            old_file.unlink(missing_ok=True)
    except OSError:
        pass


def _upload_to_gcs(payload: str, filename: str) -> None:
    """Upload checkpoint to Google Cloud Storage (best-effort)."""
    try:
        from google.cloud import storage  # type: ignore[import-untyped]

        client = storage.Client()
        bucket = client.bucket(GCS_BUCKET)

        # Upload latest
        latest_blob = bucket.blob(f"{GCS_PREFIX}latest.json")
        latest_blob.upload_from_string(payload, content_type="application/json")

        # Upload timestamped copy
        history_blob = bucket.blob(f"{GCS_PREFIX}history/{filename}")
        history_blob.upload_from_string(payload, content_type="application/json")

        logger.info("Checkpoint uploaded to gs://%s/%s", GCS_BUCKET, GCS_PREFIX)
    except Exception as exc:
        logger.warning("GCS checkpoint upload failed (non-fatal): %s", exc)
