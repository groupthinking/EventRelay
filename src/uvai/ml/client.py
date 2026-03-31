from __future__ import annotations

import json
import logging
import os
from typing import Any
from urllib import error, request

from uvai.ml.models.action_priority_ranker import ActionPriorityRanker
from uvai.ml.models.transcript_quality_scorer import TranscriptQualityScorer

logger = logging.getLogger(__name__)


class UVAIMLClient:
    """Thin client for UVAI ML endpoints with a local-model fallback."""

    def __init__(self, base_url: str | None = None, timeout: float = 5.0) -> None:
        self.base_url = (base_url or os.getenv("UVAI_ML_SERVICE_URL") or "").rstrip("/")
        self.timeout = timeout
        self._scorer = TranscriptQualityScorer()
        self._ranker = ActionPriorityRanker()

    async def score_transcript(self, metadata: dict[str, Any]) -> dict[str, Any]:
        if self.base_url:
            result = self._post_json("/score-transcript", {"metadata": metadata})
            if result is not None:
                return result

        prediction = self._scorer.predict(metadata)
        return {
            "quality_score": prediction.quality_score,
            "recommended_source": prediction.recommended_source,
            "confidence": prediction.confidence,
            "processing_estimate_seconds": prediction.processing_estimate_seconds,
            "reasoning": prediction.reasoning,
            "feature_importances": prediction.feature_importances,
            "model": self._scorer.model_info,
        }

    async def record_transcript_outcome(
        self,
        *,
        metadata: dict[str, Any],
        actual_source: str,
        actual_quality: float,
        success: bool,
    ) -> dict[str, Any]:
        payload = {
            "metadata": metadata,
            "actual_source": actual_source,
            "actual_quality": actual_quality,
            "success": success,
        }
        if self.base_url:
            result = self._post_json("/score-transcript/outcome", payload)
            if result is not None:
                return result

        features = self._scorer.extract_features(metadata)
        self._scorer.record_outcome(
            features=features,
            actual_source=actual_source,
            actual_quality=actual_quality,
            success=success,
        )
        return {
            "recorded": True,
            "total_samples": self._scorer.model_info["training_samples"],
        }

    async def rank_actions(
        self,
        actions: list[str | dict[str, Any]],
        *,
        video_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        payload = {
            "actions": actions,
            "video_context": video_context or {},
        }
        if self.base_url:
            result = self._post_json("/rank-actions", payload)
            if result is not None:
                return result

        ranking = self._ranker.rank(actions, video_context=video_context)
        return {
            "ranked_actions": [
                {
                    "text": item.original_text,
                    "priority_score": item.priority_score,
                    "tier": item.tier.value,
                    "reasoning": item.reasoning,
                    "original_index": item.original_index,
                    "features": dict(item.features),
                }
                for item in ranking.ranked_actions
            ],
            "total_actions": ranking.total_actions,
            "processing_time_seconds": ranking.processing_time_seconds,
            "model": self._ranker.model_info,
        }

    async def record_action_feedback(
        self,
        *,
        action_text: str,
        clicked: bool,
        completed: bool,
        time_to_complete_seconds: float | None = None,
    ) -> dict[str, Any]:
        payload = {
            "action_text": action_text,
            "clicked": clicked,
            "completed": completed,
            "time_to_complete_seconds": time_to_complete_seconds,
        }
        if self.base_url:
            result = self._post_json("/rank-actions/feedback", payload)
            if result is not None:
                return result

        self._ranker.record_feedback(
            action_text=action_text,
            user_clicked=clicked,
            user_completed=completed,
            time_to_complete_seconds=time_to_complete_seconds,
        )
        return {
            "recorded": True,
            "total_samples": self._ranker.model_info["training_samples"],
        }

    def _post_json(self, path: str, payload: dict[str, Any]) -> dict[str, Any] | None:
        endpoint = f"{self.base_url}{path}"
        body = json.dumps(payload).encode("utf-8")
        req = request.Request(
            endpoint,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=self.timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except (OSError, ValueError, error.HTTPError) as exc:
            logger.debug("UVAI ML request failed for %s: %s", endpoint, exc)
            return None


_uvai_ml_client: UVAIMLClient | None = None


def get_uvai_ml_client() -> UVAIMLClient:
    global _uvai_ml_client

    if _uvai_ml_client is None:
        _uvai_ml_client = UVAIMLClient()

    return _uvai_ml_client
