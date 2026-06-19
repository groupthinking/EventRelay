import json

import requests

BASE_URL = "http://localhost:8001"

def test_api():
    print("Checking base API connection...")
    res = requests.get(f"{BASE_URL}/docs")
    if res.status_code != 200:
        print("Failed to connect to API")
        return

    print("API is up.")

    # 1. Test Transcript-Action Workflow
    video_url = "https://www.youtube.com/watch?v=i3FOFgimXn0"
    print("\n--- Testing /api/v1/transcript-action ---")
    print(f"URL: {video_url}")

    headers = {"Content-Type": "application/json"}
    payload = {
        "video_url": video_url,
        "language": "en"
    }

    try:
        response = requests.post(
            f"{BASE_URL}/api/v1/transcript-action",
            json=payload,
            headers=headers,
            timeout=120
        )
        print(f"Status Code: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print("Success! Action Plan Generated.")
            # Print a brief snippet
            print(json.dumps(data, indent=2)[:500] + "\n...")
        else:
            print("Error response:")
            print(response.text)

    except Exception as e:
        print(f"Request failed: {e}")

if __name__ == "__main__":
    test_api()
