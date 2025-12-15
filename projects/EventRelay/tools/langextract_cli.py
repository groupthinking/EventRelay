#!/usr/bin/env python3
"""
Minimal LangExtract CLI

Reads a single JSON object on stdin with either:
  {"source_url": "https://..."} or {"raw_text": "..."}
Writes JSON to stdout: {"text": str, "code_blocks": [ {"language": str, "code": str} ]}

This is a lightweight, dependency-free extractor intended as a fallback.
"""
import sys
import json
import re
from typing import Dict, Any, List

def fetch_url(url: str) -> str:
    import requests  # use requests if available in env
    r = requests.get(url, timeout=20)
    r.raise_for_status()
    return r.text

def html_to_text(html: str) -> str:
    # Remove scripts/styles
    html = re.sub(r"<script[\s\S]*?</script>", " ", html, flags=re.I)
    html = re.sub(r"<style[\s\S]*?</style>", " ", html, flags=re.I)
    # Convert breaks/paras to newlines
    html = re.sub(r"<(br|p|div|li|h[1-6])[^>]*>", "\n", html, flags=re.I)
    # Strip tags
    text = re.sub(r"<[^>]+>", " ", html)
    # Collapse whitespace
    text = re.sub(r"\s+", " ", text).strip()
    return text

def extract_from_input(inp: Dict[str, Any]) -> Dict[str, Any]:
    code_blocks: List[Dict[str, str]] = []
    if "raw_text" in inp and inp["raw_text"]:
        return {"text": inp["raw_text"], "code_blocks": code_blocks}
    if "source_url" in inp and inp["source_url"]:
        html = fetch_url(inp["source_url"])
        text = html_to_text(html)
        return {"text": text, "code_blocks": code_blocks}
    return {"text": "", "code_blocks": code_blocks}

def main():
    raw = sys.stdin.read()
    try:
        data = json.loads(raw or "{}")
    except Exception:
        print(json.dumps({"text": "", "code_blocks": []}))
        return
    res = extract_from_input(data)
    print(json.dumps(res))

if __name__ == "__main__":
    main()


