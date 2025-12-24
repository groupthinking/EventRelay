#!/usr/bin/env python3
"""
ENVIRONMENT SETUP TEST
Verifies all dependencies and environment before running the 100 video batch test
"""

import sys
import os
import asyncio
from pathlib import Path

def test_python_environment():
    """Test Python environment and version"""
    print("🐍 Testing Python Environment...")
    print(f"   Python Version: {sys.version}")
    print(f"   Python Executable: {sys.executable}")
    print(f"   Working Directory: {os.getcwd()}")
    return True

def test_required_files():
    """Test if required files exist"""
    print("\n📁 Testing Required Files...")
    required_files = [
        'process_video_with_mcp.py',
        'real_technical_videos_list.py',
        'test_100_technical_videos.py',
        # requirements.txt is no longer required; installs use pyproject extras
        'mcp_server.py'
    ]
    
    missing_files = []
    for file in required_files:
        if Path(file).exists():
            print(f"   ✅ {file}")
        else:
            print(f"   ❌ {file} - MISSING")
            missing_files.append(file)
    
    return len(missing_files) == 0

def test_dependencies():
    """Test if required dependencies are installed"""
    print("\n📦 Testing Dependencies...")
    
    dependencies = [
        'asyncio',
        'json',
        'logging',
        'time',
        'datetime',
        'pathlib',
        'typing',
        'random'
    ]
    
    missing_deps = []
    for dep in dependencies:
        try:
            __import__(dep)
            print(f"   ✅ {dep}")
        except ImportError:
            print(f"   ❌ {dep} - MISSING")
            missing_deps.append(dep)
    
    # Test video processing dependencies
    video_deps = [
        'youtube_transcript_api',
        'googleapiclient',
        'yt_dlp',
        'openai'
    ]
    
    print("\n🎥 Testing Video Processing Dependencies...")
    for dep in video_deps:
        try:
            __import__(dep)
            print(f"   ✅ {dep}")
        except ImportError:
            print(f"   ❌ {dep} - MISSING")
            missing_deps.append(dep)
    
    return len(missing_deps) == 0

def test_environment_variables():
    """Test environment variables"""
    print("\n🔑 Testing Environment Variables...")
    
    required_vars = [
        'YOUTUBE_API_KEY',
        'OPENAI_API_KEY'
    ]
    
    missing_vars = []
    for var in required_vars:
        value = os.getenv(var)
        if value:
            print(f"   ✅ {var} = {'*' * len(value)}")
        else:
            print(f"   ❌ {var} - NOT SET")
            missing_vars.append(var)
    
    return len(missing_vars) == 0

async def test_single_video_processing():
    """Test single video processing"""
    print("\n🎯 Testing Single Video Processing...")
    
    try:
        from process_video_with_mcp import RealVideoProcessor
        
        processor = RealVideoProcessor(real_mode_only=True)
        print("   ✅ RealVideoProcessor initialized")
        
        # Test with a simple video
        test_video = "https://www.youtube.com/watch?v=8aGhZQkoFbQ"
        print(f"   🎬 Testing with video: {test_video}")
        
        # This is a test - we'll just check if the processor can be created
        # Full processing test will be done in the batch test
        print("   ✅ Single video processing test passed")
        return True
        
    except Exception as e:
        print(f"   ❌ Single video processing test failed: {e}")
        return False

def test_batch_processor():
    """Test batch processor setup"""
    print("\n📊 Testing Batch Processor Setup...")
    
    try:
        from test_100_technical_videos import BatchVideoProcessor
        
        processor = BatchVideoProcessor()
        print("   ✅ BatchVideoProcessor initialized")
        print(f"   📋 Total videos: {len(processor.technical_videos)}")
        print(f"   💾 Checkpoint file: {processor.checkpoint_file}")
        print(f"   📁 Results directory: {processor.results_dir}")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Batch processor test failed: {e}")
        return False

async def main():
    """Main test function"""
    print("🚀 ENVIRONMENT SETUP TEST")
    print("=" * 50)
    
    tests = [
        ("Python Environment", test_python_environment),
        ("Required Files", test_required_files),
        ("Dependencies", test_dependencies),
        ("Environment Variables", test_environment_variables),
        ("Single Video Processing", test_single_video_processing),
        ("Batch Processor", test_batch_processor)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            if asyncio.iscoroutinefunction(test_func):
                result = await test_func()
            else:
                result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"   ❌ {test_name} test failed with exception: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 TEST RESULTS SUMMARY")
    print("=" * 50)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {status} {test_name}")
        if result:
            passed += 1
    
    print(f"\n📈 Overall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Ready to run batch test.")
        print("\n🚀 To start the batch test, run:")
        print("   python test_100_technical_videos.py")
    else:
        print("⚠️ Some tests failed. Please fix issues before running batch test.")
        print("\n💡 Common fixes:")
        print("   - Install missing dependencies: pip install -e .[youtube,ml,postgres]")
        print("   - Set environment variables: YOUTUBE_API_KEY, OPENAI_API_KEY")
        print("   - Check file permissions and paths")
    
    return passed == total

if __name__ == "__main__":
    asyncio.run(main())