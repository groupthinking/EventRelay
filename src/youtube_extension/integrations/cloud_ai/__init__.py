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
from .exceptions import (
    CloudAIError,
    ConfigurationError,
    RateLimitError,
    UnsafeMediaPathError,
)
from .integrator import CloudAIIntegrator
from .media_paths import MEDIA_ROOT_ENV_VAR, get_media_root, resolve_local_media_path

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
    "ConfigurationError",
    "UnsafeMediaPathError",
    "MEDIA_ROOT_ENV_VAR",
    "get_media_root",
    "resolve_local_media_path",
]
