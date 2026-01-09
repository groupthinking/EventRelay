"""Placeholder smoke test demonstrating env-based configuration."""

import os

os.environ.setdefault('YOUTUBE_API_KEY', 'YOUR_YOUTUBE_API_KEY')
os.environ.setdefault('GEMINI_API_KEY', 'YOUR_GEMINI_API_KEY')

if __name__ == "__main__":
    print("✅ YouTube API key configured?", os.environ['YOUTUBE_API_KEY'] != 'YOUR_YOUTUBE_API_KEY')
    print("✅ Gemini API key configured?", os.environ['GEMINI_API_KEY'] != 'YOUR_GEMINI_API_KEY')
