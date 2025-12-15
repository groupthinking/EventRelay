#!/usr/bin/env python3
"""
Chained voice agent: (optional) STT -> LLM -> TTS with local playback.

Usage examples:
  # From audio file
  python3 scripts/voice_agent_chained.py --audio sample.wav

  # From text prompt directly
  python3 scripts/voice_agent_chained.py --text "Give me 3 tips to focus better."

Env:
  OPENAI_API_KEY or API_KEY_OPENAI
  OPENAI_STT_MODEL (default: whisper-1)
  OPENAI_TEXT_MODEL (default: gpt-4.1-mini)
  OPENAI_TTS_MODEL (default: gpt-4o-mini-tts)
  OPENAI_TTS_VOICE (default: alloy)
  OPENAI_TTS_FORMAT (default: wav)
"""
import os
import sys
import json
import base64
import argparse
import tempfile
import subprocess
from typing import Optional

import requests


API_BASE = "https://api.openai.com/v1"


def get_api_key() -> str:
    key = os.getenv("OPENAI_API_KEY") or os.getenv("API_KEY_OPENAI")
    if not key:
        print("OPENAI_API_KEY/API_KEY_OPENAI not set", file=sys.stderr)
        sys.exit(2)
    return key


def play_audio_bytes(data: bytes, fmt: str) -> None:
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


def transcribe_file(path: str, api_key: str, model: str) -> str:
    url = f"{API_BASE}/audio/transcriptions"
    headers = {"Authorization": f"Bearer {api_key}"}
    org = os.getenv("OPENAI_ORG_ID")
    proj = os.getenv("OPENAI_PROJECT_ID")
    if org:
        headers["OpenAI-Organization"] = org
    if proj:
        headers["OpenAI-Project"] = proj
    files = {"file": open(path, "rb")}
    data = {"model": model}
    r = requests.post(url, headers=headers, files=files, data=data, timeout=300)
    r.raise_for_status()
    j = r.json()
    return j.get("text") or j.get("transcript") or json.dumps(j)


def chat_complete(prompt: str, api_key: str, model: str) -> str:
    url = f"{API_BASE}/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    org = os.getenv("OPENAI_ORG_ID")
    proj = os.getenv("OPENAI_PROJECT_ID")
    if org:
        headers["OpenAI-Organization"] = org
    if proj:
        headers["OpenAI-Project"] = proj
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "You are a concise, friendly voice assistant. Avoid markdown, lists, emoji."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.7,
        "stream": False,
    }
    r = requests.post(url, headers=headers, data=json.dumps(payload), timeout=120)
    r.raise_for_status()
    j = r.json()
    try:
        return j["choices"][0]["message"]["content"]
    except Exception:
        return json.dumps(j)


def tts_speak(text: str, api_key: str, model: str, voice: str, fmt: str) -> bool:
    url = f"{API_BASE}/audio/speech"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    org = os.getenv("OPENAI_ORG_ID")
    proj = os.getenv("OPENAI_PROJECT_ID")
    if org:
        headers["OpenAI-Organization"] = org
    if proj:
        headers["OpenAI-Project"] = proj
    payload = {"model": model, "input": text, "voice": voice, "format": fmt}
    r = requests.post(url, headers=headers, data=json.dumps(payload), timeout=300)
    if r.status_code != 200:
        return False
    try:
        play_audio_bytes(r.content, fmt)
        return True
    except Exception:
        return False


def mac_say(text: str) -> None:
    if sys.platform == "darwin":
        try:
            subprocess.run(["say", text], check=False)
        except Exception:
            pass


def main():
    p = argparse.ArgumentParser()
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--audio", help="Path to input audio (wav/mp3)")
    g.add_argument("--text", help="Text prompt to process")
    p.add_argument("--voice", default=os.getenv("OPENAI_TTS_VOICE", "alloy"))
    p.add_argument("--fmt", default=os.getenv("OPENAI_TTS_FORMAT", "wav"))
    p.add_argument("--stt_model", default=os.getenv("OPENAI_STT_MODEL", "whisper-1"))
    p.add_argument("--text_model", default=os.getenv("OPENAI_TEXT_MODEL", "gpt-4.1-mini"))
    p.add_argument("--tts_model", default=os.getenv("OPENAI_TTS_MODEL", "gpt-4o-mini-tts"))
    args = p.parse_args()

    api_key = get_api_key()

    if args.audio:
        if not os.path.isfile(args.audio):
            print(f"Audio file not found: {args.audio}", file=sys.stderr)
            sys.exit(1)
        user_text = transcribe_file(args.audio, api_key, args.stt_model)
    else:
        user_text = args.text

    reply = chat_complete(user_text, api_key, args.text_model)
    print(f"Assistant: {reply}")

    # Try Speech API TTS, else fallback to macOS say
    if not tts_speak(reply, api_key, args.tts_model, args.voice, args.fmt):
        mac_say(reply)


if __name__ == "__main__":
    main()


