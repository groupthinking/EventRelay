#!/usr/bin/env python3
"""
MCPC Unified MCP Server
======================

Canonical MCP orchestrator that consolidates previously scattered MCP servers
into a single entry point for EventRelay. The server exposes a compact tool
surface that represents the merged capabilities from:
- MCPC (canonical)
- MCP_ROUND_TABLE (feature-merged)
- Mcpcserver (feature-merged)
- MCP_IOS (mobile hand-off)

Archived/stale sources are tracked for observability but not exposed as tools:
MCP-CORE, MCP-management, MESH, mcp-tools-extension.
"""

from __future__ import annotations

import asyncio
import json
import logging
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

MCP_VERSION = "2024-11-05"

logging.basicConfig(level=logging.INFO, stream=sys.stderr)
LOGGER = logging.getLogger("mcpc-unified-server")


@dataclass
class ConsolidatedCapability:
    """Represents a merged capability exposed by the unified server."""

    name: str
    origin: str
    description: str
    tags: list[str]


ARCHIVED_REPOS = [
    "MCP_ROUND_TABLE",
    "MCP-CORE",
    "MCP-management",
    "MESH",
    "mcp-tools-extension",
]

CONSOLIDATED_CAPABILITIES: dict[str, ConsolidatedCapability] = {
    "mcpc_core": ConsolidatedCapability(
        name="mcpc_core",
        origin="MCPC",
        description="Canonical MCPC toolchain (routing, registry, health).",
        tags=["canonical", "routing", "tools/list"],
    ),
    "round_table": ConsolidatedCapability(
        name="round_table",
        origin="MCP_ROUND_TABLE",
        description="Multi-agent coordination utilities now routed via MCPC.",
        tags=["coordination", "routing", "consensus"],
    ),
    "mcpcserver_legacy": ConsolidatedCapability(
        name="mcpcserver_legacy",
        origin="Mcpcserver",
        description="Legacy server behaviors wrapped for compatibility.",
        tags=["compatibility", "legacy"],
    ),
    "mcp_ios": ConsolidatedCapability(
        name="mcp_ios",
        origin="MCP_IOS",
        description="Mobile bridge for iOS flows, relocated under MCPC.",
        tags=["mobile", "handoff", "ios"],
    ),
}


class UnifiedMCPCServer:
    """Single entry-point MCP server exposing consolidated tools."""

    def __init__(self) -> None:
        self.server_info = {
            "name": "MCPC Unified Orchestrator",
            "version": "1.0.0",
            "mcpVersion": MCP_VERSION,
        }

    async def handle_request(self, request_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Handle incoming JSON-RPC requests."""
        request_id = request_data.get("id")
        method = request_data.get("method")
        params = request_data.get("params", {})

        LOGGER.info("Handling request %s (id=%s)", method, request_id)

        try:
            if method == "initialize":
                return self._handle_initialize(request_id)
            if method == "tools/list":
                return self._handle_tools_list(request_id)
            if method == "tools/call":
                return await self._handle_tools_call(request_id, params)
            if method == "notifications/initialized":
                return None

            if request_id is not None:
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {"code": -32601, "message": f"Method not found: {method}"},
                }
            return None
        except Exception as exc:  # pragma: no cover - defensive logging
            LOGGER.error("Error handling request: %s", exc, exc_info=True)
            if request_id is not None:
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {"code": -32000, "message": str(exc)},
                }
            return None

    def _handle_initialize(self, request_id: Any) -> Dict[str, Any]:
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "serverInfo": self.server_info,
                "capabilities": {"tools": {}},
            },
        }

    def _handle_tools_list(self, request_id: Any) -> Dict[str, Any]:
        tools: List[Dict[str, Any]] = [
            {
                "name": "mcpc_status",
                "description": "Return unified status, active capabilities, and archived repos.",
                "inputSchema": {"type": "object", "properties": {}},
            },
            {
                "name": "route_task",
                "description": "Route a task to a consolidated capability.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "capability": {
                            "type": "string",
                            "enum": list(CONSOLIDATED_CAPABILITIES.keys()),
                        },
                        "payload": {"type": "object"},
                        "priority": {"type": "string", "enum": ["high", "normal", "low"], "default": "normal"},
                    },
                    "required": ["capability"],
                },
            },
            {
                "name": "ios_handoff",
                "description": "Provide mobile hand-off details for iOS flows consolidated under MCPC.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "task": {"type": "string"},
                        "metadata": {"type": "object"},
                    },
                },
            },
        ]

        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {"tools": tools},
        }

    async def _handle_tools_call(self, request_id: Any, params: Dict[str, Any]) -> Dict[str, Any]:
        tool_name = params.get("name")
        arguments = params.get("arguments", {})

        if tool_name == "mcpc_status":
            result = self._tool_mcpc_status()
        elif tool_name == "route_task":
            result = self._tool_route_task(arguments)
        elif tool_name == "ios_handoff":
            result = self._tool_ios_handoff(arguments)
        else:
            raise ValueError(f"Unknown tool: {tool_name}")

        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {"content": [{"mimeType": "application/json", "text": json.dumps(result, indent=2)}]},
        }

    def _tool_mcpc_status(self) -> Dict[str, Any]:
        """Report consolidated state."""
        capabilities = [
            {
                "name": cap.name,
                "origin": cap.origin,
                "description": cap.description,
                "tags": cap.tags,
            }
            for cap in CONSOLIDATED_CAPABILITIES.values()
        ]

        return {
            "status": "ok",
            "server": self.server_info["name"],
            "capabilities": capabilities,
            "archived": ARCHIVED_REPOS,
        }

    def _tool_route_task(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        capability_key = arguments.get("capability")
        payload = arguments.get("payload", {})
        priority = arguments.get("priority", "normal")

        capability = CONSOLIDATED_CAPABILITIES.get(capability_key)
        if not capability:
            return {
                "status": "error",
                "message": f"Unknown capability '{capability_key}'.",
                "available": list(CONSOLIDATED_CAPABILITIES.keys()),
            }

        return {
            "status": "accepted",
            "routed_to": capability.name,
            "origin": capability.origin,
            "priority": priority,
            "echo": payload,
        }

    def _tool_ios_handoff(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        task = arguments.get("task", "unspecified")
        metadata = arguments.get("metadata", {})

        ios_path = Path(__file__).resolve().parent / "platforms" / "ios"
        return {
            "status": "ready",
            "task": task,
            "handoff_path": str(ios_path),
            "metadata": metadata,
        }


async def main() -> None:
    server = UnifiedMCPCServer()
    LOGGER.info("MCPC Unified MCP Server running on stdio...")

    reader = asyncio.StreamReader()
    protocol = asyncio.StreamReaderProtocol(reader)
    await asyncio.get_event_loop().connect_read_pipe(lambda: protocol, sys.stdin)

    writer: Optional[asyncio.StreamWriter]
    writer = None
    if sys.platform != "win32":
        try:
            w_transport, w_protocol = await asyncio.get_event_loop().connect_write_pipe(asyncio.Protocol, sys.stdout)
            writer = asyncio.StreamWriter(w_transport, w_protocol, None, asyncio.get_event_loop())
        except Exception as exc:  # pragma: no cover - fallback path
            LOGGER.warning("Could not bind stdout pipe (%s). Falling back to sys.stdout.write().", exc)
            writer = None
    else:
        LOGGER.info("Windows detected: using print() fallback for stdout.")

    while True:
        line = await reader.readline()
        if not line:
            break

        try:
            request = json.loads(line)
        except json.JSONDecodeError:
            LOGGER.error("Invalid JSON received: %s", line)
            continue

        response = await server.handle_request(request)
        if not response:
            continue

        response_str = json.dumps(response) + "\n"
        if writer:
            writer.write(response_str.encode())
            try:
                await writer.drain()
            except (AttributeError, BrokenPipeError):  # pragma: no cover
                LOGGER.warning("Writer drain failed; switching to print fallback.")
                writer = None
                print(response_str, flush=True)
        else:
            sys.stdout.write(response_str)
            sys.stdout.flush()


if __name__ == "__main__":
    if sys.platform == "win32":  # pragma: no cover - platform guard
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
