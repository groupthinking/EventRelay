#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

TOOLS = [
    {
        "name": "test_simple_text",
        "description": "Return a simple text response for conformance testing.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "test_error_handling",
        "description": "Return a tool error response for conformance testing.",
        "inputSchema": {"type": "object", "properties": {}},
    },
]

SERVER_INFO = {"name": "eventrelay-conformance-fixture", "version": "1.0.0"}
STATELESS_RESULT_META = {
    "resultType": "complete",
    "ttlMs": 0,
    "cacheScope": "private",
}
ALLOWED_PROTOCOL_VERSIONS = {"2025-11-25", "2026-07-28"}


def _jsonrpc_result(request_id: Any, result: dict[str, Any]) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def _jsonrpc_error(
    request_id: Any,
    code: int,
    message: str,
) -> dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {"code": code, "message": message},
    }


def _stateless_result(request_id: Any, result: dict[str, Any]) -> dict[str, Any]:
    return _jsonrpc_result(request_id, {**STATELESS_RESULT_META, **result})


def _normalize_protocol_version(value: Any) -> str:
    if isinstance(value, str) and value in ALLOWED_PROTOCOL_VERSIONS:
        return value
    return "2025-11-25"


def _safe_header_part(value: str) -> str:
    if "\r" in value or "\n" in value:
        raise ValueError("invalid header value")
    return value


class ConformanceFixtureHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/mcp":
            self._write_json(
                HTTPStatus.NOT_FOUND,
                _jsonrpc_error(None, -32601, "Method not found"),
            )
            return

        payload = self._read_json()
        if payload is None:
            self._write_json(
                HTTPStatus.BAD_REQUEST,
                _jsonrpc_error(None, -32700, "Parse error"),
            )
            return

        request_id = payload.get("id")
        method = payload.get("method")
        params = payload.get("params") or {}

        if request_id is None and str(method).startswith("notifications/"):
            self.send_response(HTTPStatus.ACCEPTED)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return

        if method == "initialize":
            protocol_version = _normalize_protocol_version(params.get("protocolVersion"))
            self._write_json(
                HTTPStatus.OK,
                _jsonrpc_result(
                    request_id,
                    {
                        "protocolVersion": protocol_version,
                        "capabilities": {"tools": {}},
                        "serverInfo": SERVER_INFO,
                    },
                ),
                headers={"MCP-Protocol-Version": protocol_version},
            )
            return

        if method == "server/discover":
            self._write_json(
                HTTPStatus.OK,
                _stateless_result(
                    request_id,
                    {
                        "supportedVersions": ["2026-07-28"],
                        "capabilities": {"tools": {}},
                        "serverInfo": SERVER_INFO,
                    },
                ),
                headers={"MCP-Protocol-Version": "2026-07-28"},
            )
            return

        if method == "tools/list":
            self._write_json(
                HTTPStatus.OK,
                _stateless_result(request_id, {"tools": TOOLS}),
                headers={"MCP-Protocol-Version": "2026-07-28"},
            )
            return

        if method == "tools/call":
            tool_name = params.get("name")
            if tool_name == "test_simple_text":
                self._write_json(
                    HTTPStatus.OK,
                    _stateless_result(
                        request_id,
                        {
                            "content": [
                                {
                                    "type": "text",
                                    "text": "This is a simple text response for testing.",
                                }
                            ]
                        },
                    ),
                    headers={"MCP-Protocol-Version": "2026-07-28"},
                )
                return
            if tool_name == "test_error_handling":
                self._write_json(
                    HTTPStatus.OK,
                    _stateless_result(
                        request_id,
                        {
                            "isError": True,
                            "content": [
                                {
                                    "type": "text",
                                    "text": "This tool intentionally returns an error for testing",
                                }
                            ],
                        },
                    ),
                    headers={"MCP-Protocol-Version": "2026-07-28"},
                )
                return

        self._write_json(
            HTTPStatus.NOT_FOUND,
            _jsonrpc_error(request_id, -32601, "Method not found"),
        )

    def do_GET(self) -> None:  # noqa: N802
        self._write_json(
            HTTPStatus.METHOD_NOT_ALLOWED,
            _jsonrpc_error(None, -32000, "Method not allowed."),
        )

    def do_DELETE(self) -> None:  # noqa: N802
        self._write_json(
            HTTPStatus.METHOD_NOT_ALLOWED,
            _jsonrpc_error(None, -32000, "Method not allowed."),
        )

    def log_message(self, _format: str, *_args: Any) -> None:
        return

    def _read_json(self) -> dict[str, Any] | None:
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            return None
        body = self.rfile.read(length) if length > 0 else b""
        try:
            return json.loads(body.decode("utf-8")) if body else {}
        except json.JSONDecodeError:
            return None

    def _write_json(
        self,
        status: HTTPStatus,
        payload: dict[str, Any],
        *,
        headers: dict[str, str] | None = None,
    ) -> None:
        encoded = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        for name, value in (headers or {}).items():
            self.send_header(_safe_header_part(name), _safe_header_part(value))
        self.end_headers()
        self.wfile.write(encoded)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=38765)
    args = parser.parse_args()
    server = ThreadingHTTPServer(("127.0.0.1", args.port), ConformanceFixtureHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
