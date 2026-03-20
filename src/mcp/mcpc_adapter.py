#!/usr/bin/env python3
"""
MCPC Adapter
============

Python interface to the MCPC canonical MCP orchestrator.

Launches the MCPC Node.js process via stdio transport and exposes an async
API that EventRelay's Python backend can call directly — no manual glue code
required.

Usage::

    from mcp.mcpc_adapter import MCPCAdapter

    adapter = MCPCAdapter()
    result = await adapter.call_tool("round_table", {
        "topic": "How should we process this video?",
        "agents": ["gemini", "claude"],
    })
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import uuid
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Path to the compiled MCPC server relative to the repo root.
_REPO_ROOT = Path(__file__).resolve().parents[3]
_MCPC_DIST = _REPO_ROOT / "mcp-servers" / "mcpc" / "dist" / "index.js"


class MCPCError(Exception):
    """Raised when the MCPC server returns an error response."""

    def __init__(self, code: int, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class MCPCAdapter:
    """
    Async adapter for the MCPC canonical MCP orchestrator.

    Launches the MCPC server as a subprocess (stdio transport) on first use
    and keeps it running for the lifetime of the adapter.  All JSON-RPC
    communication happens over the process stdin/stdout pair.
    """

    def __init__(
        self,
        server_path: str | os.PathLike[str] | None = None,
        node_binary: str = "node",
    ) -> None:
        self._server_path = Path(server_path) if server_path else _MCPC_DIST
        self._node_binary = node_binary
        self._process: asyncio.subprocess.Process | None = None
        self._pending: dict[str, asyncio.Future[Any]] = {}
        self._reader_task: asyncio.Task[None] | None = None
        self._initialized = False

    # ── Public API ─────────────────────────────────────────────────────────

    async def initialize(self) -> None:
        """Start the MCPC server and complete the MCP handshake."""
        if self._initialized:
            return

        self._process = await asyncio.create_subprocess_exec(
            self._node_binary,
            str(self._server_path),
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        # Start background reader
        self._reader_task = asyncio.create_task(self._read_loop())

        # MCP initialize handshake
        await self._send_request(
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "eventrelay-python-adapter", "version": "1.0.0"},
            },
        )
        await self._send_notification("notifications/initialized", {})
        self._initialized = True
        logger.info("[MCPCAdapter] MCPC server initialized.")

    async def list_tools(self) -> list[dict[str, Any]]:
        """Return the list of tools exposed by the MCPC server."""
        await self._ensure_initialized()
        result = await self._send_request("tools/list", {})
        return result.get("tools", [])

    async def call_tool(
        self, tool_name: str, arguments: dict[str, Any] | None = None
    ) -> Any:
        """
        Invoke a tool on the MCPC server.

        Args:
            tool_name: Name of the tool to call (e.g. ``"round_table"``).
            arguments: Tool arguments dict.

        Returns:
            The parsed content returned by the tool.

        Raises:
            MCPCError: If the server returns a JSON-RPC error.
        """
        await self._ensure_initialized()
        result = await self._send_request(
            "tools/call",
            {"name": tool_name, "arguments": arguments or {}},
        )
        # MCP tools/call returns {content: [{type, text}], isError?}
        content = result.get("content", [])
        if result.get("isError"):
            text = content[0]["text"] if content else "Unknown error"
            raise MCPCError(-1, text)
        if content:
            raw = content[0].get("text", "")
            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                return raw
        return result

    async def close(self) -> None:
        """Shut down the MCPC server process."""
        if self._reader_task:
            self._reader_task.cancel()
            try:
                await self._reader_task
            except asyncio.CancelledError:
                pass
        if self._process:
            try:
                self._process.terminate()
                await asyncio.wait_for(self._process.wait(), timeout=5)
            except Exception:
                pass
            self._process = None
        self._initialized = False
        logger.info("[MCPCAdapter] MCPC server closed.")

    # ── Context manager support ────────────────────────────────────────────

    async def __aenter__(self) -> "MCPCAdapter":
        await self.initialize()
        return self

    async def __aexit__(self, *_: Any) -> None:
        await self.close()

    # ── Internal helpers ───────────────────────────────────────────────────

    async def _ensure_initialized(self) -> None:
        if not self._initialized:
            await self.initialize()

    async def _send_request(self, method: str, params: dict[str, Any]) -> Any:
        """Send a JSON-RPC request and await the response."""
        request_id = str(uuid.uuid4())
        future: asyncio.Future[Any] = asyncio.get_event_loop().create_future()
        self._pending[request_id] = future

        message = json.dumps(
            {"jsonrpc": "2.0", "id": request_id, "method": method, "params": params}
        )
        await self._write(message)

        try:
            response = await asyncio.wait_for(future, timeout=30)
        except asyncio.TimeoutError as exc:
            self._pending.pop(request_id, None)
            raise MCPCError(-32000, f"Request timed out: {method}") from exc

        if "error" in response:
            err = response["error"]
            raise MCPCError(err.get("code", -1), err.get("message", "Unknown error"))

        return response.get("result", {})

    async def _send_notification(self, method: str, params: dict[str, Any]) -> None:
        """Send a JSON-RPC notification (no id, no response expected)."""
        message = json.dumps({"jsonrpc": "2.0", "method": method, "params": params})
        await self._write(message)

    async def _write(self, message: str) -> None:
        assert self._process and self._process.stdin
        self._process.stdin.write((message + "\n").encode())
        await self._process.stdin.drain()

    async def _read_loop(self) -> None:
        """Background task: read responses from the MCPC server stdout."""
        assert self._process and self._process.stdout
        try:
            while True:
                line = await self._process.stdout.readline()
                if not line:
                    break
                try:
                    data = json.loads(line.decode())
                    request_id = data.get("id")
                    if request_id and request_id in self._pending:
                        future = self._pending.pop(request_id)
                        if not future.done():
                            future.set_result(data)
                except json.JSONDecodeError:
                    logger.warning("[MCPCAdapter] Non-JSON stdout: %s", line[:120])
        except asyncio.CancelledError:
            pass
        except Exception as exc:
            logger.error("[MCPCAdapter] Read loop error: %s", exc)
            # Fail all pending futures
            for future in self._pending.values():
                if not future.done():
                    future.set_exception(exc)
            self._pending.clear()
