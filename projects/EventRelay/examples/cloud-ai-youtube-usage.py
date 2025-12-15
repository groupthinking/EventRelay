#!/usr/bin/env python3
"""
Basic Cloud AI Integration Example

This example demonstrates how to use the unified cloud AI integration
to analyze YouTube videos with multiple providers.
"""

import asyncio
import logging
import os
from typing import List

# Import the cloud AI integration
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from youtube_extension.integrations.cloud_ai import (
    CloudAIIntegrator,
    AnalysisType, 
    CloudAIProvider,
    VideoAnalysisResult
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def basic_analysis_example():
    """Basic example using a single provider with fallback."""
    
    # Configuration for cloud AI providers
    config = {
        "google_cloud": {
            "enabled": True,
            "project_id": "your-google-project",
            "location_id": "us-central1"
        },
        "aws_rekognition": {
            "enabled": True,
            "aws_access_key_id": "your-aws-key",
            "aws_secret_access_key": "your-aws-secret",
            "region": "us-west-2"
        },
        "azure_vision": {
            "enabled": True,
            "subscription_key": "your-azure-key",
            "endpoint": "https://your-region.api.cognitive.microsoft.com/"
        },
        "apple_fastvlm": {
            "enabled": True,
            "model_path": "/path/to/fastvlm/model"
        }
    }
    
    # Example YouTube video URL (replace with actual video)
    video_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    
    # Analysis types to perform
    analysis_types = [
        AnalysisType.OBJECT_TRACKING,
        AnalysisType.LABEL_DETECTION,
        AnalysisType.OCR,
        AnalysisType.TEXT_DETECTION
    ]
    
    try:
        # Initialize the cloud AI integrator
        async with CloudAIIntegrator(config) as ai:
            logger.info("Cloud AI integrator initialized")
            
            # Check provider status
            status = await ai.get_provider_status()
            logger.info(f"Provider status: {status}")
            
            # Analyze the video (with automatic fallback)
            logger.info(f"Analyzing video: {video_url}")
            result = await ai.analyze_video(
                video_url=video_url,
                analysis_types=analysis_types,
                preferred_provider=CloudAIProvider.GOOGLE_CLOUD,
                use_fallback=True
            )
            
            # Print results
            print_analysis_results(result)
            
    except Exception as e:
        logger.error(f"Analysis failed: {e}")


async def multi_provider_comparison():
    """Example using multiple providers for comparison."""
    
    config = {
        "google_cloud": {"enabled": False},  # Disabled for demo
        "aws_rekognition": {"enabled": False},  # Disabled for demo
        "azure_vision": {"enabled": False},  # Disabled for demo
        "apple_fastvlm": {"enabled": True, "model_path": "/tmp/mock_model"}
    }
    
    video_url = "https://www.youtube.com/watch?v=example"
    analysis_types = [AnalysisType.LABEL_DETECTION, AnalysisType.OBJECT_TRACKING]
    
    try:
        async with CloudAIIntegrator(config) as ai:
            # Get results from multiple providers
            results = await ai.multi_provider_analysis(video_url, analysis_types)
            
            logger.info(f"Received results from {len(results)} providers")
            
            for result in results:
                print(f"\n--- Results from {result.provider.value} ---")
                print_analysis_results(result)
            
            # Aggregate results if multiple providers returned data
            if len(results) > 1:
                aggregated = ai.aggregate_results(results)
                print("\n--- Aggregated Results ---")
                print_analysis_results(aggregated)
                
    except Exception as e:
        logger.error(f"Multi-provider analysis failed: {e}")


def print_analysis_results(result: VideoAnalysisResult):
    """Helper function to print analysis results in a readable format."""
    
    print(f"Provider: {result.provider.value}")
    print(f"Video ID: {result.video_id}")
    print(f"Processing Time: {result.processing_time:.2f}s")
    print(f"Analysis Types: {[t.value for t in result.analysis_types]}")
    
    if result.objects:
        print(f"\nObjects detected ({len(result.objects)}):")
        for obj in result.objects[:5]:  # Show first 5
            timestamp_info = f" at {obj.timestamp:.1f}s" if obj.timestamp else ""
            print(f"  - {obj.label} (confidence: {obj.confidence:.2f}){timestamp_info}")
    
    if result.labels:
        print(f"\nLabels detected ({len(result.labels)}):")
        for label in result.labels[:5]:  # Show first 5
            print(f"  - {label.label} (confidence: {label.confidence:.2f})")
    
    if result.text_detections:
        print(f"\nText detected ({len(result.text_detections)}):")
        for text in result.text_detections[:3]:  # Show first 3
            timestamp_info = f" at {text.timestamp:.1f}s" if text.timestamp else ""
            print(f"  - '{text.label}' (confidence: {text.confidence:.2f}){timestamp_info}")
    
    if result.faces:
        print(f"\nFaces detected: {len(result.faces)}")
    
    if result.shots:
        print(f"\nShot changes detected: {len(result.shots)}")


async def environment_based_config():
    """Example using configuration from environment variables."""
    
    # Set some example environment variables (in production, set these properly)
    # os.environ["GOOGLE_CLOUD_PROJECT"] = "your-project"
    # os.environ["AWS_ACCESS_KEY_ID"] = "your-key"
    
    try:
        # Use the quick_analyze function with environment-based config
        from youtube_extension.integrations.cloud_ai import quick_analyze
        
        result = await quick_analyze(
            video_url="https://www.youtube.com/watch?v=example",
            analysis_types=[AnalysisType.LABEL_DETECTION],
            provider=CloudAIProvider.APPLE_FASTVLM  # Use Apple as it doesn't need credentials
        )
        
        print("Environment-based analysis completed:")
        print_analysis_results(result)
        
    except Exception as e:
        logger.error(f"Environment-based analysis failed: {e}")


async def main():
    """Run all examples."""
    
    print("=== Cloud AI Integration Examples ===\n")
    
    print("1. Basic Analysis Example")
    print("This would normally analyze with real providers, but will fail without credentials")
    try:
        await basic_analysis_example()
    except Exception as e:
        print(f"Expected failure (no credentials configured): {e}")
    
    print("\n2. Multi-Provider Comparison")
    await multi_provider_comparison()
    
    print("\n3. Environment-Based Configuration") 
    await environment_based_config()
    
    print("\n=== Examples Complete ===")


if __name__ == "__main__":
    asyncio.run(main())