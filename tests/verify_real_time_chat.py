import httpx
import asyncio
import json
import os
import sys


async def verify_real_time_chat():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--video-url", default="https://www.youtube.com/watch?v=yPYZpwSpKmA"
    )
    parser.add_argument("--query", default="What is this video about?")
    parser.add_argument(
        "--video-id", help="Video ID (optional, overrides video-url if provided)"
    )
    args = parser.parse_args()

    video_url = args.video_url
    if args.video_id:
        video_url = f"https://www.youtube.com/watch?v={args.video_id}"

    query = args.query

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
