"""
Cloud AI Integration Base Module

Provides unified interfaces and base classes for cloud AI/ML integrations.
"""

from .base import BaseCloudAI, CloudAIProvider, VideoAnalysisResult, DetectionResult, AnalysisType
from .integrator import CloudAIIntegrator
from .exceptions import CloudAIError, RateLimitError, ConfigurationError
from .config import CloudAIConfig

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