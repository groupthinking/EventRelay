#!/usr/bin/env python3
"""
LiquidAI LFM2-VL MCP Server

Wraps the public LFM2-VL HuggingFace Space endpoint as a local MCP server so
that the EventRelay agent network can route tasks to LFM2-VL alongside the
existing providers (Gemini, Claude, Grok, OpenAI).

Reference URLs
--------------
  WebGPU demo  : https://liquidai-lfm2-vl-webgpu.static.hf.space
  MCP endpoint : https://liquidai-lfm2-mcp.static.hf.space
  HF Space     : https://huggingface.co/spaces/LiquidAI/LFM2-VL-WebGPU

Usage
-----
  python mcp-servers/liquidai-lfm2/server.py

Environment variables
---------------------
  LIQUIDAI_API_KEY   – Optional bearer token for authenticated deployments.
  LFM2_MCP_BASE_URL  – Override the upstream MCP server URL (default above).
  LFM2_MAX_TOKENS    – Default max tokens for generation (default: 512).
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
from typing import Any

import httpx

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("liquidai-lfm2-mcp")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

LFM2_MCP_BASE_URL: str = os.environ.get(
    "LFM2_MCP_BASE_URL", "https://liquidai-lfm2-mcp.static.hf.space"
)
LIQUIDAI_API_KEY: str | None = os.environ.get("LIQUIDAI_API_KEY")
LFM2_MAX_TOKENS: int = int(os.environ.get("LFM2_MAX_TOKENS", "512"))

# ---------------------------------------------------------------------------
# JSON-RPC helpers
# ---------------------------------------------------------------------------


def _ok(request_id: Any, result: Any) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def _err(request_id: Any, code: int, message: str) -> dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {"code": code, "message": message},
    }


# ---------------------------------------------------------------------------
# Tool definitions
# ---------------------------------------------------------------------------

TOOLS = [
    {
        "name": "generate_text",
        "description": "Generate text using LiquidAI LFM2-VL",
        "inputSchema": {
            "type": "object",
            "properties": {
                "prompt": {"type": "string", "description": "Text prompt"},
                "system": {"type": "string", "description": "Optional system prompt"},
                "max_tokens": {"type": "integer", "default": LFM2_MAX_TOKENS},
                "temperature": {"type": "number", "default": 0.7},
            },
            "required": ["prompt"],
        },
    },
    {
        "name": "analyze_vision",
        "description": "Analyse an image using LFM2-VL vision capabilities",
        "inputSchema": {
            "type": "object",
            "properties": {
                "prompt": {"type": "string", "description": "Question about the image"},
                "image": {
                    "type": "string",
                    "description": "Base-64 encoded image data or a public image URL",
                },
                "max_tokens": {"type": "integer", "default": LFM2_MAX_TOKENS},
            },
            "required": ["prompt", "image"],
        },
    },
    {
        "name": "chat_completion",
        "description": "Multi-turn chat with LFM2-VL",
        "inputSchema": {
            "type": "object",
            "properties": {
                "messages": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "role": {
                                "type": "string",
                                "enum": ["user", "assistant", "system"],
                            },
                            "content": {"type": "string"},
                        },
                        "required": ["role", "content"],
                    },
                },
                "max_tokens": {"type": "integer", "default": LFM2_MAX_TOKENS},
                "temperature": {"type": "number", "default": 0.7},
            },
            "required": ["messages"],
        },
    },
]


# ---------------------------------------------------------------------------
# Upstream proxy helper
# ---------------------------------------------------------------------------


async def _proxy_to_lfm2(tool_name: str, arguments: dict[str, Any]) -> str:
    """Forward a tool call to the upstream LFM2 MCP endpoint."""
    headers: dict[str, str] = {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    if LIQUIDAI_API_KEY:
        headers["Authorization"] = f"Bearer {LIQUIDAI_API_KEY}"

    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {"name": tool_name, "arguments": arguments},
    }

    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            f"{LFM2_MCP_BASE_URL}/mcp",
            headers=headers,
            json=payload,
        )
        resp.raise_for_status()
        data = resp.json()

    if "error" in data:
        err = data["error"]
        raise RuntimeError(f"LFM2 error {err.get('code')}: {err.get('message')}")

    result = data.get("result", {})
    # Unwrap MCP content list if present
    if isinstance(result, dict):
        content = result.get("content", [])
        if isinstance(content, list) and content:
            first = content[0]
            if isinstance(first, dict):
                return first.get("text", str(result))
        return result.get("text", str(result))
    return str(result)


# ---------------------------------------------------------------------------
# Request handler
# ---------------------------------------------------------------------------


async def handle_request(request: dict[str, Any]) -> dict[str, Any]:
    """Dispatch a single JSON-RPC 2.0 request and return the response."""
    req_id = request.get("id")
    method = request.get("method", "")
    params = request.get("params", {})

    try:
        if method == "initialize":
            return _ok(
                req_id,
                {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "serverInfo": {
                        "name": "liquidai-lfm2-mcp",
                        "version": "1.0.0",
                        "description": (
                            "LiquidAI LFM2-VL MCP server – proxy to "
                            + LFM2_MCP_BASE_URL
                        ),
                    },
                },
            )

        if method == "tools/list":
            return _ok(req_id, {"tools": TOOLS})

        if method == "tools/call":
            tool_name: str = params.get("name", "")
            arguments: dict[str, Any] = params.get("arguments", {})
            valid_names = {t["name"] for t in TOOLS}
            if tool_name not in valid_names:
                return _err(req_id, -32602, f"Unknown tool: {tool_name}")

            logger.info("Calling LFM2 tool '%s'", tool_name)
            text = await _proxy_to_lfm2(tool_name, arguments)
            return _ok(
                req_id,
                {"content": [{"type": "text", "text": text}]},
            )

        return _err(req_id, -32601, f"Method not found: {method}")

    except Exception as exc:  # noqa: BLE001
        logger.error("Error handling request: %s", exc)
        return _err(req_id, -32603, str(exc))


# ---------------------------------------------------------------------------
# Stdio transport (MCP standard)
# ---------------------------------------------------------------------------


async def run_stdio() -> None:
    """Run an MCP stdio server reading/writing newline-delimited JSON."""
    logger.info(
        "LiquidAI LFM2-VL MCP server started (upstream: %s)", LFM2_MCP_BASE_URL
    )
    reader = asyncio.StreamReader()
    proto = asyncio.StreamReaderProtocol(reader)
    loop = asyncio.get_event_loop()
    await loop.connect_read_pipe(lambda: proto, sys.stdin)

    transport, _ = await loop.connect_write_pipe(asyncio.BaseProtocol, sys.stdout)

    while True:
        try:
            line = await reader.readline()
        except (EOFError, asyncio.IncompleteReadError):
            break
        if not line:
            break
        line = line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
        except json.JSONDecodeError as exc:
            response = _err(None, -32700, f"Parse error: {exc}")
            transport.write((json.dumps(response) + "\n").encode())
            continue

        response = await handle_request(request)
        transport.write((json.dumps(response) + "\n").encode())


if __name__ == "__main__":
    asyncio.run(run_stdio())
