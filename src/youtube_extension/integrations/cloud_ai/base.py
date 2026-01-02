"""
Base Cloud AI Integration Classes

Defines common interfaces and data structures for all cloud AI providers.
"""

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Optional


class CloudAIProvider(Enum):
    """Supported cloud AI providers."""
    GOOGLE_CLOUD = "google_cloud"
    AWS_REKOGNITION = "aws_rekognition"
    AZURE_VISION = "azure_vision"


class AnalysisType(Enum):
    """Types of video/image analysis available."""
    OBJECT_TRACKING = "object_tracking"
    OCR = "ocr"
    LABEL_DETECTION = "label_detection"
    LOGO_RECOGNITION = "logo_recognition"
    SHOT_DETECTION = "shot_detection"
    FACE_DETECTION = "face_detection"
    TEXT_DETECTION = "text_detection"
    CONTENT_MODERATION = "content_moderation"
    SCENE_ANALYSIS = "scene_analysis"


@dataclass
class DetectionResult:
    """Individual detection result with confidence and metadata."""
    label: str
    confidence: float
    bounding_box: Optional[dict[str, float]] = None  # {x, y, width, height}
    timestamp: Optional[float] = None  # For video analysis
    metadata: Optional[dict[str, Any]] = None


@dataclass
class VideoAnalysisResult:
    """Complete video analysis result from a cloud AI provider."""
    provider: CloudAIProvider
    video_id: str
    analysis_types: list[AnalysisType]

    # Core detection results
    objects: list[DetectionResult]
    labels: list[DetectionResult]
    text_detections: list[DetectionResult]
    faces: list[DetectionResult]
    logos: list[DetectionResult]

    # Video-specific results
    shots: list[dict[str, float]]  # [{start_time, end_time}]
    scenes: list[dict[str, Any]]

    # Analysis metadata
    processing_time: float
    cost_estimate: Optional[float] = None
    timestamp: datetime = None

    # Raw provider response for debugging
    raw_response: Optional[dict[str, Any]] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()


class BaseCloudAI(ABC):
    """Base class for all cloud AI provider integrations."""

    def __init__(self, config: dict[str, Any]):
        self.config = config
        self.provider = None  # Set in subclasses
        self._client = None

    async def __aenter__(self):
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.cleanup()

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the cloud AI client and validate configuration."""
        pass

    @abstractmethod
    async def cleanup(self) -> None:
        """Cleanup resources and close connections."""
        pass

    @abstractmethod
    async def analyze_video(self, video_url: str,
                          analysis_types: list[AnalysisType]) -> VideoAnalysisResult:
        """Analyze video using specified analysis types."""
        pass

    @abstractmethod
    async def analyze_image(self, image_url: str,
                          analysis_types: list[AnalysisType]) -> VideoAnalysisResult:
        """Analyze single image using specified analysis types."""
        pass

    @abstractmethod
    def get_supported_analysis_types(self) -> list[AnalysisType]:
        """Get list of analysis types supported by this provider."""
        pass

    @abstractmethod
    async def get_service_status(self) -> dict[str, Any]:
        """Check service health and availability."""
        pass

    async def batch_analyze(self, video_urls: list[str],
                          analysis_types: list[AnalysisType]) -> list[VideoAnalysisResult]:
        """Analyze multiple videos in batch with rate limiting."""
        results = []

        # Simple sequential processing with rate limiting
        # Subclasses can override for more sophisticated batch processing
        for url in video_urls:
            try:
                result = await self.analyze_video(url, analysis_types)
                results.append(result)

                # Basic rate limiting - can be customized per provider
                await asyncio.sleep(0.1)

            except Exception as e:
                # Log error but continue with other videos
                import logging
                logging.error(f"Failed to analyze {url}: {str(e)}")
                continue

        return results

    def estimate_cost(self, video_duration: float,
                     analysis_types: list[AnalysisType]) -> float:
        """Estimate processing cost for given video and analysis types."""
        # Default implementation - override in subclasses with provider-specific pricing
        base_cost = 0.01  # $0.01 per minute base
        type_multiplier = len(analysis_types) * 0.5
        return (video_duration / 60) * base_cost * type_multiplier
