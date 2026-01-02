"""Demo application showing how to configure environment-based API keys."""

import os

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "YOUR_GEMINI_API_KEY")
YOUTUBE_API_KEY = os.environ.get("YOUTUBE_API_KEY", "YOUR_YOUTUBE_API_KEY")

if __name__ == "__main__":
    print("Gemini API key set?", GEMINI_API_KEY != "YOUR_GEMINI_API_KEY")
    print("YouTube API key set?", YOUTUBE_API_KEY != "YOUR_YOUTUBE_API_KEY")
