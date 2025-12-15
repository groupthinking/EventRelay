#!/usr/bin/env python3
"""
Basic usage examples for FastVLM + Gemini Hybrid System
"""

import sys
import os

# Ensure the package is available (development mode)
try:
    import youtube_extension
except ImportError:
    # Add parent directory for development
    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)

from fastvlm_gemini_hybrid import HybridVLMProcessor, RoutingEngine, VideoPipeline
from fastvlm_gemini_hybrid.config import HybridConfig, ProcessingMode, TaskType
from PIL import Image
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')


def example_basic_image_processing():
    """Basic image processing example"""
    print("\n=== Basic Image Processing ===")
    
    # Initialize processor
    processor = HybridVLMProcessor()
    
    # Example prompts and routing
    examples = [
        {
            "prompt": "Describe this image in detail",
            "metadata": None,
            "description": "General description - auto routing"
        },
        {
            "prompt": "What technical components are visible in this diagram?",
            "metadata": {"source": "technical_document"},
            "description": "Technical content - routes to FastVLM"
        },
        {
            "prompt": "Analyze the complex relationships and provide detailed reasoning",
            "metadata": None,
            "description": "Complex analysis - routes to Gemini"
        },
        {
            "prompt": "Quick caption for this private company data",
            "metadata": {"privacy_required": True},
            "description": "Privacy-sensitive - forces local processing"
        }
    ]
    
    # Create a sample image (you would use a real image path)
    sample_image = Image.new('RGB', (224, 224), color='blue')
    
    for example in examples:
        print(f"\n{example['description']}")
        print(f"Prompt: {example['prompt']}")
        
        result = processor.process(
            sample_image,
            example['prompt'],
            metadata=example['metadata']
        )
        
        print(f"Routing: {result.get('routing', {}).get('mode')}")
        print(f"Processor used: {result.get('processor')}")
        print(f"Success: {result.get('success')}")
        if result.get('success'):
            print(f"Response preview: {result.get('response', '')[:100]}...")
        print(f"Latency: {result.get('latency', 0):.2f}s")


def example_video_processing():
    """Video processing example"""
    print("\n=== Video Processing ===")
    
    # Initialize pipeline
    pipeline = VideoPipeline()
    
    # Example video path (you would use a real video)
    video_path = "sample_video.mp4"
    
    # Check if video exists (for demo purposes, we'll skip if not)
    if not os.path.exists(video_path):
        print(f"Video {video_path} not found. Skipping video examples.")
        return
    
    # 1. Process video with automatic hybrid routing
    print("\n1. Hybrid video processing:")
    result = pipeline.process_video_hybrid(
        video_path,
        "Describe what's happening in this video"
    )
    print(f"Strategy used: {result.get('strategy')}")
    print(f"Success: {result.get('success')}")
    
    # 2. Stream processing for real-time analysis
    print("\n2. Stream processing (first 3 frames):")
    frame_count = 0
    for frame_result in pipeline.process_video_stream(
        video_path,
        "Describe this frame",
        frame_rate=1,
        mode=ProcessingMode.LOCAL_ONLY
    ):
        print(f"Frame {frame_result['frame_info']['frame_number']}: "
              f"{frame_result.get('response', '')[:50]}...")
        frame_count += 1
        if frame_count >= 3:
            break
    
    # 3. Comprehensive analysis
    print("\n3. Comprehensive video analysis:")
    analysis = pipeline.analyze_video_content(
        video_path,
        analysis_type="content_summary"
    )
    print(f"Analysis complete: {analysis.get('success')}")


def example_batch_processing():
    """Batch processing example"""
    print("\n=== Batch Processing ===")
    
    processor = HybridVLMProcessor()
    
    # Create sample images
    images = [
        Image.new('RGB', (224, 224), color='red'),
        Image.new('RGB', (224, 224), color='green'),
        Image.new('RGB', (224, 224), color='blue')
    ]
    
    # Batch process with same prompt
    print("\n1. Batch with same prompt:")
    results = processor.batch_process(
        images,
        "What color is this image?"
    )
    
    for i, result in enumerate(results):
        print(f"Image {i+1}: {result.get('processor')} - {result.get('success')}")
    
    # Batch process with different prompts
    print("\n2. Batch with different prompts:")
    prompts = [
        "Describe the color",
        "Is this image bright or dark?",
        "What objects are visible?"
    ]
    
    results = processor.batch_process(images, prompts)
    
    for i, result in enumerate(results):
        print(f"Image {i+1}: {result.get('routing', {}).get('mode')}")


def example_parallel_processing():
    """Parallel processing example"""
    print("\n=== Parallel Processing ===")
    
    # Configure for parallel processing
    config = HybridConfig()
    config.default_mode = ProcessingMode.HYBRID_PARALLEL
    
    processor = HybridVLMProcessor(config)
    
    # Process with both models in parallel
    sample_image = Image.new('RGB', (224, 224), color='yellow')
    
    result = processor.process(
        sample_image,
        "Describe this image",
        force_mode=ProcessingMode.HYBRID_PARALLEL
    )
    
    print(f"Parallel processing results:")
    if 'results' in result:
        for model, model_result in result['results'].items():
            print(f"\n{model}:")
            print(f"  Success: {model_result.get('success')}")
            print(f"  Latency: {model_result.get('latency', 0):.2f}s")
            if model_result.get('success'):
                print(f"  Response: {model_result.get('response', '')[:100]}...")
    
    print(f"\nPrimary processor: {result.get('primary_processor')}")


def example_routing_analysis():
    """Analyze routing decisions"""
    print("\n=== Routing Analysis ===")
    
    router = RoutingEngine()
    
    test_prompts = [
        "Show me a real-time caption",
        "Analyze this YouTube video: https://youtube.com/...",
        "What's in this private document?",
        "Provide complex reasoning about the relationships",
        "Quick description please",
        "Summarize this 2-hour video",
        "Find similar images in the database"
    ]
    
    decisions = []
    for prompt in test_prompts:
        decision = router.route(prompt)
        decisions.append(decision)
        print(f"\nPrompt: '{prompt[:50]}...'")
        print(f"  Mode: {decision.mode.value}")
        print(f"  Confidence: {decision.confidence:.2f}")
        print(f"  Reason: {decision.reason}")
        if decision.task_type:
            print(f"  Task type: {decision.task_type.value}")
    
    # Get routing statistics
    stats = router.get_routing_stats(decisions)
    print(f"\n=== Routing Statistics ===")
    print(f"Total decisions: {stats['total_decisions']}")
    print(f"Mode distribution: {stats['mode_distribution']}")
    print(f"Average confidence: {stats['average_confidence']:.2f}")
    print(f"Primary mode: {stats['primary_mode']}")


def example_performance_monitoring():
    """Monitor system performance"""
    print("\n=== Performance Monitoring ===")
    
    processor = HybridVLMProcessor()
    
    # Process several images to generate metrics
    for i in range(5):
        image = Image.new('RGB', (224, 224), color=(i*50, i*50, i*50))
        processor.process(image, f"Test prompt {i}")
    
    # Get metrics
    metrics = processor.get_metrics()
    
    print("\nSystem Metrics:")
    print(f"Total requests: {metrics['total_requests']}")
    print(f"Local requests: {metrics['local_requests']}")
    print(f"Cloud requests: {metrics['cloud_requests']}")
    print(f"Hybrid requests: {metrics['hybrid_requests']}")
    print(f"Cache hits: {metrics['cache_hits']}")
    print(f"Average latency: {metrics.get('average_latency', 0):.2f}s")
    print(f"Cache hit rate: {metrics.get('cache_hit_rate', 0):.2%}")
    
    # Health check
    health = processor.health_check()
    print("\nHealth Check:")
    print(f"Status: {health['status']}")
    print(f"FastVLM available: {health['components']['fastvlm']['available']}")
    print(f"Gemini available: {health['components']['gemini']['available']}")
    print(f"Cache size: {health['components']['cache']['size']}")


if __name__ == "__main__":
    print("FastVLM + Gemini Hybrid System Examples")
    print("=" * 50)
    
    # Run examples
    example_basic_image_processing()
    example_video_processing()
    example_batch_processing()
    example_parallel_processing()
    example_routing_analysis()
    example_performance_monitoring()
    
    print("\n" + "=" * 50)
    print("Examples completed!")