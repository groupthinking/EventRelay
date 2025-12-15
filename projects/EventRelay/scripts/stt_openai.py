#!/usr/bin/env python3
"""
OpenAI Transcription client using /audio/transcriptions (e.g., whisper-1 or gpt-4o-mini-transcribe).

Usage:
  python3 scripts/stt_openai.py path/to/audio.wav [model]

Env:
  OPENAI_API_KEY or API_KEY_OPENAI
  OPENAI_STT_MODEL (default: whisper-1)
"""
import os
import sys
import requests


def main():
    if len(sys.argv) < 2:
        print("Provide an audio file path.")
        sys.exit(1)
    path = sys.argv[1]
    model = sys.argv[2] if len(sys.argv) > 2 else os.getenv("OPENAI_STT_MODEL", "whisper-1")
    api_key = os.getenv("OPENAI_API_KEY") or os.getenv("API_KEY_OPENAI")
    if not api_key:
        print("OPENAI_API_KEY/API_KEY_OPENAI not set")
        sys.exit(2)

    url = "https://api.openai.com/v1/audio/transcriptions"
    headers = {"Authorization": f"Bearer {api_key}"}
    org = os.getenv("OPENAI_ORG_ID")
    proj = os.getenv("OPENAI_PROJECT_ID")
    if org:
        headers["OpenAI-Organization"] = org
    if proj:
        headers["OpenAI-Project"] = proj
    files = {"file": open(path, "rb")}
    data = {"model": model}
    r = requests.post(url, headers=headers, files=files, data=data, timeout=120)
    r.raise_for_status()
    print(r.json())


if __name__ == "__main__":
    main()


