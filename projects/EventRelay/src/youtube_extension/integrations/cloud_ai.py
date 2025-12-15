"""
Cloud AI Integration - Main Module

Unified interface for all cloud AI/ML video processing providers.
This module provides the main entry point for integrating with:
- Google Cloud Video Intelligence & Vision API
- Amazon Rekognition  
- Microsoft Azure AI Vision
- Apple FastVLM

Usage:
    from youtube_extension.integrations.cloud_ai import CloudAIIntegrator
    
    config = {
        "google_cloud": {
            "enabled": True,
            "project_id": "your-project",
            "location_id": "us-central1"
        },
        "aws_rekognition": {
            "enabled": True, 
            "aws_access_key_id": "your-key",
            "aws_secret_access_key": "your-secret",
            "region": "us-west-2"
        }
    }
    
    async with CloudAIIntegrator(config) as ai:
        result = await ai.analyze_video(
            "https://youtube.com/watch?v=example",
            [AnalysisType.OBJECT_TRACKING, AnalysisType.OCR]
        )
"""

from typing import Dict, Any, List, Optional

from .cloud_ai.integrator import CloudAIIntegrator
from .cloud_ai.base import CloudAIProvider, AnalysisType, VideoAnalysisResult, DetectionResult
from .cloud_ai.exceptions import (
    CloudAIError, 
    RateLimitError, 
    ConfigurationError,
    ServiceUnavailableError,
    AuthenticationError,
    QuotaExceededError
)

__all__ = [
    # Main integrator
    "CloudAIIntegrator",
    
    # Core types
    "CloudAIProvider",
    "AnalysisType", 
    "VideoAnalysisResult",
    "DetectionResult",
    
    # Exceptions
    "CloudAIError",
    "RateLimitError",
    "ConfigurationError", 
    "ServiceUnavailableError",
    "AuthenticationError",
    "QuotaExceededError"
]


def get_available_providers() -> List[str]:
    """Get list of available cloud AI providers based on installed dependencies."""
    available = []
    
    # Check Google Cloud
    try:
        import google.cloud.videointelligence
        import google.cloud.vision
        available.append("google_cloud")
    except ImportError:
        pass
    
    # Check AWS
    try:
        import boto3
        available.append("aws_rekognition")
    except ImportError:
        pass
    
    # Check Azure
    try:
        import azure.cognitiveservices.vision.computervision
        available.append("azure_vision")
    except ImportError:
        pass
    
    return available


def create_default_config() -> Dict[str, Any]:
    """Create a default configuration template for cloud AI services."""
    return {
        "google_cloud": {
            "enabled": False,
            "project_id": "your-google-cloud-project",
            "location_id": "us-central1",
            "timeout": 300
        },
        "aws_rekognition": {
            "enabled": False,
            "aws_access_key_id": "your-aws-access-key",
            "aws_secret_access_key": "your-aws-secret-key", 
            "region": "us-west-2",
            "s3_bucket": "your-rekognition-bucket",
            "max_wait_time": 600
        },
        "azure_vision": {
            "enabled": False,
            "subscription_key": "your-azure-subscription-key",
            "endpoint": "https://your-region.api.cognitive.microsoft.com/"
        }
    }


async def quick_analyze(video_url: str, 
                       analysis_types: Optional[List[AnalysisType]] = None,
                       provider: Optional[CloudAIProvider] = None) -> VideoAnalysisResult:
    """
    Quick analysis function with sensible defaults.
    
    Uses environment variables for configuration and falls back to available providers.
    """
    import os
    
    if analysis_types is None:
        analysis_types = [
            AnalysisType.LABEL_DETECTION,
            AnalysisType.OBJECT_TRACKING,
            AnalysisType.TEXT_DETECTION
        ]
    
    # Create config from environment variables
    config = {
        "google_cloud": {
            "enabled": bool(os.getenv("GOOGLE_CLOUD_PROJECT")),
            "project_id": os.getenv("GOOGLE_CLOUD_PROJECT"),
            "location_id": os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
        },
        "aws_rekognition": {
            "enabled": bool(os.getenv("AWS_ACCESS_KEY_ID")),
            "aws_access_key_id": os.getenv("AWS_ACCESS_KEY_ID"),
            "aws_secret_access_key": os.getenv("AWS_SECRET_ACCESS_KEY"),
            "region": os.getenv("AWS_DEFAULT_REGION", "us-west-2")
        },
        "azure_vision": {
            "enabled": bool(os.getenv("AZURE_COGNITIVE_SERVICES_KEY")),
            "subscription_key": os.getenv("AZURE_COGNITIVE_SERVICES_KEY"),
            "endpoint": os.getenv("AZURE_COGNITIVE_SERVICES_ENDPOINT")
        }
    }
    
    async with CloudAIIntegrator(config) as ai:
        return await ai.analyze_video(
            video_url, 
            analysis_types,
            preferred_provider=provider
        )
