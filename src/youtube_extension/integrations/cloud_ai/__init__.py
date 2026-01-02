"""
Cloud AI Integration Base Module

Provides unified interfaces and base classes for cloud AI/ML integrations.
"""

from .base import (
    AnalysisType,
    BaseCloudAI,
    CloudAIProvider,
    DetectionResult,
    VideoAnalysisResult,
)
from .config import CloudAIConfig
from .exceptions import CloudAIError, ConfigurationError, RateLimitError
from .integrator import CloudAIIntegrator

__all__ = [
    "BaseCloudAI",
    "CloudAIProvider",
    "VideoAnalysisResult",
    "DetectionResult",
    "AnalysisType",
    "CloudAIIntegrator",
    "CloudAIConfig",
    "CloudAIError",
    "RateLimitError",
    "ConfigurationError"
]
