#!/usr/bin/env python3
"""
YouTube Data API v3 Test Script
Based on official Google documentation: https://developers.google.com/youtube/v3/code_samples/code_snippets
"""

import os
import sys
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_youtube_api():
    """Test YouTube Data API v3 with our API key"""
    
    # Get API key from environment
    api_key = os.getenv('YOUTUBE_API_KEY') or os.getenv('REACT_APP_YOUTUBE_API_KEY')
    
    if not api_key:
        print("❌ No YouTube API key found in environment variables")
        print("Please set YOUTUBE_API_KEY or REACT_APP_YOUTUBE_API_KEY in your .env file")
        return False
    
    print(f"🔑 Using API key: {api_key[:10]}...")
    
    try:
        # Build the YouTube API service
        youtube = build('youtube', 'v3', developerKey=api_key)
        
        # Test 1: Get information about GoogleDevelopers channel (public data)
        print("\n🎯 Test 1: Getting GoogleDevelopers channel info...")
        request = youtube.channels().list(
            part='snippet,statistics',
            id='UC_x5XG1OV2P6uZZ5FSM9Ttw'  # GoogleDevelopers channel ID
        )
        response = request.execute()
        
        if response['items']:
            channel = response['items'][0]
            print(f"✅ Channel found: {channel['snippet']['title']}")
            print(f"   Subscribers: {channel['statistics'].get('subscriberCount', 'N/A')}")
            print(f"   Views: {channel['statistics'].get('viewCount', 'N/A')}")
            print(f"   Videos: {channel['statistics'].get('videoCount', 'N/A')}")
        else:
            print("❌ No channel found")
            return False
        
        # Test 2: Get video information (public data)
        print("\n🎯 Test 2: Getting video info...")
        video_id = 'LnKoncbQBsM'  # Linux File Permissions video
        request = youtube.videos().list(
            part='snippet,statistics,contentDetails',
            id=video_id
        )
        response = request.execute()
        
        if response['items']:
            video = response['items'][0]
            print(f"✅ Video found: {video['snippet']['title']}")
            print(f"   Channel: {video['snippet']['channelTitle']}")
            print(f"   Views: {video['statistics'].get('viewCount', 'N/A')}")
            print(f"   Likes: {video['statistics'].get('likeCount', 'N/A')}")
            print(f"   Duration: {video['contentDetails']['duration']}")
        else:
            print("❌ No video found")
            return False
        
        # Test 3: Search for videos
        print("\n🎯 Test 3: Searching for videos...")
        request = youtube.search().list(
            part='snippet',
            q='world class software development',
            type='video',
            maxResults=5
        )
        response = request.execute()
        
        print(f"✅ Found {len(response['items'])} videos:")
        for item in response['items']:
            print(f"   - {item['snippet']['title']}")
        
        print("\n🎉 All YouTube API tests passed!")
        return True
        
    except HttpError as e:
        print(f"❌ YouTube API Error: {e}")
        if e.resp.status == 400:
            print("   This usually means the API key is invalid or has restrictions")
        elif e.resp.status == 403:
            print("   This usually means the API key doesn't have the required permissions")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def test_api_key_format():
    """Test if the API key format is valid"""
    
    api_key = os.getenv('YOUTUBE_API_KEY') or os.getenv('REACT_APP_YOUTUBE_API_KEY')
    
    if not api_key:
        print("❌ No API key found")
        return False
    
    # YouTube API keys should be 39 characters and start with 'AIzaSy'
    if len(api_key) != 39:
        print(f"❌ API key length is {len(api_key)}, should be 39 characters")
        return False
    
    if not api_key.startswith('AIzaSy'):
        print("❌ API key should start with 'AIzaSy'")
        return False
    
    print("✅ API key format is valid")
    return True

def main():
    """Main test function"""
    
    print("🧪 Testing YouTube Data API v3 Setup")
    print("=" * 50)
    
    # Test API key format
    if not test_api_key_format():
        print("\n❌ API key format test failed")
        return
    
    # Test API functionality
    if test_youtube_api():
        print("\n🎉 All tests passed! Your YouTube API setup is working correctly.")
        print("\nNext steps:")
        print("1. Update your .env file with the working API key")
        print("2. Test the MCP proxy server")
        print("3. Run the world-class video processor")
    else:
        print("\n❌ API functionality test failed")
        print("\nTroubleshooting:")
        print("1. Check if your API key is valid in Google Cloud Console")
        print("2. Ensure YouTube Data API v3 is enabled for your project")
        print("3. Check if there are any restrictions on your API key")

if __name__ == "__main__":
    main()
