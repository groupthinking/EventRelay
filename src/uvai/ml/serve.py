"""UVAI ML Ray Serve Application — Phase 2.

Architecture:
    Each model deployment handles its own route directly.
    The router extracts request bodies and passes plain dicts
    to avoid Starlette Request serialization issues.

Phase 2 additions:
    - Weight persistence: auto-checkpoint after every N outcomes
    - Restore from checkpoint on startup (survives restarts)
    - BigQuery export for training data pipeline
    - EMA-smoothed gradient updates with configurable learning rate

Endpoints:
    GET  /health                → service health
    GET  /models                → model metadata
    POST /score-transcript      → predict transcript quality
    POST /score-transcript/outcome → record actual results + checkpoint
    POST /rank-actions          → rank actions by priority
    POST /rank-actions/feedback → record user feedback + checkpoint
    POST /checkpoint            → force save checkpoint
    GET  /checkpoint            → view latest checkpoint info

Usage:
    serve deploy ray-serve-config.yaml
"""

from __future__ import annotations

import logging
import os
import time
from typing import Any

from ray import serve
from starlette.requests import Request
from starlette.responses import JSONResponse

from uvai.ml.models.action_priority_ranker import (
    ActionPriorityRanker,
)
from uvai.ml.models.transcript_quality_scorer import (
    TranscriptQualityScorer,
)
from uvai.ml.weight_persistence import (
    load_checkpoint,
    restore_ranker,
    restore_scorer,
    save_checkpoint,
    serialize_ranker,
    serialize_scorer,
)

logger = logging.getLogger(__name__)

# Auto-checkpoint every N training samples
CHECKPOINT_INTERVAL = int(os.getenv("UVAI_CHECKPOINT_INTERVAL", "10"))


@serve.deployment(
    name="transcript-quality-scorer",
    num_replicas=1,
    ray_actor_options={"num_cpus": 0.5},
)
class TranscriptQualityScorerDeployment:
    """Transcript quality prediction model with Phase 2 persistence."""

    def __init__(self) -> None:
        self.model = TranscriptQualityScorer()
        self._samples_since_checkpoint = 0

        # Restore from checkpoint if available
        checkpoint = load_checkpoint()
        if checkpoint:
            restore_scorer(self.model, checkpoint)

        logger.info(
            "TranscriptQualityScorer initialized: %s",
            self.model.model_info,
        )

    def predict(self, metadata: dict[str, Any]) -> dict:
        """Score transcript quality from metadata dict."""
        prediction = self.model.predict(metadata)
        return {
            "quality_score": prediction.quality_score,
            "recommended_source": prediction.recommended_source,
            "confidence": prediction.confidence,
            "processing_estimate_seconds": (
                prediction.processing_estimate_seconds
            ),
            "reasoning": prediction.reasoning,
            "feature_importances": prediction.feature_importances,
            "model": self.model.model_info,
        }

    def record_outcome(
        self, body: dict[str, Any],
    ) -> dict:
        """Record actual result for continuous learning + auto-checkpoint."""
        features = self.model.extract_features(
            body.get("metadata", {}),
        )
        self.model.record_outcome(
            features=features,
            actual_source=body.get("actual_source", "unknown"),
            actual_quality=float(
                body.get("actual_quality", 0.0),
            ),
            success=bool(body.get("success", False)),
        )

        self._samples_since_checkpoint += 1
        checkpoint_saved = False
        if self._samples_since_checkpoint >= CHECKPOINT_INTERVAL:
            self._save_checkpoint()
            checkpoint_saved = True

        # Export to BigQuery (best-effort)
        self._export_outcome_to_bigquery(body)

        return {
            "recorded": True,
            "total_samples": self.model._training_samples,
            "checkpoint_saved": checkpoint_saved,
        }

    def get_model_info(self) -> dict:
        """Return model metadata."""
        return self.model.model_info

    def get_serialized_state(self) -> dict:
        """Return serializable state for checkpointing."""
        return serialize_scorer(self.model)

    def _save_checkpoint(self) -> None:
        """Save scorer checkpoint. Ranker state will be empty here."""
        try:
            save_checkpoint(
                scorer_state=serialize_scorer(self.model),
                ranker_state={},
            )
            self._samples_since_checkpoint = 0
        except Exception as exc:
            logger.warning("Scorer checkpoint failed: %s", exc)

    def _export_outcome_to_bigquery(self, body: dict[str, Any]) -> None:
        """Best-effort BigQuery export."""
        try:
            from uvai.ml.bigquery_export import export_transcript_outcome
            export_transcript_outcome(
                video_url=body.get("metadata", {}).get("video_url", ""),
                metadata=body.get("metadata", {}),
                actual_source=body.get("actual_source", "unknown"),
                actual_quality=float(body.get("actual_quality", 0.0)),
                success=bool(body.get("success", False)),
            )
        except Exception:
            logger.debug("BigQuery export skipped", exc_info=True)


@serve.deployment(
    name="action-priority-ranker",
    num_replicas=1,
    ray_actor_options={"num_cpus": 0.5},
)
class ActionPriorityRankerDeployment:
    """Action priority ranking model with Phase 2 persistence."""

    def __init__(self) -> None:
        self.model = ActionPriorityRanker()
        self._samples_since_checkpoint = 0

        # Restore from checkpoint if available
        checkpoint = load_checkpoint()
        if checkpoint:
            restore_ranker(self.model, checkpoint)

        logger.info(
            "ActionPriorityRanker initialized: %s",
            self.model.model_info,
        )

    def rank(
        self,
        actions: list,
        video_context: dict[str, Any] | None = None,
    ) -> dict:
        """Rank actions by priority."""
        result = self.model.rank(
            actions, video_context=video_context,
        )
        return {
            "ranked_actions": [
                {
                    "text": a.original_text,
                    "priority_score": a.priority_score,
                    "tier": a.tier.value,
                    "reasoning": a.reasoning,
                    "original_index": a.original_index,
                }
                for a in result.ranked_actions
            ],
            "total_actions": result.total_actions,
            "processing_time_seconds": (
                result.processing_time_seconds
            ),
            "model": self.model.model_info,
        }

    def record_feedback(self, body: dict[str, Any]) -> dict:
        """Record user interaction for continuous learning + auto-checkpoint."""
        self.model.record_feedback(
            action_text=body.get("action_text", ""),
            user_clicked=bool(body.get("clicked", False)),
            user_completed=bool(
                body.get("completed", False),
            ),
            time_to_complete_seconds=body.get(
                "time_to_complete_seconds",
            ),
        )

        self._samples_since_checkpoint += 1
        checkpoint_saved = False
        if self._samples_since_checkpoint >= CHECKPOINT_INTERVAL:
            self._save_checkpoint()
            checkpoint_saved = True

        # Export to BigQuery (best-effort)
        self._export_feedback_to_bigquery(body)

        return {
            "recorded": True,
            "total_samples": self.model._training_samples,
            "checkpoint_saved": checkpoint_saved,
        }

    def get_model_info(self) -> dict:
        """Return model metadata."""
        return self.model.model_info

    def get_serialized_state(self) -> dict:
        """Return serializable state for checkpointing."""
        return serialize_ranker(self.model)

    def _save_checkpoint(self) -> None:
        """Save ranker checkpoint. Scorer state will be empty here."""
        try:
            save_checkpoint(
                scorer_state={},
                ranker_state=serialize_ranker(self.model),
            )
            self._samples_since_checkpoint = 0
        except Exception as exc:
            logger.warning("Ranker checkpoint failed: %s", exc)

    def _export_feedback_to_bigquery(self, body: dict[str, Any]) -> None:
        """Best-effort BigQuery export."""
        try:
            from uvai.ml.bigquery_export import export_action_feedback
            export_action_feedback(
                action_text=body.get("action_text", ""),
                clicked=bool(body.get("clicked", False)),
                completed=bool(body.get("completed", False)),
                time_to_complete_seconds=body.get("time_to_complete_seconds"),
            )
        except Exception:
            logger.debug("BigQuery export skipped", exc_info=True)


@serve.deployment(
    name="uvai-ml-router",
    num_replicas=1,
    ray_actor_options={"num_cpus": 0.25},
    route_prefix="/",
)
class UVAIMLRouter:
    """HTTP router — extracts JSON bodies and dispatches
    plain dicts to model deployments (avoiding Request
    serialization issues).
    """

    def __init__(
        self,
        scorer: TranscriptQualityScorerDeployment,
        ranker: ActionPriorityRankerDeployment,
    ) -> None:
        self.scorer = scorer
        self.ranker = ranker
        self._start_time = time.time()

    async def __call__(
        self, request: Request,
    ) -> JSONResponse:
        path = request.url.path.rstrip("/")

        # --- Health ---
        if path in ("/health", ""):
            return JSONResponse({
                "status": "healthy",
                "uptime_seconds": round(
                    time.time() - self._start_time, 2,
                ),
                "models": [
                    "transcript-quality-scorer",
                    "action-priority-ranker",
                ],
                "version": "2.0.0",
                "phase": "2",
            })

        # --- Models metadata ---
        if path == "/models":
            scorer_info = await (
                self.scorer.get_model_info.remote()
            )
            ranker_info = await (
                self.ranker.get_model_info.remote()
            )
            return JSONResponse({
                "models": {
                    "transcript_quality_scorer": scorer_info,
                    "action_priority_ranker": ranker_info,
                },
            })

        # --- Parse body for POST routes ---
        body: dict[str, Any] = {}
        if request.method == "POST":
            try:
                body = await request.json()
            except Exception:
                return JSONResponse(
                    {"error": "Invalid JSON body"},
                    status_code=400,
                )

        # --- Score transcript ---
        if path == "/score-transcript":
            metadata = body.get("metadata")
            if not metadata or not isinstance(metadata, dict):
                return JSONResponse(
                    {"error": "Missing 'metadata' dict"},
                    status_code=400,
                )
            result = await (
                self.scorer.predict.remote(metadata)
            )
            return JSONResponse(result)

        if path == "/score-transcript/outcome":
            result = await (
                self.scorer.record_outcome.remote(body)
            )
            return JSONResponse(result)

        # --- Rank actions ---
        if path == "/rank-actions":
            actions = body.get("actions")
            if not actions or not isinstance(actions, list):
                return JSONResponse(
                    {"error": "Missing 'actions' list"},
                    status_code=400,
                )
            video_context = body.get("video_context")
            result = await (
                self.ranker.rank.remote(
                    actions, video_context,
                )
            )
            return JSONResponse(result)

        if path == "/rank-actions/feedback":
            result = await (
                self.ranker.record_feedback.remote(body)
            )
            return JSONResponse(result)

        # --- Checkpoint management (Phase 2) ---
        if path == "/checkpoint":
            if request.method == "POST":
                # Force save checkpoint
                scorer_state = await self.scorer.get_serialized_state.remote()
                ranker_state = await self.ranker.get_serialized_state.remote()
                try:
                    save_checkpoint(scorer_state, ranker_state)

                    # Also export to BigQuery
                    try:
                        from uvai.ml.bigquery_export import export_model_checkpoint
                        export_model_checkpoint(scorer_state, ranker_state)
                    except Exception:
                        pass

                    return JSONResponse({
                        "saved": True,
                        "scorer_samples": scorer_state.get("training_samples", 0),
                        "ranker_samples": ranker_state.get("training_samples", 0),
                    })
                except Exception as exc:
                    # Log the full error server-side; return a static body so the
                    # exception text does not leak to the client (CWE-209).
                    logger.error("Checkpoint save failed: %s", exc, exc_info=True)
                    return JSONResponse(
                        {"error": "Internal server error"},
                        status_code=500,
                    )
            else:
                # GET: view checkpoint info
                checkpoint = load_checkpoint()
                if checkpoint:
                    return JSONResponse(checkpoint)
                return JSONResponse(
                    {"error": "No checkpoint found"},
                    status_code=404,
                )

        # --- 404 ---
        return JSONResponse(
            {
                "error": f"Unknown path: {path}",
                "available_endpoints": [
                    "/health",
                    "/models",
                    "/score-transcript",
                    "/score-transcript/outcome",
                    "/rank-actions",
                    "/rank-actions/feedback",
                    "/checkpoint",
                ],
            },
            status_code=404,
        )


# --- Deployment graph ---
scorer = TranscriptQualityScorerDeployment.bind()
ranker = ActionPriorityRankerDeployment.bind()
app = UVAIMLRouter.bind(scorer, ranker)
