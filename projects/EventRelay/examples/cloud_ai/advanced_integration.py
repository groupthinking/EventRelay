#!/usr/bin/env python3
"""
Advanced Cloud AI Integration Example

Demonstrates advanced features like:
- Configuration management
- Batch processing
- Error handling and retry logic
- Cost estimation
- Performance monitoring
"""

import asyncio
import logging
import json
from typing import List, Dict, Any
from datetime import datetime

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from youtube_extension.integrations.cloud_ai import (
    CloudAIIntegrator,
    AnalysisType,
    CloudAIProvider,
    VideoAnalysisResult,
    ConfigurationError,
    RateLimitError
)
from youtube_extension.integrations.cloud_ai.config import CloudAIConfig

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def configuration_management_example():
    """Demonstrate advanced configuration management."""
    
    print("\n=== Configuration Management ===")
    
    # Create configuration from environment
    config = CloudAIConfig.from_environment()
    
    # Check dependencies
    availability = config.check_dependencies()
    print(f"Provider availability: {availability}")
    
    # Validate all configurations
    validation_results = config.validate_all()
    print(f"Validation results: {validation_results}")
    
    # Get enabled and ready providers
    ready_providers = config.get_enabled_providers()
    print(f"Ready providers: {ready_providers}")
    
    # Save configuration to file for future use
    # config.save_to_file("cloud_ai_config.json")
    
    return config


async def batch_processing_example(config: CloudAIConfig):
    """Demonstrate batch video processing."""
    
    print("\n=== Batch Processing ===")
    
    # List of videos to process (mock URLs for demo)
    video_urls = [
        "https://www.youtube.com/watch?v=video1",
        "https://www.youtube.com/watch?v=video2", 
        "https://www.youtube.com/watch?v=video3",
        "https://www.youtube.com/watch?v=video4",
        "https://www.youtube.com/watch?v=video5"
    ]
    
    analysis_types = [AnalysisType.LABEL_DETECTION, AnalysisType.OBJECT_TRACKING]
    
    # Mock configuration for demo
    demo_config = {
        "apple_fastvlm": {
            "enabled": True,
            "model_path": "/tmp/mock_model"
        }
    }
    
    try:
        async with CloudAIIntegrator(demo_config) as ai:
            print(f"Processing {len(video_urls)} videos...")
            
            # Process videos in batches
            batch_size = 2
            all_results = []
            
            for i in range(0, len(video_urls), batch_size):
                batch = video_urls[i:i+batch_size]
                print(f"Processing batch {i//batch_size + 1}: {batch}")
                
                # Use batch_analyze method (if implemented) or process sequentially
                batch_results = []
                for url in batch:
                    try:
                        result = await ai.analyze_video(url, analysis_types)
                        batch_results.append(result)
                        print(f"  ✓ Processed {url}")
                    except Exception as e:
                        print(f"  ✗ Failed {url}: {e}")
                        continue
                
                all_results.extend(batch_results)
                
                # Add delay between batches to respect rate limits
                if i + batch_size < len(video_urls):
                    await asyncio.sleep(1)
            
            print(f"Batch processing complete. Processed {len(all_results)}/{len(video_urls)} videos")
            
            # Generate summary report
            generate_batch_report(all_results)
            
    except Exception as e:
        logger.error(f"Batch processing failed: {e}")


async def error_handling_example():
    """Demonstrate robust error handling and retry logic."""
    
    print("\n=== Error Handling & Retry Logic ===")
    
    # Configuration with invalid credentials to trigger errors
    error_config = {
        "google_cloud": {
            "enabled": True,
            "project_id": "invalid-project",
        },
        "aws_rekognition": {
            "enabled": True,
            "aws_access_key_id": "invalid",
            "aws_secret_access_key": "invalid",
            "region": "us-west-2"
        },
        "apple_fastvlm": {
            "enabled": True,
            "model_path": "/tmp/mock_model"
        }
    }
    
    video_url = "https://www.youtube.com/watch?v=example"
    analysis_types = [AnalysisType.LABEL_DETECTION]
    
    async with CloudAIIntegrator(error_config) as ai:
        # This will demonstrate fallback from failed providers to working ones
        try:
            result = await ai.analyze_video(
                video_url,
                analysis_types,
                preferred_provider=CloudAIProvider.GOOGLE_CLOUD,  # Will fail
                use_fallback=True  # Will fallback to Apple FastVLM
            )
            print(f"Analysis succeeded with fallback provider: {result.provider.value}")
            
        except Exception as e:
            print(f"All providers failed: {e}")


async def cost_estimation_example():
    """Demonstrate cost estimation for different providers."""
    
    print("\n=== Cost Estimation ===")
    
    # Mock video durations and analysis types
    scenarios = [
        {"duration": 60, "types": [AnalysisType.LABEL_DETECTION]},
        {"duration": 300, "types": [AnalysisType.OBJECT_TRACKING, AnalysisType.OCR]},
        {"duration": 1800, "types": [AnalysisType.LABEL_DETECTION, AnalysisType.FACE_DETECTION, AnalysisType.TEXT_DETECTION]}
    ]
    
    config = {
        "apple_fastvlm": {"enabled": True, "model_path": "/tmp/mock"}
    }
    
    async with CloudAIIntegrator(config) as ai:
        for provider_type, provider in ai.providers.items():
            print(f"\nCost estimates for {provider_type.value}:")
            
            for scenario in scenarios:
                cost = provider.estimate_cost(
                    scenario["duration"], 
                    scenario["types"]
                )
                print(f"  {scenario['duration']}s video with {len(scenario['types'])} analysis types: ${cost:.4f}")


async def performance_monitoring_example():
    """Demonstrate performance monitoring and benchmarking."""
    
    print("\n=== Performance Monitoring ===")
    
    config = {
        "apple_fastvlm": {"enabled": True, "model_path": "/tmp/mock"}
    }
    
    video_url = "https://www.youtube.com/watch?v=example"
    analysis_types = [AnalysisType.LABEL_DETECTION, AnalysisType.OBJECT_TRACKING]
    
    # Run multiple analyses to collect performance data
    performance_data = []
    
    async with CloudAIIntegrator(config) as ai:
        for i in range(3):
            start_time = datetime.utcnow()
            
            try:
                result = await ai.analyze_video(video_url, analysis_types)
                
                performance_data.append({
                    "run": i + 1,
                    "provider": result.provider.value,
                    "processing_time": result.processing_time,
                    "objects_detected": len(result.objects),
                    "labels_detected": len(result.labels),
                    "success": True
                })
                
            except Exception as e:
                performance_data.append({
                    "run": i + 1,
                    "error": str(e),
                    "success": False
                })
    
    # Generate performance report
    print("\nPerformance Report:")
    for data in performance_data:
        if data["success"]:
            print(f"  Run {data['run']}: {data['processing_time']:.2f}s, "
                  f"{data['objects_detected']} objects, {data['labels_detected']} labels")
        else:
            print(f"  Run {data['run']}: FAILED - {data['error']}")


def generate_batch_report(results: List[VideoAnalysisResult]):
    """Generate a comprehensive report from batch processing results."""
    
    print("\n=== Batch Processing Report ===")
    
    if not results:
        print("No results to report")
        return
    
    # Summary statistics
    total_videos = len(results)
    total_objects = sum(len(r.objects) for r in results)
    total_labels = sum(len(r.labels) for r in results)
    total_text = sum(len(r.text_detections) for r in results)
    avg_processing_time = sum(r.processing_time for r in results) / total_videos
    
    print(f"Videos processed: {total_videos}")
    print(f"Total objects detected: {total_objects}")
    print(f"Total labels detected: {total_labels}")
    print(f"Total text detections: {total_text}")
    print(f"Average processing time: {avg_processing_time:.2f}s")
    
    # Most common labels across all videos
    all_labels = []
    for result in results:
        all_labels.extend([label.label for label in result.labels])
    
    if all_labels:
        from collections import Counter
        common_labels = Counter(all_labels).most_common(5)
        print(f"\nMost common labels:")
        for label, count in common_labels:
            print(f"  - {label}: {count} videos")
    
    # Provider performance
    providers = [r.provider.value for r in results]
    from collections import Counter
    provider_usage = Counter(providers)
    print(f"\nProvider usage:")
    for provider, count in provider_usage.items():
        print(f"  - {provider}: {count} videos")


async def real_world_integration_example():
    """Example of how this would integrate with the YouTube Extension."""
    
    print("\n=== Real-World Integration Example ===")
    
    # This demonstrates how the cloud AI integration would be used
    # within the existing YouTube Extension architecture
    
    # Mock video processing pipeline
    youtube_videos = [
        {"id": "dQw4w9WgXcQ", "title": "Sample Video 1", "url": "https://youtube.com/watch?v=dQw4w9WgXcQ"},
        {"id": "example123", "title": "Sample Video 2", "url": "https://youtube.com/watch?v=example123"}
    ]
    
    # Integration configuration
    integration_config = {
        "apple_fastvlm": {
            "enabled": True,
            "model_path": "/tmp/mock_model"
        }
    }
    
    # Process each video through the cloud AI pipeline
    enhanced_videos = []
    
    async with CloudAIIntegrator(integration_config) as ai:
        for video in youtube_videos:
            print(f"\nProcessing: {video['title']}")
            
            try:
                # Analyze video with cloud AI
                ai_result = await ai.analyze_video(
                    video["url"],
                    [AnalysisType.LABEL_DETECTION, AnalysisType.OBJECT_TRACKING, AnalysisType.OCR]
                )
                
                # Enhance video metadata with AI insights
                enhanced_video = {
                    **video,
                    "ai_analysis": {
                        "provider": ai_result.provider.value,
                        "processing_time": ai_result.processing_time,
                        "objects": [{"label": obj.label, "confidence": obj.confidence} 
                                  for obj in ai_result.objects[:10]],
                        "labels": [{"label": lbl.label, "confidence": lbl.confidence}
                                 for lbl in ai_result.labels[:10]],
                        "text_detected": [txt.label for txt in ai_result.text_detections[:5]]
                    }
                }
                
                enhanced_videos.append(enhanced_video)
                print(f"  ✓ Enhanced with {len(ai_result.labels)} labels, {len(ai_result.objects)} objects")
                
            except Exception as e:
                print(f"  ✗ AI analysis failed: {e}")
                enhanced_videos.append(video)  # Add without AI enhancement
    
    # Save enhanced results (in real implementation, would save to database)
    print(f"\nProcessed {len(enhanced_videos)} videos with AI enhancement")
    
    # Example of how to access the enhanced data
    for video in enhanced_videos:
        if "ai_analysis" in video:
            print(f"\n{video['title']} - AI Insights:")
            for label in video["ai_analysis"]["labels"][:3]:
                print(f"  - {label['label']} ({label['confidence']:.2f})")


async def main():
    """Run all advanced examples."""
    
    print("=== Advanced Cloud AI Integration Examples ===")
    
    # 1. Configuration Management
    config = await configuration_management_example()
    
    # 2. Batch Processing
    await batch_processing_example(config)
    
    # 3. Error Handling
    await error_handling_example()
    
    # 4. Cost Estimation
    await cost_estimation_example()
    
    # 5. Performance Monitoring
    await performance_monitoring_example()
    
    # 6. Real-world Integration
    await real_world_integration_example()
    
    print("\n=== Advanced Examples Complete ===")


if __name__ == "__main__":
    asyncio.run(main())