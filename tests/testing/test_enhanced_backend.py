#!/usr/bin/env python3
"""
Test Enhanced FastAPI Backend
Test the new markdown processing endpoints and caching functionality
"""

import asyncio
import aiohttp
import json
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE_URL = "http://localhost:8000"

async def test_health_check():
    """Test the health check endpoint"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{BASE_URL}/health") as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info(f"✅ Health check passed: {data}")
                    return True
                else:
                    logger.error(f"❌ Health check failed: {response.status}")
                    return False
    except Exception as e:
        logger.error(f"❌ Health check error: {e}")
        return False

async def test_markdown_processing():
    """Test the new markdown processing endpoint"""
    try:
        test_video_url = "https://www.youtube.com/watch?v=aircAruvnKk"
        
        payload = {
            "video_url": test_video_url,
            "force_regenerate": False
        }
        
        logger.info(f"🚀 Testing markdown processing for: {test_video_url}")
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{BASE_URL}/api/process-video-markdown",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=300)  # 5 minute timeout
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info(f"✅ Markdown processing successful!")
                    logger.info(f"   Video ID: {data.get('video_id')}")
                    logger.info(f"   Cached: {data.get('cached')}")
                    logger.info(f"   Processing time: {data.get('processing_time')}")
                    logger.info(f"   Save path: {data.get('save_path')}")
                    
                    # Show preview of markdown content
                    markdown_preview = data.get('markdown_content', '')[:300]
                    logger.info(f"   Markdown preview: {markdown_preview}...")
                    
                    return data.get('video_id')
                else:
                    error_text = await response.text()
                    logger.error(f"❌ Markdown processing failed: {response.status}")
                    logger.error(f"   Error: {error_text}")
                    return None
                    
    except Exception as e:
        logger.error(f"❌ Markdown processing error: {e}")
        return None

async def test_markdown_retrieval(video_id: str):
    """Test retrieving cached markdown analysis"""
    try:
        logger.info(f"📄 Testing markdown retrieval for: {video_id}")
        
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{BASE_URL}/api/markdown/{video_id}") as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info(f"✅ Markdown retrieval successful!")
                    logger.info(f"   Video ID: {data.get('video_id')}")
                    logger.info(f"   Cached: {data.get('cached')}")
                    logger.info(f"   Cache age: {data.get('cache_age_hours', 0):.2f} hours")
                    logger.info(f"   File size: {data.get('file_size', 0)} bytes")
                    return True
                else:
                    error_text = await response.text()
                    logger.error(f"❌ Markdown retrieval failed: {response.status}")
                    logger.error(f"   Error: {error_text}")
                    return False
                    
    except Exception as e:
        logger.error(f"❌ Markdown retrieval error: {e}")
        return False

async def test_cache_stats():
    """Test cache statistics endpoint"""
    try:
        logger.info(f"📊 Testing cache statistics")
        
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{BASE_URL}/api/cache/stats") as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info(f"✅ Cache stats retrieved successfully!")
                    logger.info(f"   Total cached videos: {data.get('total_cached_videos')}")
                    logger.info(f"   Total size: {data.get('total_size_mb')} MB")
                    logger.info(f"   Categories: {list(data.get('categories', {}).keys())}")
                    return True
                else:
                    error_text = await response.text()
                    logger.error(f"❌ Cache stats failed: {response.status}")
                    logger.error(f"   Error: {error_text}")
                    return False
                    
    except Exception as e:
        logger.error(f"❌ Cache stats error: {e}")
        return False

async def test_original_endpoints():
    """Test that original endpoints still work"""
    try:
        # Test chat endpoint
        logger.info(f"💬 Testing chat endpoint")
        
        payload = {
            "message": "Hello, can you help me process a video?",
            "context": "tooltip-assistant",
            "session_id": "test-session"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{BASE_URL}/api/chat", json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info(f"✅ Chat endpoint working!")
                    logger.info(f"   Response: {data.get('response')[:100]}...")
                    return True
                else:
                    error_text = await response.text()
                    logger.error(f"❌ Chat endpoint failed: {response.status}")
                    logger.error(f"   Error: {error_text}")
                    return False
                    
    except Exception as e:
        logger.error(f"❌ Chat endpoint error: {e}")
        return False

async def run_comprehensive_tests():
    """Run all tests to validate the enhanced backend"""
    logger.info("🧪 Starting Enhanced Backend Tests")
    logger.info("=" * 50)
    
    # Test results tracking
    results = {
        "health_check": False,
        "markdown_processing": False,
        "markdown_retrieval": False,
        "cache_stats": False,
        "original_endpoints": False
    }
    
    # 1. Health check
    results["health_check"] = await test_health_check()
    
    if not results["health_check"]:
        logger.error("❌ Backend not available - stopping tests")
        return results
    
    # 2. Test original endpoints still work
    results["original_endpoints"] = await test_original_endpoints()
    
    # 3. Test new markdown processing
    video_id = await test_markdown_processing()
    if video_id:
        results["markdown_processing"] = True
        
        # 4. Test markdown retrieval
        results["markdown_retrieval"] = await test_markdown_retrieval(video_id)
    
    # 5. Test cache stats
    results["cache_stats"] = await test_cache_stats()
    
    # Results summary
    logger.info("=" * 50)
    logger.info("🏁 Test Results Summary:")
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        logger.info(f"   {test_name}: {status}")
    
    total_passed = sum(results.values())
    logger.info(f"\nOverall: {total_passed}/{len(results)} tests passed")
    
    if total_passed == len(results):
        logger.info("🎉 All tests passed! Enhanced backend is working correctly.")
    else:
        logger.warning(f"⚠️  {len(results) - total_passed} tests failed. Check logs above.")
    
    return results

if __name__ == "__main__":
    print(f"""
🚀 Enhanced FastAPI Backend Test Suite
=====================================

This will test the new markdown processing functionality:
1. Health check endpoint
2. Original chat endpoint (backwards compatibility)
3. New /api/process-video-markdown endpoint
4. New /api/markdown/{{video_id}} endpoint  
5. New /api/cache/stats endpoint

Make sure the backend is running on {BASE_URL}
""")
    
if __name__ == "__main__":
    # Run tests
    asyncio.run(run_comprehensive_tests())