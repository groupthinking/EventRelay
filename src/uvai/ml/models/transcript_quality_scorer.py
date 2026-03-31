"""Transcript Quality Scorer — Model #1.

Predicts the quality/accuracy of a transcript BEFORE full processing,
allowing the pipeline to select the optimal extraction source and allocate
resources intelligently.

Features used:
    - Video duration (seconds)
    - Has closed captions (bool)
    - Language code
    - Channel subscriber tier
    - Video category
    - View count tier
    - Transcript source attempted

Output:
    - quality_score: 0.0 – 1.0 (predicted accuracy)
    - recommended_source: best extraction method
    - confidence: model confidence in prediction
    - processing_estimate_seconds: predicted processing time
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class TranscriptSource(str, Enum):
    """Available transcript extraction sources."""

    YOUTUBE_API = "youtube_api"
    SPEECH_TO_TEXT = "speech_v2"
    GEMINI_VIDEO = "gemini_video"
    GEMINI_FILE = "gemini_video_file"
    PROVIDED = "provided"


@dataclass
class QualityPrediction:
    """Output of the quality scoring model."""

    quality_score: float  # 0.0–1.0
    recommended_source: str
    confidence: float
    processing_estimate_seconds: float
    feature_importances: dict[str, float] = field(default_factory=dict)
    reasoning: str = ""


@dataclass
class VideoFeatures:
    """Extracted features from video metadata for scoring."""

    duration_seconds: float = 0.0
    has_captions: bool = False
    language: str = "en"
    subscriber_count: int = 0
    view_count: int = 0
    category: str = "unknown"
    is_live: bool = False
    is_short: bool = False
    title_length: int = 0
    description_length: int = 0


class TranscriptQualityScorer:
    """Heuristic + learned model for transcript quality prediction.

    Phase 1: Rule-based heuristics derived from pipeline observations.
    Phase 2: Trains on accumulated pipeline results for continuous improvement.
    """

    # Source reliability priors (from observed pipeline performance)
    SOURCE_PRIORS: dict[str, float] = {
        TranscriptSource.YOUTUBE_API: 0.92,
        TranscriptSource.SPEECH_TO_TEXT: 0.78,
        TranscriptSource.GEMINI_VIDEO: 0.85,
        TranscriptSource.GEMINI_FILE: 0.80,
        TranscriptSource.PROVIDED: 0.95,
    }

    # Processing time estimates per source (seconds)
    SOURCE_LATENCY: dict[str, float] = {
        TranscriptSource.YOUTUBE_API: 2.0,
        TranscriptSource.SPEECH_TO_TEXT: 15.0,
        TranscriptSource.GEMINI_VIDEO: 8.0,
        TranscriptSource.GEMINI_FILE: 25.0,
        TranscriptSource.PROVIDED: 0.1,
    }

    # Language support tiers
    TIER1_LANGUAGES: set[str] = {
        "en", "es", "fr", "de", "pt", "ja", "ko", "zh",
    }
    TIER2_LANGUAGES: set[str] = {
        "it", "nl", "ru", "ar", "hi", "id", "tr", "pl",
    }
    MAX_SOURCE_ADJUSTMENT = 0.35

    def __init__(self) -> None:
        self._weights: dict[str, float] | None = None
        self._training_samples: int = 0
        self._version: str = "1.0.0-heuristic"
        self._source_adjustments: dict[str, float] = {
            source.value: 0.0 for source in TranscriptSource
        }

    def extract_features(self, metadata: dict[str, Any]) -> VideoFeatures:
        """Extract scoring features from raw video metadata."""

        duration = float(
            metadata.get("duration_seconds")
            or metadata.get("duration")
            or 0
        )

        has_captions = bool(
            metadata.get("has_captions")
            or metadata.get("captions_available")
        )

        language = str(
            metadata.get("language")
            or metadata.get("default_audio_language")
            or "en"
        )
        if "-" in language:
            language = language.split("-")[0]

        subscriber_count = int(metadata.get("subscriber_count") or 0)
        view_count = int(metadata.get("view_count") or 0)

        category = str(
            metadata.get("category")
            or metadata.get("category_id")
            or "unknown"
        )

        is_live = bool(metadata.get("is_live") or metadata.get("was_live"))
        is_short = duration > 0 and duration <= 60

        title = str(metadata.get("title") or "")
        description = str(metadata.get("description") or "")

        return VideoFeatures(
            duration_seconds=duration,
            has_captions=has_captions,
            language=language.lower(),
            subscriber_count=subscriber_count,
            view_count=view_count,
            category=category,
            is_live=is_live,
            is_short=is_short,
            title_length=len(title),
            description_length=len(description),
        )

    def predict(self, metadata: dict[str, Any]) -> QualityPrediction:
        """Score transcript quality and recommend extraction source."""

        start_time = time.monotonic()
        features = self.extract_features(metadata)

        # Score each source
        source_scores: dict[str, float] = {}
        importances: dict[str, float] = {}

        for source in TranscriptSource:
            if source == TranscriptSource.PROVIDED:
                continue
            score, feature_weights = self._score_source(source, features)
            source_scores[source.value] = score
            importances[source.value] = sum(feature_weights.values())

        # Select best source
        best_source = max(
            source_scores,
            key=source_scores.get,  # type: ignore[arg-type]
        )
        best_score = source_scores[best_source]

        # Compute overall quality prediction
        quality_score = self._compute_quality_score(features, best_score)

        # Confidence based on feature completeness
        confidence = self._compute_confidence(features)

        # Estimate processing time
        latency = self.SOURCE_LATENCY.get(best_source, 10.0)
        if features.duration_seconds > 0:
            duration_factor = min(features.duration_seconds / 600.0, 3.0)
            latency *= max(1.0, duration_factor)

        reasoning = self._build_reasoning(features, best_source, quality_score)

        elapsed = time.monotonic() - start_time
        logger.debug(
            "Quality prediction completed in %.3fs: score=%.2f source=%s",
            elapsed,
            quality_score,
            best_source,
        )

        return QualityPrediction(
            quality_score=round(quality_score, 4),
            recommended_source=best_source,
            confidence=round(confidence, 4),
            processing_estimate_seconds=round(latency, 2),
            feature_importances=importances,
            reasoning=reasoning,
        )

    def _score_source(
        self,
        source: TranscriptSource,
        features: VideoFeatures,
    ) -> tuple[float, dict[str, float]]:
        """Score a specific source for the given video features."""

        base = self.SOURCE_PRIORS[source] + self._source_adjustments.get(
            source.value,
            0.0,
        )
        weights: dict[str, float] = {}

        # --- Caption availability ---
        if source == TranscriptSource.YOUTUBE_API:
            if features.has_captions:
                weights["captions"] = 0.15
            else:
                weights["captions"] = -0.40  # API will fail without captions

        # --- Language tier ---
        if features.language in self.TIER1_LANGUAGES:
            weights["language"] = 0.05
        elif features.language in self.TIER2_LANGUAGES:
            weights["language"] = 0.0
        else:
            weights["language"] = -0.10
            if source == TranscriptSource.YOUTUBE_API:
                # API rarely has rare language captions
                weights["language"] = -0.20

        # --- Duration impact ---
        if features.duration_seconds > 3600:  # >1 hour
            if source == TranscriptSource.GEMINI_VIDEO:
                weights["duration"] = -0.15  # Gemini URL has limits
            elif source == TranscriptSource.GEMINI_FILE:
                weights["duration"] = -0.10  # File upload is expensive
            elif source == TranscriptSource.SPEECH_TO_TEXT:
                weights["duration"] = -0.05  # STT handles long audio OK
        elif features.is_short:
            weights["duration"] = 0.05  # Short videos are easy for all sources

        # --- Live/stream content ---
        if features.is_live:
            if source == TranscriptSource.YOUTUBE_API:
                weights["live"] = -0.30  # Live transcripts are messy
            elif source == TranscriptSource.GEMINI_VIDEO:
                weights["live"] = -0.15
            else:
                weights["live"] = -0.05

        # --- Channel quality signal ---
        if features.subscriber_count > 100_000:
            # Big channels have better captions
            weights["channel_quality"] = 0.05
        elif (
            features.subscriber_count > 0
            and features.subscriber_count < 1_000
        ):
            weights["channel_quality"] = -0.03

        final_score = max(0.0, min(1.0, base + sum(weights.values())))
        return final_score, weights

    def _compute_quality_score(
        self,
        features: VideoFeatures,
        best_source_score: float,
    ) -> float:
        """Compute overall expected quality of the transcription result."""

        score = best_source_score

        # Boost for English content (most models perform best)
        if features.language == "en":
            score = min(1.0, score + 0.03)

        # Penalty for very long content (more room for errors)
        if features.duration_seconds > 7200:
            score *= 0.92

        # Boost for videos with descriptions (more context)
        if features.description_length > 200:
            score = min(1.0, score + 0.02)

        return max(0.0, min(1.0, score))

    def _compute_confidence(self, features: VideoFeatures) -> float:
        """Confidence in prediction based on features."""

        completeness = 0.0
        total_features = 6

        if features.duration_seconds > 0:
            completeness += 1
        if features.language != "unknown":
            completeness += 1
        if features.subscriber_count > 0:
            completeness += 1
        if features.view_count > 0:
            completeness += 1
        if features.category != "unknown":
            completeness += 1
        if features.title_length > 0:
            completeness += 1

        base_confidence = completeness / total_features

        # Model maturity factor
        if self._weights is not None:
            maturity = min(1.0, self._training_samples / 1000.0)
        else:
            maturity = 0.5  # Heuristic mode = medium confidence

        return base_confidence * 0.6 + maturity * 0.4

    def _build_reasoning(
        self,
        features: VideoFeatures,
        best_source: str,
        quality_score: float,
    ) -> str:
        """Human-readable explanation of the prediction."""

        reasons: list[str] = []

        yt_api = TranscriptSource.YOUTUBE_API
        if features.has_captions and best_source == yt_api:
            reasons.append(
                "Closed captions available "
                "— YouTube API recommended"
            )
        elif not features.has_captions:
            reasons.append(
                "No closed captions "
                "— fallback to AI extraction"
            )

        if features.language not in self.TIER1_LANGUAGES:
            reasons.append(
                f"Language '{features.language}' is not "
                "Tier 1 — lower accuracy expected"
            )

        if features.duration_seconds > 3600:
            mins = features.duration_seconds / 60
            reasons.append(
                f"Long video ({mins:.0f} min) "
                "— processing time increased"
            )

        if features.is_live:
            reasons.append(
                "Live/stream content "
                "— transcript quality may be lower"
            )

        if quality_score >= 0.85:
            reasons.append("High quality prediction — proceed with confidence")
        elif quality_score >= 0.65:
            reasons.append(
                "Moderate quality "
                "— consider verification after extraction"
            )
        else:
            reasons.append(
                "Low quality prediction "
                "— manual review recommended"
            )

        if reasons:
            return "; ".join(reasons)
        return "Standard processing expected"

    def record_outcome(
        self,
        features: VideoFeatures,
        actual_source: str,
        actual_quality: float,
        success: bool,
    ) -> None:
        """Record an actual pipeline outcome for continuous learning.

        This is called after transcript extraction completes, feeding the
        actual results back into the model for future predictions.
        """

        self._training_samples += 1
        base_prior = self.SOURCE_PRIORS.get(actual_source, 0.5)
        target_quality = max(
            0.0,
            min(1.0, actual_quality if success else actual_quality * 0.5),
        )
        learning_rate = min(0.25, 1.0 / max(self._training_samples, 1) ** 0.5)
        current_adjustment = self._source_adjustments.get(actual_source, 0.0)
        updated_adjustment = current_adjustment + learning_rate * (
            target_quality - (base_prior + current_adjustment)
        )
        self._source_adjustments[actual_source] = max(
            -self.MAX_SOURCE_ADJUSTMENT,
            min(self.MAX_SOURCE_ADJUSTMENT, updated_adjustment),
        )
        self._weights = dict(self._source_adjustments)
        self._version = "1.1.0-online"
        logger.info(
            "Training sample %d recorded: source=%s quality=%.2f success=%s adjustment=%.4f",
            self._training_samples,
            actual_source,
            actual_quality,
            success,
            self._source_adjustments.get(actual_source, 0.0),
        )

    @property
    def model_info(self) -> dict[str, Any]:
        """Return model metadata for monitoring."""

        return {
            "name": "TranscriptQualityScorer",
            "version": self._version,
            "training_samples": self._training_samples,
            "mode": "learned" if self._weights else "heuristic",
            "source_priors": dict(self.SOURCE_PRIORS),
            "source_adjustments": dict(self._source_adjustments),
        }
