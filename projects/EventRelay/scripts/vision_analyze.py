#!/usr/bin/env python3
"""
Analyze an image using OpenAI Responses API (vision).

Usage:
  python3 scripts/vision_analyze.py <image_path_or_url> [detail]

Env:
  OPENAI_API_KEY or API_KEY_OPENAI
  OPENAI_VISION_MODEL (default: gpt-4.1-mini)

Notes:
  - Accepts a local file path or a URL. Local files are encoded as base64 data URLs.
  - Optional detail: low|high|auto (default auto)
"""
import os
import sys
import base64
import json
import requests


def is_url(s: str) -> bool:
    return s.startswith("http://") or s.startswith("https://")


def encode_image_to_data_url(path: str) -> str:
    mime = "image/jpeg"
    if path.lower().endswith(".png"):
        mime = "image/png"
    elif path.lower().endswith(".webp"):
        mime = "image/webp"
    elif path.lower().endswith(".gif"):
        mime = "image/gif"
    with open(path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")
    return f"data:{mime};base64,{b64}"


def main():
    if len(sys.argv) < 2:
        print("Usage: vision_analyze.py <image_path_or_url> [detail]")
        sys.exit(1)
    image_ref = sys.argv[1]
    detail = sys.argv[2] if len(sys.argv) > 2 else "auto"

    api_key = os.getenv("OPENAI_API_KEY") or os.getenv("API_KEY_OPENAI")
    if not api_key:
        print("OPENAI_API_KEY/API_KEY_OPENAI not set")
        sys.exit(2)

    model = os.getenv("OPENAI_VISION_MODEL", "gpt-4.1-mini")
    url = "https://api.openai.com/v1/responses"
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

    if is_url(image_ref):
        image_url = image_ref
    else:
        if not os.path.isfile(image_ref):
            print(f"File not found: {image_ref}")
            sys.exit(3)
        image_url = encode_image_to_data_url(image_ref)

    payload = {
        "model": model,
        "input": [
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": "What's in this image?"},
                    {"type": "input_image", "image_url": image_url, "detail": detail},
                ],
            }
        ],
    }

    r = requests.post(url, headers=headers, data=json.dumps(payload), timeout=120)
    r.raise_for_status()
    data = r.json()
    # Prefer output_text when available
    out = data.get("output_text")
    if out:
        print(out)
        return
    # Fallback: print raw
    print(json.dumps(data, indent=2))


if __name__ == "__main__":
    main()


