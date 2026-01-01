#!/usr/bin/env python3
"""
LangExtract MCP Wrapper (minimal)

Supports tools:
- extract: { source_url?: string, raw_text?: string } -> { text: string, code_blocks: [ {language, code} ] }
- health: {} -> { status: string }

Backends supported (priority order):
1) HTTP service via LANGEXTRACT_BASE (expects POST /extract {source_url|raw_text})
2) Local CLI via LANGEXTRACT_CLI (executable path)

If neither backend is available, returns an error result.
"""
import json
import os
import sys
from typing import Any, Dict
import subprocess

def list_tools() -> Dict[str, Any]:
    return {
        "tools": [
            {
                "name": "extract",
                "description": "Extract language/text and code blocks from a URL or raw text",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "source_url": {"type": "string"},
                        "raw_text": {"type": "string"}
                    },
                    "anyOf": [
                        {"required": ["source_url"]},
                        {"required": ["raw_text"]}
                    ]
                }
            },
            {
                "name": "health",
                "description": "LangExtract wrapper health",
                "input_schema": {"type": "object", "properties": {}}
            }
        ]
    }

def _extract_via_http(arguments: Dict[str, Any]):
    import requests
    base = os.getenv("LANGEXTRACT_BASE")
    if not base:
        return None
    r = requests.post(f"{base.rstrip('/')}/extract", json=arguments, timeout=60)
    if r.status_code != 200:
        raise RuntimeError(f"LangExtract HTTP {r.status_code}: {r.text[:200]}")
    return r.json()

def _extract_via_cli(arguments: Dict[str, Any]):
    cli = os.getenv("LANGEXTRACT_CLI")
    if not cli:
        return None
    payload = json.dumps(arguments)
    proc = subprocess.run([cli, "--json"], input=payload.encode(), capture_output=True, timeout=60)
    if proc.returncode != 0:
        raise RuntimeError(f"LangExtract CLI failed: {proc.stderr.decode()[:200]}")
    return json.loads(proc.stdout.decode())

def call_tool(name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    if name == "health":
        status = "unconfigured"
        if os.getenv("LANGEXTRACT_BASE") or os.getenv("LANGEXTRACT_CLI"):
            status = "configured"
        return {"status": status}
    if name == "extract":
        # Try HTTP first, then CLI
        try:
            res = _extract_via_http(arguments)
            if res is None:
                res = _extract_via_cli(arguments)
            if res is None:
                raise RuntimeError("LangExtract backend not configured (set LANGEXTRACT_BASE or LANGEXTRACT_CLI)")
            # Normalize response
            text = res.get("text", "")
            code_blocks = res.get("code_blocks", [])
            return {"text": text, "code_blocks": code_blocks}
        except Exception as e:
            return {"error": str(e)}
    raise ValueError("unknown tool")

def main():
    for line in sys.stdin:
        if not line.strip():
            continue
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


