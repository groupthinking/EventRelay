#!/usr/bin/env python3
"""
Minimal Orchestrator Task: Video → Process → Repo/Deploy hooks (stubs)

This script demonstrates chaining:
1) Process video via MCP youtube_learning_service
2) Generate repo scaffolding (stub hook)
3) Deploy (stub hook)
"""
import json
import subprocess
import os
from typing import Dict, Any

REG = os.path.join(os.path.dirname(__file__), "..", "src", "mcp", "mcp_registry.json")

def mcp_call(server_cmd, payload: Dict[str, Any]) -> Dict[str, Any]:
    proc = subprocess.Popen(server_cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = proc.communicate((json.dumps(payload) + "\n").encode(), timeout=60)
    if proc.returncode not in (0, None):
        raise RuntimeError(err.decode())
    lines = out.decode().strip().splitlines()
    return json.loads(lines[-1]).get("result", {})

def load_registry():
    with open(REG) as f:
        return json.load(f)

def process_video(video_url: str) -> Dict[str, Any]:
    reg = load_registry()
    yt = next(t for t in reg["tools"] if t["name"]=="youtube_learning_service")
    cmd = yt["command"]
    env = os.environ.copy(); env.update(yt.get("env", {}))
    payload = {"method":"tools/call","params":{"name":"process_video_markdown","arguments":{"video_url":video_url}}}
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
    out, err = proc.communicate((json.dumps(payload)+"\n").encode(), timeout=180)
    if proc.returncode!=0:
        raise RuntimeError(err.decode())
    return json.loads(out.decode().strip().splitlines()[-1]).get("result", {})

def repo_scaffold(result: Dict[str, Any]) -> Dict[str, Any]:
    # Stub: create repo structure
    return {"status":"ok","repo_url":"https://example.com/repo"}

def deploy(repo_info: Dict[str, Any]) -> Dict[str, Any]:
    # Stub: simulate deploy
    return {"status":"ok","url":"https://app.example.com"}

def main():
    import sys
    if len(sys.argv)<2:
        print("Usage: orchestrator_minimal.py <video_url>"); return 1
    video_url = sys.argv[1]
    res = process_video(video_url)
    print("PROCESS:", json.dumps(res)[:200])
    repo = repo_scaffold(res)
    print("REPO:", repo)
    dep = deploy(repo)
    print("DEPLOY:", dep)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())


