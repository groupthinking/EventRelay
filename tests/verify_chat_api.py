import asyncio
import httpx
import json
import sys


async def test_chat_endpoint():
    print("Testing /chat endpoint...")

    url = "http://localhost:8000/api/v1/chat"

    # Test case 1: Basic chat without video context
    payload = {
        "query": "Hello, how can you help me?",
        "session_id": "test_session_1",
        "context": "tooltip-assistant",
    }

    print(f"\nTest 1: Basic chat - Sending to {url}")
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload)
            print(f"Status Code: {response.status_code}")
            if response.status_code == 200:
                print("Response data:")
                print(json.dumps(response.json(), indent=2))
            else:
                print(f"Error response: {response.text}")
    except Exception as e:
        print(f"Error connecting to server: {e}")
        return

    # Test case 2: Chat with video context (Rick Roll)
    payload_with_video = {
        "query": "What is this video about?",
        "video_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "session_id": "test_session_2",
        "context": "universal-ask",
    }

    print(f"\nTest 2: Chat with video context - Sending to {url}")
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload_with_video)
            print(f"Status Code: {response.status_code}")
            if response.status_code == 200:
                print("Response data:")
                print(json.dumps(response.json(), indent=2))
            else:
                print(f"Error response: {response.text}")
    except Exception as e:
        print(f"Error connecting to server: {e}")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--run":
        asyncio.run(test_chat_endpoint())
    else:
        print("Usage: python tests/verify_chat_api.py --run")
        print(
            "Make sure the backend server relative to GroupThinking/EventRelay is running at localhost:8000"
        )
