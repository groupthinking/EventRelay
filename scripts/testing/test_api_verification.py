#!/usr/bin/env python3
"""
API VERIFICATION SCRIPT

Tests actual API integration to verify working components vs mock fallbacks
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parents[2]
API_COST_DB = Path(
    os.getenv('API_COST_MONITOR_DB_PATH')
    or (PROJECT_ROOT / '.runtime' / 'api_cost_monitoring.db')
).expanduser()

def test_youtube_api():
    """Test YouTube API with real credentials"""
    try:
        from googleapiclient.discovery import build
        api_key = os.getenv('YOUTUBE_API_KEY')
        if not api_key:
            return False, "YOUTUBE_API_KEY not found"

        youtube = build('youtube', 'v3', developerKey=api_key)
        # Test with a simple search
        request = youtube.search().list(q='test', part='id', maxResults=1)
        response = request.execute()
        return True, f"YouTube API working - found {len(response.get('items', []))} results"
    except Exception as e:
        return False, f"YouTube API failed: {str(e)}"

def test_gemini_api():
    """Verify Gemini API connection and model availability"""
    print("\n🔹 Verifying Gemini API...")

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("❌ GEMINI_API_KEY not found in environment variables")
        return False, "GEMINI_API_KEY not found"

    try:
        from google import genai
        client = genai.Client(api_key=api_key)

        # Test generation with a simple prompt
        print("  - Testing content generation...")
        response = client.models.generate_content(
            model="gemini-2.0-flash-exp",
            contents="Hello, world!"
        )

        if response and response.text:
            print("  ✅ Gemini API connected and generating content")
            return True, f"Gemini API working - response: {response.text[:50]}..."
        else:
            print("  ❌ Gemini API returned empty response")
            return False, "Gemini API returned empty response"

    except Exception as e:
        print(f"  ❌ Gemini API verification failed: {str(e)}")
        return False, f"Gemini API failed: {str(e)}"

def test_openai_api():
    """Test OpenAI API with real credentials"""
    try:
        from openai import OpenAI
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            return False, "OPENAI_API_KEY not found"

        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "Hello, test message"}],
            max_tokens=50
        )
        return True, f"OpenAI API working - response: {response.choices[0].message.content[:50]}..."
    except Exception as e:
        return False, f"OpenAI API failed: {str(e)}"

def test_anthropic_api():
    """Test Anthropic API with real credentials"""
    try:
        from anthropic import Anthropic
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if not api_key:
            return False, "ANTHROPIC_API_KEY not found"

        client = Anthropic(api_key=api_key)
        response = client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=50,
            messages=[{"role": "user", "content": "Hello, test message"}]
        )
        return True, f"Anthropic API working - response: {response.content[0].text[:50]}..."
    except Exception as e:
        return False, f"Anthropic API failed: {str(e)}"

def test_database_connection():
    """Test database connection"""
    try:
        import sqlite3
        conn = sqlite3.connect(str(API_COST_DB))
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM api_usage')
        count = cursor.fetchone()[0]
        conn.close()
        return True, f"Database working - {count} records found"
    except Exception as e:
        return False, f"Database failed: {str(e)}"

def main():
    print("🔍 API VERIFICATION TEST")
    print("=" * 50)

    tests = [
        ("YouTube API", test_youtube_api),
        ("Gemini API", test_gemini_api),
        ("OpenAI API", test_openai_api),
        ("Anthropic API", test_anthropic_api),
        ("Database", test_database_connection),
    ]

    results = []
    for name, test_func in tests:
        print(f"\n🧪 Testing {name}...")
        try:
            success, message = test_func()
            status = "✅ PASS" if success else "❌ FAIL"
            print(f"   {status}: {message}")
            results.append((name, success, message))
        except Exception as e:
            print(f"   ❌ ERROR: Test failed with exception: {str(e)}")
            results.append((name, False, str(e)))

    print("\n" + "=" * 50)
    print("📊 SUMMARY:")

    working_count = sum(1 for _, success, _ in results if success)
    total_count = len(results)

    print(f"Working APIs: {working_count}/{total_count}")

    for name, success, message in results:
        status_icon = "✅" if success else "❌"
        print(f"  {status_icon} {name}: {'WORKING' if success else 'FAILED'}")

    if working_count == total_count:
        print("\n🎉 ALL APIS ARE WORKING CORRECTLY!")
        return 0
    else:
        print(f"\n⚠️  {total_count - working_count} API(s) FAILED")
        return 1

if __name__ == '__main__':
    sys.exit(main())
