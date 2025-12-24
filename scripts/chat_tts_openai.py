#!/usr/bin/env python3
"""
OpenAI Chat Completions audio TTS client (gpt-4o-audio-preview).

Usage:
  python3 scripts/chat_tts_openai.py "text to speak" [voice] [format]

Env:
  OPENAI_API_KEY or API_KEY_OPENAI (required)
  OPENAI_CHAT_TTS_MODEL (default: gpt-4o-audio-preview)
"""
import os
import sys
import json
import base64
import tempfile
import subprocess
import requests


def play_audio_bytes(data: bytes, fmt: str):
    suffix = ".wav" if fmt == "wav" else ".mp3"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as f:
        f.write(data)
        path = f.name
    try:
        if sys.platform == "darwin":
            subprocess.run(["afplay", path], check=True)
        elif sys.platform.startswith("linux"):
            player = ["aplay", path] if suffix == ".wav" else ["ffplay", "-nodisp", "-autoexit", path]
            subprocess.run(player, check=True)
        elif sys.platform == "win32":
            ps = (f"$p=New-Object System.Media.SoundPlayer('{path}');" "$p.PlaySync();")
            subprocess.run(["powershell", "-Command", ps], check=True)
    finally:
        try:
            os.remove(path)
        except Exception:
            pass


def main():
    if len(sys.argv) < 2:
        print("Provide text to speak.")
        sys.exit(1)
    text = sys.argv[1]
    voice = sys.argv[2] if len(sys.argv) > 2 else os.getenv("OPENAI_TTS_VOICE", "alloy")
    fmt = sys.argv[3] if len(sys.argv) > 3 else os.getenv("OPENAI_TTS_FORMAT", "wav")

    api_key = os.getenv("OPENAI_API_KEY") or os.getenv("API_KEY_OPENAI")
    if not api_key:
        print("OPENAI_API_KEY/API_KEY_OPENAI not set")
        sys.exit(2)

    model = os.getenv("OPENAI_CHAT_TTS_MODEL", "gpt-4o-audio-preview")
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    org = os.getenv("OPENAI_ORG_ID")
    proj = os.getenv("OPENAI_PROJECT_ID")
    if org:
        headers["OpenAI-Organization"] = org
    if proj:
        headers["OpenAI-Project"] = proj
    payload = {
        "model": model,
        "modalities": ["text", "audio"],
        "audio": {"voice": voice, "format": fmt},
        "messages": [
            {"role": "user", "content": text}
        ],
    }

    r = requests.post(url, headers=headers, data=json.dumps(payload), timeout=120)
    r.raise_for_status()
    data = r.json()
    try:
        b64 = data["choices"][0]["message"]["audio"]["data"]
    except Exception:
        print("No audio in response")
        sys.exit(3)
    audio_bytes = base64.b64decode(b64)
    play_audio_bytes(audio_bytes, fmt)


if __name__ == "__main__":
    main()


