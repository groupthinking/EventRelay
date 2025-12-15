#!/usr/bin/env python3
"""
MCP wrapper server that exposes the youtube-extension API as tools.
"""
import json
import os
import sys
from typing import Any, Dict
import requests

BASE = os.getenv("YOUTUBE_EXTENSION_BASE", "http://localhost:8000")

def list_tools() -> Dict[str, Any]:
    return {
        "tools": [
            {
                "name": "process_video_markdown",
                "description": "Process a YouTube URL into a markdown guide",
                "input_schema": {"type": "object", "properties": {"video_url": {"type": "string"}, "force_regenerate": {"type": "boolean"}}, "required": ["video_url"]},
            },
            {"name": "get_markdown", "description": "Get cached markdown by video_id",
             "input_schema": {"type": "object", "properties": {"video_id": {"type": "string"}}, "required": ["video_id"]}},
            {"name": "cache_stats", "description": "Get cache stats", "input_schema": {"type": "object", "properties": {}}},
            {"name": "health", "description": "Service health", "input_schema": {"type": "object", "properties": {}}},
        ]
    }

def call_tool(name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    if name == "process_video_markdown":
        r = requests.post(f"{BASE}/api/process-video-markdown", json=arguments, timeout=120)
        return r.json()
    if name == "get_markdown":
        vid = arguments["video_id"]
        r = requests.get(f"{BASE}/api/markdown/{vid}", timeout=30)
        return r.json()
    if name == "cache_stats":
        r = requests.get(f"{BASE}/api/cache/stats", timeout=15)
        return r.json()
    if name == "health":
        r = requests.get(f"{BASE}/health", timeout=10)
        return r.json()
    raise ValueError("unknown tool")

def main():
    # Minimal stdio loop for MCP-like usage (simplified)
    for line in sys.stdin:
        req = json.loads(line)
        if req.get("method") == "tools/list":
            sys.stdout.write(json.dumps({"result": list_tools()}) + "\n"); sys.stdout.flush()
        elif req.get("method") == "tools/call":
            params = req.get("params", {})
            name = params.get("name")
            args = params.get("arguments", {})
            res = call_tool(name, args)
            sys.stdout.write(json.dumps({"result": res}) + "\n"); sys.stdout.flush()
        else:
            sys.stdout.write(json.dumps({"error": {"message": "unknown method"}}) + "\n"); sys.stdout.flush()

if __name__ == "__main__":
    main()


