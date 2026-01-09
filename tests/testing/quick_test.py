"""Quick check for required API keys."""

import os

def ensure_keys():
    missing = [
        name for name in ("YOUTUBE_API_KEY", "GEMINI_API_KEY")
        if not os.environ.get(name)
    ]
    if missing:
        raise SystemExit(f"Missing required keys: {', '.join(missing)}")

if __name__ == "__main__":
    ensure_keys()
    print("All required keys present.")
