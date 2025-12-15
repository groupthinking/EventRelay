#!/usr/bin/env python3
"""
Comprehensive Cloud AI Integration Demonstration

This script demonstrates all the key features of the cloud AI integration:
- Multi-provider analysis
- Fallback mechanisms
- Batch processing
- Configuration management
- API integration
- Error handling
- Performance monitoring
"""

import asyncio
import logging
import sys
from pathlib import Path
from datetime import datetime
import json
from typing import List, Dict, Any

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from youtube_extension.integrations.cloud_ai import (
    CloudAIIntegrator,
    AnalysisType,
    CloudAIProvider,
    VideoAnalysisResult,
    CloudAIError
)
from youtube_extension.integrations.cloud_ai.config import CloudAIConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s'
)
logger = logging.getLogger(__name__)


class CloudAIDemo:
    """Comprehensive demonstration of cloud AI capabilities."""
    
    def __init__(self):
        self.demo_videos = [
            "https://youtube.com/watch?v=demo1",
            "https://youtube.com/watch?v=demo2",
            "https://youtube.com/watch?v=demo3"
        ]
        
        self.analysis_types = [
            AnalysisType.LABEL_DETECTION,
            AnalysisType.OBJECT_TRACKING,
            AnalysisType.OCR,
            AnalysisType.SCENE_ANALYSIS
        ]
        
        # Demo configuration (only Apple FastVLM enabled for testing)
        self.config = {
            "google_cloud": {
                "enabled": False,  # Would need real credentials
                "project_id": "demo-project"
            },
            "aws_rekognition": {
                "enabled": False,  # Would need real credentials
                "aws_access_key_id": "demo-key",
                "aws_secret_access_key": "demo-secret",
                "region": "us-west-2"
            },
            "azure_vision": {
                "enabled": False,  # Would need real credentials
                "subscription_key": "demo-key",
                "endpoint": "https://demo.api.cognitive.microsoft.com/"
            },
            "apple_fastvlm": {
                "enabled": True,
                "model_path": "/tmp/demo_model"
            }
        }
    
    async def run_comprehensive_demo(self):
        """Run the complete demonstration."""
        
        print("🎬 YouTube Extension - Cloud AI Integration Demo")
        print("=" * 60)
        
        await self._demo_1_configuration_management()
        await self._demo_2_provider_status()
        await self._demo_3_single_video_analysis()
        await self._demo_4_multi_provider_comparison()
        await self._demo_5_batch_processing()
        await self._demo_6_error_handling()
        await self._demo_7_performance_monitoring()
        await self._demo_8_integration_showcase()
        
        print("\n🎉 Demo Complete!")
        print("=" * 60)
    
    async def _demo_1_configuration_management(self):
        """Demonstrate configuration management capabilities."""
        
        print("\n📋 Demo 1: Configuration Management")
        print("-" * 40)
        
        # Create config from dictionary
        config = CloudAIConfig(self.config)
        
        # Check dependencies
        availability = config.check_dependencies()
        print(f"Provider availability: {availability}")
        
        # Validate configurations
        validation_results = config.validate_all()
        for provider, errors in validation_results.items():
            if errors:
                print(f"❌ {provider}: {errors}")
            else:
                print(f"✅ {provider}: Valid configuration")
        
        # Show enabled providers
        enabled = config.get_enabled_providers()
        print(f"Enabled and ready providers: {enabled}")
    
    async def _demo_2_provider_status(self):
        """Demonstrate provider status checking."""
        
        print("\n🏥 Demo 2: Provider Health Status")
        print("-" * 40)
        
        async with CloudAIIntegrator(self.config) as ai:
            status = await ai.get_provider_status()
            
            for provider, provider_status in status.items():
                if provider_status["available"]:
                    health = provider_status["status"]["status"]
                    response_time = provider_status["status"]["response_time"]
                    print(f"✅ {provider}: {health} ({response_time:.3f}s)")
                else:
                    print(f"❌ {provider}: {provider_status.get('error', 'Unavailable')}")
    
    async def _demo_3_single_video_analysis(self):
        """Demonstrate single video analysis."""
        
        print("\n🎥 Demo 3: Single Video Analysis")
        print("-" * 40)
        
        video_url = self.demo_videos[0]
        
        async with CloudAIIntegrator(self.config) as ai:
            print(f"Analyzing: {video_url}")
            
            result = await ai.analyze_video(
                video_url=video_url,
                analysis_types=self.analysis_types,
                preferred_provider=CloudAIProvider.APPLE_FASTVLM,
                use_fallback=True
            )
            
            self._print_analysis_summary(result)
    
    async def _demo_4_multi_provider_comparison(self):
        """Demonstrate multi-provider analysis."""
        
        print("\n🔄 Demo 4: Multi-Provider Comparison")
        print("-" * 40)
        
        # For demo, we only have Apple FastVLM available
        # In production, this would show results from multiple providers
        
        video_url = self.demo_videos[1]
        
        async with CloudAIIntegrator(self.config) as ai:
            print(f"Multi-provider analysis: {video_url}")
            
            results = await ai.multi_provider_analysis(
                video_url=video_url,
                analysis_types=[AnalysisType.LABEL_DETECTION]
            )
            
            print(f"Received results from {len(results)} provider(s):")
            for result in results:
                print(f"\n📊 {result.provider.value}:")
                print(f"   Labels: {len(result.labels)}")
                print(f"   Objects: {len(result.objects)}")
                print(f"   Processing time: {result.processing_time:.2f}s")
            
            # Demonstrate result aggregation
            if len(results) > 1:
                aggregated = ai.aggregate_results(results)
                print(f"\n🔗 Aggregated results:")
                print(f"   Total labels: {len(aggregated.labels)}")
                print(f"   Total objects: {len(aggregated.objects)}")
    
    async def _demo_5_batch_processing(self):
        """Demonstrate batch video processing."""
        
        print("\n📦 Demo 5: Batch Processing")
        print("-" * 40)
        
        async with CloudAIIntegrator(self.config) as ai:
            print(f"Processing {len(self.demo_videos)} videos in batch...")
            
            # Note: batch_analyze method would need to be implemented
            # For demo, we'll process sequentially
            results = []
            
            for i, video_url in enumerate(self.demo_videos):
                try:
                    print(f"  Processing video {i+1}/{len(self.demo_videos)}")
                    
                    result = await ai.analyze_video(
                        video_url=video_url,
                        analysis_types=[AnalysisType.LABEL_DETECTION],
                        use_fallback=True
                    )
                    
                    results.append(result)
                    print(f"  ✅ Completed: {len(result.labels)} labels detected")
                    
                except Exception as e:
                    print(f"  ❌ Failed: {e}")
                    continue
            
            # Generate batch summary
            self._print_batch_summary(results)
    
    async def _demo_6_error_handling(self):
        """Demonstrate error handling and fallback mechanisms."""
        
        print("\n⚠️  Demo 6: Error Handling & Fallback")
        print("-" * 40)
        
        # Create config with invalid providers to trigger errors
        error_config = {
            "google_cloud": {
                "enabled": True,
                "project_id": "invalid-project"
            },
            "aws_rekognition": {
                "enabled": True,
                "aws_access_key_id": "invalid",
                "aws_secret_access_key": "invalid",
                "region": "invalid-region"
            },
            "apple_fastvlm": {
                "enabled": True,
                "model_path": "/tmp/demo_model"  # This will work as fallback
            }
        }
        
        video_url = self.demo_videos[0]
        
        async with CloudAIIntegrator(error_config) as ai:
            print("Attempting analysis with invalid providers (will fallback)...")
            
            try:
                result = await ai.analyze_video(
                    video_url=video_url,
                    analysis_types=[AnalysisType.LABEL_DETECTION],
                    preferred_provider=CloudAIProvider.GOOGLE_CLOUD,  # This will fail
                    use_fallback=True  # Will fallback to Apple FastVLM
                )
                
                print(f"✅ Success with fallback provider: {result.provider.value}")
                print(f"   Processing time: {result.processing_time:.2f}s")
                
            except CloudAIError as e:
                print(f"❌ All providers failed: {e}")
    
    async def _demo_7_performance_monitoring(self):
        """Demonstrate performance monitoring capabilities."""
        
        print("\n📈 Demo 7: Performance Monitoring")
        print("-" * 40)
        
        video_url = self.demo_videos[0]
        analysis_runs = []
        
        async with CloudAIIntegrator(self.config) as ai:
            print("Running multiple analyses for performance measurement...")
            
            for run in range(3):
                start_time = datetime.utcnow()
                
                try:
                    result = await ai.analyze_video(
                        video_url=video_url,
                        analysis_types=[AnalysisType.LABEL_DETECTION],
                        use_fallback=True
                    )
                    
                    end_time = datetime.utcnow()
                    total_time = (end_time - start_time).total_seconds()
                    
                    analysis_runs.append({
                        "run": run + 1,
                        "total_time": total_time,
                        "processing_time": result.processing_time,
                        "provider": result.provider.value,
                        "labels_count": len(result.labels),
                        "success": True
                    })
                    
                    print(f"  Run {run + 1}: {total_time:.2f}s total, {result.processing_time:.2f}s processing")
                    
                except Exception as e:
                    analysis_runs.append({
                        "run": run + 1,
                        "error": str(e),
                        "success": False
                    })
                    print(f"  Run {run + 1}: Failed - {e}")
        
        # Performance summary
        successful_runs = [r for r in analysis_runs if r["success"]]
        if successful_runs:
            avg_total = sum(r["total_time"] for r in successful_runs) / len(successful_runs)
            avg_processing = sum(r["processing_time"] for r in successful_runs) / len(successful_runs)
            
            print(f"\n📊 Performance Summary:")
            print(f"   Successful runs: {len(successful_runs)}/{len(analysis_runs)}")
            print(f"   Average total time: {avg_total:.2f}s")
            print(f"   Average processing time: {avg_processing:.2f}s")
    
    async def _demo_8_integration_showcase(self):
        """Showcase integration with existing YouTube Extension features."""
        
        print("\n🔗 Demo 8: YouTube Extension Integration")
        print("-" * 40)
        
        # Simulate YouTube video metadata
        youtube_video = {
            "id": "demoVideo123",
            "title": "Sample Technical Video",
            "url": "https://youtube.com/watch?v=demoVideo123",
            "duration": 300,  # 5 minutes
            "description": "A sample technical video for AI analysis"
        }
        
        print(f"Processing YouTube video: {youtube_video['title']}")
        
        async with CloudAIIntegrator(self.config) as ai:
            # Analyze video with AI
            ai_result = await ai.analyze_video(
                video_url=youtube_video["url"],
                analysis_types=[
                    AnalysisType.LABEL_DETECTION,
                    AnalysisType.OBJECT_TRACKING,
                    AnalysisType.OCR
                ]
            )
            
            # Enhanced video metadata with AI insights
            enhanced_video = {
                **youtube_video,
                "ai_enhanced": True,
                "ai_analysis": {
                    "provider": ai_result.provider.value,
                    "processing_time": ai_result.processing_time,
                    "confidence_score": self._calculate_confidence_score(ai_result),
                    "detected_topics": [label.label for label in ai_result.labels[:10]],
                    "detected_objects": [obj.label for obj in ai_result.objects[:5]],
                    "text_content": [text.label for text in ai_result.text_detections[:3]],
                    "analysis_timestamp": datetime.utcnow().isoformat(),
                    "suitable_for_indexing": len(ai_result.labels) > 3,
                    "content_complexity": self._assess_complexity(ai_result)
                }
            }
            
            print("✅ Video enhanced with AI analysis:")
            print(f"   🏷️  Topics: {', '.join(enhanced_video['ai_analysis']['detected_topics'][:3])}...")
            print(f"   🎯 Objects: {', '.join(enhanced_video['ai_analysis']['detected_objects'][:3])}...")
            print(f"   📊 Confidence: {enhanced_video['ai_analysis']['confidence_score']:.2f}")
            print(f"   🧠 Complexity: {enhanced_video['ai_analysis']['content_complexity']}")
            print(f"   📚 Indexing ready: {enhanced_video['ai_analysis']['suitable_for_indexing']}")
            
            # Show how this integrates with existing video processing pipeline
            print(f"\n🔄 Integration with existing pipeline:")
            print(f"   • Video metadata enriched with AI insights")
            print(f"   • Automatic tagging from detected labels")
            print(f"   • Content classification for recommendation engine")
            print(f"   • OCR text extraction for search indexing")
            print(f"   • Quality assessment for content curation")
    
    def _print_analysis_summary(self, result: VideoAnalysisResult):
        """Print a summary of analysis results."""
        
        print(f"\n📊 Analysis Results:")
        print(f"   Provider: {result.provider.value}")
        print(f"   Processing time: {result.processing_time:.2f}s")
        print(f"   Analysis types: {[t.value for t in result.analysis_types]}")
        
        if result.labels:
            print(f"   🏷️  Labels ({len(result.labels)}):")
            for label in result.labels[:5]:
                print(f"     • {label.label} ({label.confidence:.2f})")
        
        if result.objects:
            print(f"   🎯 Objects ({len(result.objects)}):")
            for obj in result.objects[:3]:
                timestamp_info = f" at {obj.timestamp:.1f}s" if obj.timestamp else ""
                print(f"     • {obj.label} ({obj.confidence:.2f}){timestamp_info}")
        
        if result.text_detections:
            print(f"   📝 Text ({len(result.text_detections)}):")
            for text in result.text_detections[:3]:
                print(f"     • '{text.label}' ({text.confidence:.2f})")
    
    def _print_batch_summary(self, results: List[VideoAnalysisResult]):
        """Print summary of batch processing results."""
        
        if not results:
            print("❌ No successful analyses")
            return
        
        total_labels = sum(len(r.labels) for r in results)
        total_objects = sum(len(r.objects) for r in results)
        avg_processing_time = sum(r.processing_time for r in results) / len(results)
        
        print(f"\n📈 Batch Processing Summary:")
        print(f"   Videos processed: {len(results)}")
        print(f"   Total labels: {total_labels}")
        print(f"   Total objects: {total_objects}")
        print(f"   Average processing time: {avg_processing_time:.2f}s")
        
        # Most common labels across all videos
        all_labels = []
        for result in results:
            all_labels.extend([label.label for label in result.labels])
        
        if all_labels:
            from collections import Counter
            common_labels = Counter(all_labels).most_common(3)
            print(f"   Most common labels: {', '.join([label for label, count in common_labels])}")
    
    def _calculate_confidence_score(self, result: VideoAnalysisResult) -> float:
        """Calculate overall confidence score for the analysis."""
        
        all_confidences = []
        
        # Collect all confidence scores
        all_confidences.extend([label.confidence for label in result.labels])
        all_confidences.extend([obj.confidence for obj in result.objects])
        all_confidences.extend([text.confidence for text in result.text_detections])
        
        if not all_confidences:
            return 0.0
        
        return sum(all_confidences) / len(all_confidences)
    
    def _assess_complexity(self, result: VideoAnalysisResult) -> str:
        """Assess content complexity based on AI analysis."""
        
        total_detections = len(result.labels) + len(result.objects) + len(result.text_detections)
        
        if total_detections < 5:
            return "Simple"
        elif total_detections < 15:
            return "Moderate"
        else:
            return "Complex"


async def main():
    """Run the comprehensive demo."""
    
    try:
        demo = CloudAIDemo()
        await demo.run_comprehensive_demo()
        
    except KeyboardInterrupt:
        print("\n\n⏹️  Demo interrupted by user")
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())