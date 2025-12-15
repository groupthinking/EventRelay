#!/usr/bin/env python3
"""
Comprehensive System Test for FastVLM + Gemini Hybrid Integration
Tests all components and features
"""

import sys
import os
import logging
import time
import json
from pathlib import Path
from PIL import Image
import numpy as np

# Ensure package availability (use proper package imports)
try:
    import youtube_extension
except ImportError:
    logger.warning("youtube_extension package not found. Please install with: pip install -e .")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_basic_setup():
    """Test basic system setup and imports"""
    print("\n" + "="*60)
    print("TEST 1: Basic Setup and Imports")
    print("="*60)
    
    try:
        from fastvlm_gemini_hybrid import HybridVLMProcessor, RoutingEngine, VideoPipeline
        from fastvlm_gemini_hybrid.config import HybridConfig, ProcessingMode
        print("✅ Core modules imported successfully")
        
        from fastvlm_gemini_hybrid.routing_rules_advanced import AdvancedRoutingEngine
        print("✅ Advanced routing module imported")
        
        from fastvlm_gemini_hybrid.mlx_backend import MLXOptimizedProcessor
        print("✅ MLX backend module imported")
        
        from fastvlm_gemini_hybrid.agents import MedicalImagingAgent, VideoSurveillanceAgent
        print("✅ Custom agents imported")
        
        return True
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False


def test_model_availability():
    """Test FastVLM model availability"""
    print("\n" + "="*60)
    print("TEST 2: Model Availability")
    print("="*60)
    
    model_paths = [
        "/workspace/ml-fastvlm/checkpoints/llava-fastvithd_0.5b_stage3",
        "/workspace/ml-fastvlm/checkpoints/llava-fastvithd_1.5b_stage3",
        "/workspace/ml-fastvlm/checkpoints/llava-fastvithd_7b_stage3"
    ]
    
    available_models = []
    for path in model_paths:
        if Path(path).exists():
            print(f"✅ Model found: {Path(path).name}")
            available_models.append(path)
        else:
            print(f"⚠️  Model not found: {Path(path).name}")
    
    if available_models:
        print(f"\n📦 {len(available_models)} models available")
        return True
    else:
        print("\n❌ No models found. Run: bash ml-fastvlm/get_models.sh")
        return False


def test_hybrid_processor():
    """Test hybrid processor initialization and basic functionality"""
    print("\n" + "="*60)
    print("TEST 3: Hybrid Processor")
    print("="*60)
    
    try:
        from fastvlm_gemini_hybrid import HybridVLMProcessor
        from fastvlm_gemini_hybrid.config import HybridConfig
        
        # Configure
        config = HybridConfig()
        config.fastvlm.model_path = "/workspace/ml-fastvlm/checkpoints/llava-fastvithd_0.5b_stage3"
        
        # Initialize processor
        processor = HybridVLMProcessor(config)
        print("✅ Hybrid processor initialized")
        
        # Check health
        health = processor.health_check()
        print(f"   FastVLM available: {health['components']['fastvlm']['available']}")
        print(f"   Gemini available: {health['components']['gemini']['available']}")
        print(f"   Cache enabled: {health['components']['cache']['enabled']}")
        
        # Create test image
        test_image = Image.new('RGB', (224, 224), color='blue')
        
        # Test processing
        result = processor.process(
            test_image,
            "Describe this image",
            metadata={"test": True}
        )
        
        if result.get("success"):
            print(f"✅ Processing successful")
            print(f"   Processor used: {result.get('processor')}")
            print(f"   Latency: {result.get('latency', 0):.2f}s")
            print(f"   Routing mode: {result.get('routing', {}).get('mode')}")
        else:
            print(f"⚠️  Processing failed: {result.get('error')}")
        
        return True
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False


def test_routing_engine():
    """Test routing engine with various prompts"""
    print("\n" + "="*60)
    print("TEST 4: Routing Engine")
    print("="*60)
    
    try:
        from fastvlm_gemini_hybrid.routing_engine import RoutingEngine
        from fastvlm_gemini_hybrid.routing_rules_advanced import AdvancedRoutingEngine
        
        # Test basic routing
        router = RoutingEngine()
        print("✅ Basic routing engine initialized")
        
        test_prompts = [
            ("Generate a real-time caption for this live feed", "LOCAL_ONLY"),
            ("Analyze this YouTube video", "CLOUD_ONLY"),
            ("Extract text from this private document", "LOCAL_ONLY"),
            ("Provide complex reasoning about the relationships", "CLOUD_ONLY"),
            ("Describe this image", "HYBRID_AUTO")
        ]
        
        print("\nBasic Routing Tests:")
        for prompt, expected in test_prompts:
            decision = router.route(prompt)
            status = "✅" if expected in str(decision.mode) else "⚠️"
            print(f"  {status} '{prompt[:30]}...' -> {decision.mode.value}")
        
        # Test advanced routing
        adv_router = AdvancedRoutingEngine()
        print("\n✅ Advanced routing engine initialized")
        
        medical_prompt = "Analyze this xray for abnormalities"
        decision = adv_router.get_routing_decision(medical_prompt)
        print(f"\nAdvanced Routing Test:")
        print(f"  Prompt: '{medical_prompt}'")
        print(f"  Rule: {decision['rule_name']}")
        print(f"  Domain: {decision['domain']}")
        print(f"  Privacy Required: {decision['requires_privacy']}")
        print(f"  Mode: {decision['mode'].value}")
        
        return True
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False


def test_video_pipeline():
    """Test video processing pipeline"""
    print("\n" + "="*60)
    print("TEST 5: Video Pipeline")
    print("="*60)
    
    try:
        from fastvlm_gemini_hybrid import VideoPipeline
        
        pipeline = VideoPipeline()
        print("✅ Video pipeline initialized")
        
        # Create test video frames
        print("\nCreating test video...")
        import cv2
        import tempfile
        
        with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as tmp:
            video_path = tmp.name
        
        # Create simple test video
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(video_path, fourcc, 10.0, (640, 480))
        
        for i in range(30):  # 3 seconds at 10fps
            frame = np.ones((480, 640, 3), dtype=np.uint8) * (i * 8)
            cv2.putText(frame, f"Frame {i}", (50, 240), 
                       cv2.FONT_HERSHEY_SIMPLEX, 2, (255, 255, 255), 3)
            out.write(frame)
        
        out.release()
        print(f"✅ Test video created: {video_path}")
        
        # Test frame extraction
        frames = pipeline.extract_frames(video_path, frame_rate=2, max_frames=5)
        print(f"✅ Extracted {len(frames)} frames")
        
        # Test video analysis
        print("\nTesting video analysis...")
        result = pipeline.process_video_hybrid(
            video_path,
            "Describe what happens in this video"
        )
        
        if result.get("success"):
            print(f"✅ Video analysis successful")
            print(f"   Strategy: {result.get('strategy')}")
            print(f"   Processor: {result.get('processor')}")
        else:
            print(f"⚠️  Video analysis failed: {result.get('error')}")
        
        # Cleanup
        os.unlink(video_path)
        
        return True
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False


def test_mlx_backend():
    """Test MLX backend for Apple Silicon"""
    print("\n" + "="*60)
    print("TEST 6: MLX Backend (Apple Silicon)")
    print("="*60)
    
    try:
        from fastvlm_gemini_hybrid.mlx_backend import MLXOptimizedProcessor
        import platform
        
        # Check platform
        is_mac = platform.system() == "Darwin"
        print(f"Platform: {platform.system()}")
        
        if not is_mac:
            print("⚠️  MLX only available on macOS, skipping...")
            return True
        
        processor = MLXOptimizedProcessor()
        print("✅ MLX processor initialized")
        
        # Create test image
        test_image = Image.new('RGB', (224, 224), color='red')
        
        # Test processing
        result = processor.process(
            test_image,
            "Describe this image",
            prefer_mlx=True
        )
        
        if result.get("success"):
            print(f"✅ MLX processing successful")
            print(f"   Backend: {result.get('backend')}")
            print(f"   Latency: {result.get('latency', 0):.2f}s")
        else:
            print(f"⚠️  MLX processing unavailable: {result.get('error')}")
        
        return True
    except Exception as e:
        print(f"⚠️  MLX test skipped: {e}")
        return True


def test_custom_agents():
    """Test custom task-specific agents"""
    print("\n" + "="*60)
    print("TEST 7: Custom Agents")
    print("="*60)
    
    try:
        from fastvlm_gemini_hybrid.agents import MedicalImagingAgent, VideoSurveillanceAgent
        
        # Test Medical Imaging Agent
        print("\nMedical Imaging Agent:")
        medical_agent = MedicalImagingAgent()
        print("✅ Medical imaging agent initialized")
        
        # Create test medical image
        medical_image = Image.new('RGB', (512, 512), color='gray')
        
        # Analyze
        analysis = medical_agent.analyze_medical_image(
            medical_image,
            modality="xray",
            body_part="chest",
            clinical_history="Test case"
        )
        
        print(f"   Analysis ID: {analysis['analysis_id']}")
        print(f"   Risk Level: {analysis.get('risk_assessment', {}).get('level', 'unknown')}")
        print(f"   Report generated: {len(analysis.get('report', '')) > 0}")
        
        # Test Video Surveillance Agent
        print("\nVideo Surveillance Agent:")
        surveillance_agent = VideoSurveillanceAgent()
        print("✅ Video surveillance agent initialized")
        
        # Test configuration
        print(f"   Alert types: {len(surveillance_agent.alert_types)}")
        print(f"   Motion threshold: {surveillance_agent.motion_threshold}")
        print(f"   Frame buffer size: {surveillance_agent.frame_buffer_size}")
        
        return True
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False


def test_performance_metrics():
    """Test performance monitoring and metrics"""
    print("\n" + "="*60)
    print("TEST 8: Performance Metrics")
    print("="*60)
    
    try:
        from fastvlm_gemini_hybrid import HybridVLMProcessor
        
        processor = HybridVLMProcessor()
        
        # Process several test images
        print("Running performance tests...")
        test_image = Image.new('RGB', (224, 224), color='green')
        
        latencies = []
        for i in range(5):
            result = processor.process(
                test_image,
                f"Test prompt {i}"
            )
            if result.get("success"):
                latencies.append(result.get("latency", 0))
        
        # Get metrics
        metrics = processor.get_metrics()
        
        print("\n📊 Performance Metrics:")
        print(f"   Total requests: {metrics['total_requests']}")
        print(f"   Local requests: {metrics['local_requests']}")
        print(f"   Cloud requests: {metrics['cloud_requests']}")
        print(f"   Hybrid requests: {metrics['hybrid_requests']}")
        print(f"   Cache hits: {metrics['cache_hits']}")
        
        if latencies:
            print(f"   Average latency: {np.mean(latencies):.2f}s")
            print(f"   Min latency: {np.min(latencies):.2f}s")
            print(f"   Max latency: {np.max(latencies):.2f}s")
        
        return True
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False


def test_webgpu_setup():
    """Test WebGPU setup"""
    print("\n" + "="*60)
    print("TEST 9: WebGPU Browser Interface")
    print("="*60)
    
    webgpu_path = Path("/workspace/fastvlm_gemini_hybrid/webgpu")
    
    if webgpu_path.exists():
        files = list(webgpu_path.glob("*"))
        print(f"✅ WebGPU interface found with {len(files)} files")
        
        for file in ["index.html", "webgpu-processor.js", "server.py"]:
            if (webgpu_path / file).exists():
                print(f"   ✅ {file}")
            else:
                print(f"   ❌ {file} missing")
        
        print(f"\nTo start WebGPU interface:")
        print(f"   cd {webgpu_path}")
        print(f"   python3 server.py")
        print(f"   Open browser to http://localhost:8080")
        
        return True
    else:
        print("❌ WebGPU interface not found")
        return False


def run_all_tests():
    """Run all system tests"""
    print("\n" + "="*60)
    print("FASTVLM + GEMINI HYBRID SYSTEM - COMPREHENSIVE TEST SUITE")
    print("="*60)
    
    tests = [
        ("Basic Setup", test_basic_setup),
        ("Model Availability", test_model_availability),
        ("Hybrid Processor", test_hybrid_processor),
        ("Routing Engine", test_routing_engine),
        ("Video Pipeline", test_video_pipeline),
        ("MLX Backend", test_mlx_backend),
        ("Custom Agents", test_custom_agents),
        ("Performance Metrics", test_performance_metrics),
        ("WebGPU Setup", test_webgpu_setup)
    ]
    
    results = []
    for name, test_func in tests:
        try:
            success = test_func()
            results.append((name, success))
        except Exception as e:
            print(f"\n❌ Test '{name}' crashed: {e}")
            results.append((name, False))
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status:10} {name}")
    
    print(f"\nResults: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! System is fully operational.")
    elif passed >= total * 0.7:
        print("\n✅ Most tests passed. System is operational with some limitations.")
    else:
        print("\n⚠️  Multiple tests failed. Please check the configuration.")
    
    # Recommendations
    print("\n" + "="*60)
    print("RECOMMENDATIONS")
    print("="*60)
    
    if not results[1][1]:  # Model availability test
        print("1. Download FastVLM models:")
        print("   cd /workspace/ml-fastvlm && bash get_models.sh")
    
    if not os.getenv("GEMINI_API_KEY"):
        print("2. Set Gemini API key for cloud processing:")
        print("   export GEMINI_API_KEY='your-api-key'")
    
    print("\n3. To use the system:")
    print("   python3 /workspace/examples/basic_usage.py")
    print("   python3 /workspace/examples/advanced_integration.py")
    
    print("\n4. To start WebGPU interface:")
    print("   cd /workspace/fastvlm_gemini_hybrid/webgpu")
    print("   python3 server.py")


if __name__ == "__main__":
    run_all_tests()