#!/usr/bin/env python3
"""
Integration Test Script
=======================

This script tests the FastAPI backend and frontend integration.
"""

import asyncio
import aiohttp
import json
import time
from pathlib import Path

# Test configuration
BACKEND_URL = "http://localhost:8000"
TEST_MESSAGE = "Hello, this is a test message from the integration test!"

async def test_health_endpoint():
    """Test the health endpoint"""
    print("🔍 Testing health endpoint...")
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(f"{BACKEND_URL}/health") as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ Health check passed: {data}")
                    return True
                else:
                    print(f"❌ Health check failed: {response.status}")
                    return False
        except Exception as e:
            print(f"❌ Health check error: {e}")
            return False

async def test_chat_endpoint():
    """Test the chat endpoint"""
    print("🔍 Testing chat endpoint...")
    
    async with aiohttp.ClientSession() as session:
        try:
            payload = {
                "message": TEST_MESSAGE,
                "context": "tooltip-assistant",
                "session_id": "test-session"
            }
            
            async with session.post(
                f"{BACKEND_URL}/api/chat",
                json=payload,
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ Chat endpoint passed: {data['response'][:100]}...")
                    return True
                else:
                    print(f"❌ Chat endpoint failed: {response.status}")
                    error_text = await response.text()
                    print(f"Error details: {error_text}")
                    return False
        except Exception as e:
            print(f"❌ Chat endpoint error: {e}")
            return False

async def test_video_processing_endpoint():
    """Test the video processing endpoint"""
    print("🔍 Testing video processing endpoint...")
    
    async with aiohttp.ClientSession() as session:
        try:
            payload = {
                "video_url": "https://www.youtube.com/watch?v=aircAruvnKk",  # 3Blue1Brown - Educational content
                "options": {}
            }
            
            async with session.post(
                f"{BACKEND_URL}/api/process-video",
                json=payload,
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ Video processing endpoint passed: {data['status']}")
                    return True
                else:
                    print(f"❌ Video processing endpoint failed: {response.status}")
                    error_text = await response.text()
                    print(f"Error details: {error_text}")
                    return False
        except Exception as e:
            print(f"❌ Video processing endpoint error: {e}")
            return False

async def test_websocket_connection():
    """Test WebSocket connection"""
    print("🔍 Testing WebSocket connection...")
    
    try:
        import websockets
        
        uri = f"ws://localhost:8000/ws"
        async with websockets.connect(uri) as websocket:
            # Wait for welcome message
            welcome_message = await websocket.recv()
            welcome_data = json.loads(welcome_message)
            
            if welcome_data.get("type") == "connection":
                print(f"✅ WebSocket connection established: {welcome_data['message']}")
                
                # Send a ping message
                ping_message = {
                    "type": "ping",
                    "timestamp": time.time()
                }
                await websocket.send(json.dumps(ping_message))
                
                # Wait for pong response
                pong_message = await websocket.recv()
                pong_data = json.loads(pong_message)
                
                if pong_data.get("type") == "pong":
                    print("✅ WebSocket ping/pong test passed")
                    return True
                else:
                    print(f"❌ Unexpected pong response: {pong_data}")
                    return False
            else:
                print(f"❌ Unexpected welcome message: {welcome_data}")
                return False
                
    except ImportError:
        print("⚠️ websockets library not available, skipping WebSocket test")
        return True
    except Exception as e:
        print(f"❌ WebSocket test error: {e}")
        return False

async def main():
    """Run all integration tests"""
    print("🚀 Starting integration tests...")
    print("=" * 50)
    
    tests = [
        ("Health Endpoint", test_health_endpoint),
        ("Chat Endpoint", test_chat_endpoint),
        ("Video Processing Endpoint", test_video_processing_endpoint),
        ("WebSocket Connection", test_websocket_connection),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n🧪 Running {test_name}...")
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
            results.append((test_name, False))
    
    print("\n" + "=" * 50)
    print("📊 Integration Test Results:")
    print("=" * 50)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{status} - {test_name}")
        if result:
            passed += 1
    
    print(f"\n🎯 Overall Result: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All integration tests passed! Frontend/backend integration is working.")
    else:
        print("⚠️ Some tests failed. Please check the backend and try again.")
    
    return passed == total

if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
