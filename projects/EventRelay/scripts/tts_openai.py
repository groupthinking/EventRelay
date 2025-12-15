#!/usr/bin/env python3
"""
OpenAI TTS client.

Usage:
  python3 scripts/tts_openai.py "text to speak" [voice] [format]

Env:
  OPENAI_API_KEY  (required)
  OPENAI_TTS_MODEL (optional, default: gpt-4o-mini-tts)

Notes:
  - Falls back to 'tts-1' model if specified model is not available.
  - Uses 'wav' format by default for easy playback with afplay/aplay.
"""
import os
import sys
import json
import time
import tempfile
import subprocess
import requests


def read_env_file_if_present():
    # Light best-effort .env loader without external deps
    env_path_candidates = [
        os.path.join(os.getcwd(), ".env"),
        os.path.join(os.path.dirname(os.getcwd()), ".env"),
    ]
    for p in env_path_candidates:
        if os.path.isfile(p):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith("#"):
                            continue
                        if "=" in line:
                            k, v = line.split("=", 1)
                            k = k.strip()
                            v = v.strip().strip('"').strip("'")
                            os.environ.setdefault(k, v)
            except Exception:
                pass


def tts_request(api_key: str, text: str, voice: str, fmt: str, model: str) -> bytes:
    url = "https://api.openai.com/v1/audio/speech"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    # Optional scoping headers for org/project keys
    org = os.getenv("OPENAI_ORG_ID")
    proj = os.getenv("OPENAI_PROJECT_ID")
    if org:
        headers["OpenAI-Organization"] = org
    if proj:
        headers["OpenAI-Project"] = proj
    payload = {
        "model": model,
        "input": text,
        "voice": voice,
        "format": fmt,
    }
    r = requests.post(url, headers=headers, data=json.dumps(payload), timeout=120)
    if r.status_code == 404 and model != "tts-1":
        # Fallback to tts-1 if the preferred model is not present
        payload["model"] = "tts-1"
        r = requests.post(url, headers=headers, data=json.dumps(payload), timeout=120)
    r.raise_for_status()
    return r.content


def play_audio(data: bytes, fmt: str):
    suffix = ".wav" if fmt == "wav" else ".mp3"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as f:
        f.write(data)
        tmp_path = f.name
    try:
        if sys.platform == "darwin":
            subprocess.run(["afplay", tmp_path], check=True)
        elif sys.platform.startswith("linux"):
            # Try aplay for wav; else ffplay if available
            player = ["aplay", tmp_path] if suffix == ".wav" else ["ffplay", "-nodisp", "-autoexit", tmp_path]
            subprocess.run(player, check=True)
        elif sys.platform == "win32":
            ps = (
                f"$p=New-Object System.Media.SoundPlayer('{tmp_path}');"
                "$p.PlaySync();"
            )
            subprocess.run(["powershell", "-Command", ps], check=True)
        else:
            pass
    finally:
        try:
            os.remove(tmp_path)
        except Exception:
            pass


def main():
    read_env_file_if_present()
    if len(sys.argv) < 2:
        print("Provide text to speak.")
        sys.exit(1)
    text = sys.argv[1]
    voice = sys.argv[2] if len(sys.argv) > 2 else os.getenv("OPENAI_TTS_VOICE", "alloy")
    fmt = sys.argv[3] if len(sys.argv) > 3 else os.getenv("OPENAI_TTS_FORMAT", "wav")
    api_key = os.getenv("OPENAI_API_KEY") or os.getenv("API_KEY_OPENAI")
    if not api_key:
        print("OPENAI_API_KEY not set in environment or .env")
        sys.exit(2)
    model = os.getenv("OPENAI_TTS_MODEL", "gpt-4o-mini-tts")
    audio = tts_request(api_key, text, voice, fmt, model)
    play_audio(audio, fmt)


if __name__ == "__main__":
    main()


