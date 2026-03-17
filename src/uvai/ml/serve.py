"""UVAI Ray Serve deployment — serves ML models via HTTP.

Architecture:
    Each model deployment handles its own route directly.
    The router extracts request bodies and passes plain dicts
    to avoid Starlette Request serialization issues.

Endpoints:
    GET  /health                → service health
    POST /score-transcript      → predict transcript quality
    POST /score-transcript/outcome → record actual results
    POST /rank-actions          → rank actions by priority
    POST /rank-actions/feedback → record user feedback

Usage:
    serve deploy ray-serve-config.yaml
"""

from __future__ import annotations

import logging
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

logger = logging.getLogger(__name__)


@serve.deployment(
    name="transcript-quality-scorer",
    num_replicas=1,
    ray_actor_options={"num_cpus": 0.5},
)
class TranscriptQualityScorerDeployment:
    """Transcript quality prediction model."""

    def __init__(self) -> None:
        self.model = TranscriptQualityScorer()
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
        """Record actual result for continuous learning."""
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
        return {
            "recorded": True,
            "total_samples": self.model._training_samples,
        }

    def get_model_info(self) -> dict:
        """Return model metadata."""
        return self.model.model_info


@serve.deployment(
    name="action-priority-ranker",
    num_replicas=1,
    ray_actor_options={"num_cpus": 0.5},
)
class ActionPriorityRankerDeployment:
    """Action priority ranking model."""

    def __init__(self) -> None:
        self.model = ActionPriorityRanker()
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
        """Record user interaction for continuous learning."""
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
        return {
            "recorded": True,
            "total_samples": self.model._training_samples,
        }

    def get_model_info(self) -> dict:
        """Return model metadata."""
        return self.model.model_info


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
                "version": "1.0.0",
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
                ],
            },
            status_code=404,
        )


# --- Deployment graph ---

scorer = TranscriptQualityScorerDeployment.bind()
ranker = ActionPriorityRankerDeployment.bind()
app = UVAIMLRouter.bind(scorer, ranker)
