"""Placeholder script. Populate environment variables before use."""

import os

REQUIRED_KEYS = ['YOUTUBE_API_KEY', 'GEMINI_API_KEY']

for key in REQUIRED_KEYS:
    if not os.environ.get(key):
        raise SystemExit(f"Environment variable {key} is required before running {__file__}.")

print("Environment ready. Implement processing logic here.")
