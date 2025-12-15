#!/usr/bin/env python3
"""
Orchestrate summary-to-speech:
 - Prefer OpenAI TTS if API key is configured (.env or env).
 - Fallback to macOS 'say' on local dev.

Usage:
  python3 scripts/say_summary.py "short summary text"
"""
import os
import sys
import subprocess
import requests  # kept for future health checks


def main():
    if len(sys.argv) < 2:
        print("Provide summary text.")
        sys.exit(1)
    text = sys.argv[1]

    # Support both env var names
    openai_key = os.getenv("OPENAI_API_KEY") or os.getenv("API_KEY_OPENAI")

    if openai_key:
        # Use OpenAI TTS; if it fails, continue to macOS fallback
        cp = subprocess.run(["python3", "scripts/tts_openai.py", text], check=False)
        if cp.returncode == 0:
            return

    # macOS native fallback (ensures at least one audible path during local dev)
    if sys.platform == "darwin":
        try:
            subprocess.run(["say", text], check=True)
            return
        except Exception:
            pass

    print("No TTS backend available: set OPENAI_API_KEY/API_KEY_OPENAI or use macOS 'say'.")


if __name__ == "__main__":
    main()


