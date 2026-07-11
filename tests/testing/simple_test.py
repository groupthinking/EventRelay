"""Placeholder smoke test demonstrating env-based configuration."""

import os

if __name__ == "__main__":
    # Only set placeholder defaults when run as a script — never as an import
    # side-effect, which would pollute the environment for other test modules.
    os.environ.setdefault('YOUTUBE_API_KEY', 'YOUR_YOUTUBE_API_KEY')
    os.environ.setdefault('GEMINI_API_KEY', 'YOUR_GEMINI_API_KEY')
    print("✅ YouTube API key configured?", os.environ['YOUTUBE_API_KEY'] != 'YOUR_YOUTUBE_API_KEY')
    print("✅ Gemini API key configured?", os.environ['GEMINI_API_KEY'] != 'YOUR_GEMINI_API_KEY')
