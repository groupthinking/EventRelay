import asyncio
import httpx
import json


async def populate_video():
    print("Populating video data...")
    url = "http://localhost:8000/api/v1/transcript-action"

    payload = {"video_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"}

    print(f"Sending request to {url}...")
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(url, json=payload)
            print(f"Status Code: {response.status_code}")
            if response.status_code == 200:
                print("Video processed successfully.")
            else:
                print(f"Error: {response.text}")
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    asyncio.run(populate_video())
