
import os
import sys
import requests

def test_key():
    api_key = os.environ.get("YOUTUBE_API_KEY")
    if not api_key:
        print("❌ YOUTUBE_API_KEY not found in environment")
        return

    print(f"🔑 Testing API Key: {api_key[:4]}...{api_key[-4:]}")
    
    url = "https://www.googleapis.com/youtube/v3/videos"
    params = {
        'id': 'WNJmTvqraW8',
        'key': api_key,
        'part': 'snippet'
    }
    
    try:
        response = requests.get(url, params=params)
        print(f"📡 Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            if "items" in data and len(data["items"]) > 0:
                print("✅ API Key is VALID and working!")
                print("   Video Title:", data["items"][0]["snippet"]["title"])
            else:
                print("⚠️  API Key worked, but returned no items (unexpected for this video).")
        else:
            print("❌ API Key FAILED")
            print("   Response:", response.text)
            
    except Exception as e:
        print(f"❌ Connection Error: {e}")

if __name__ == "__main__":
    test_key()
