import httpx
import asyncio
import json
import os
import sys


async def verify_real_time_chat():
    # Use a video URL that is likely NOT processed yet.
    # "Together Forever" by Rick Astley
    video_url = "https://www.youtube.com/watch?v=yPYZpwSpKmA"  # Together Forever

    # Alternatively, use a fresh one from a recent tech talk
    # "Google I/O 2024 Keynote" - highly likely to work with Gemini
    # video_url = "https://www.youtube.com/watch?v=N8-U8A-v1XU"

    query = "What is this video about?"

    payload = {
        "query": query,
        "video_url": video_url,
        "context": "tooltip-assistant",
        "session_id": "test_real_time",
    }

    print(f"--- Testing Real-Time Chat with Video Context ---")
    print(f"Video URL: {video_url}")
    print(f"Query: {query}")
    print(f"Sending request to /api/v1/chat...")

    timeout = httpx.Timeout(120.0, connect=60.0)  # Longer timeout for processing

    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            response = await client.post(
                "http://localhost:8000/api/v1/chat", json=payload
            )
            print(f"Status Code: {response.status_code}")

            if response.status_code == 200:
                result = response.json()
                print("\nAssistant Response:")
                print(result.get("response"))
                print(f"\nStatus: {result.get('status')}")
            else:
                print(f"Error: {response.text}")

        except Exception as e:
            print(f"Exception: {e}")


if __name__ == "__main__":
    asyncio.run(verify_real_time_chat())
