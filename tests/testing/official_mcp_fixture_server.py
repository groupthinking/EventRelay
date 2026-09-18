#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import urlparse

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
    {
        "name": "test_primitives",
        "description": "Return deterministic primitive fixtures for testing.",
        "inputSchema": {"type": "object", "properties": {}},
    },
]
RESOURCES = {
    "resource://fixtures/static/text": {
        "mimeType": "text/plain",
        "text": "fixture static text",
    },
    "resource://fixtures/static/json": {
        "mimeType": "application/json",
        "text": json.dumps(
            {
                "string": "value",
                "number": 7,
                "boolean": True,
                "array": [1, "two", False],
                "object": {"nested": "ok"},
                "null": None,
            },
            sort_keys=True,
        ),
    },
}
PROMPTS = {
    "summarize_video": {
        "description": "Summarize a video fixture prompt.",
        "arguments": [{"name": "video_id", "required": True}],
    }
}

SERVER_INFO = {"name": "eventrelay-conformance-fixture", "version": "1.0.0"}
STATELESS_RESULT_META = {
    "resultType": "complete",
    "ttlMs": 0,
    "cacheScope": "private",
}
ALLOWED_PROTOCOL_VERSIONS = {"2025-11-25", "2026-07-28"}
SCOPE_STEP_UP_FLAG = "EVENTRELAY_FIXTURE_SCOPE_STEP_UP"
TARGET_NAME_PATTERN = re.compile(r"^[A-Za-z0-9_:-]{1,128}$")


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
    _handler_runs: dict[str, int] = {}
    _scope_receipts: list[dict[str, Any]] = []

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
        scope_context = self._scope_context(request_id=request_id, method=method, params=params)
        if scope_context is False:
            return

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

        if method == "resources/read":
            uri = str(params.get("uri") or "")
            resource = RESOURCES.get(uri)
            if resource is None:
                self._write_json(
                    HTTPStatus.NOT_FOUND,
                    _jsonrpc_error(request_id, -32602, "Resource not found"),
                    headers={"MCP-Protocol-Version": "2026-07-28"},
                )
                return
            self._write_json(
                HTTPStatus.OK,
                _stateless_result(
                    request_id,
                    {
                        "contents": [
                            {
                                "uri": uri,
                                "mimeType": resource["mimeType"],
                                "text": resource["text"],
                            }
                        ],
                        **self._approved_scope_payload(scope_context),
                    },
                ),
                headers={"MCP-Protocol-Version": "2026-07-28"},
            )
            return

        if method == "prompts/get":
            name = str(params.get("name") or "")
            prompt = PROMPTS.get(name)
            if prompt is None:
                self._write_json(
                    HTTPStatus.NOT_FOUND,
                    _jsonrpc_error(request_id, -32602, "Prompt not found"),
                    headers={"MCP-Protocol-Version": "2026-07-28"},
                )
                return
            video_id = str((params.get("arguments") or {}).get("video_id") or "unknown")
            self._write_json(
                HTTPStatus.OK,
                _stateless_result(
                    request_id,
                    {
                        "description": prompt["description"],
                        "messages": [
                            {
                                "role": "user",
                                "content": {
                                    "type": "text",
                                    "text": f"Summarize video {video_id} with verified evidence only.",
                                },
                            }
                        ],
                        **self._approved_scope_payload(scope_context),
                    },
                ),
                headers={"MCP-Protocol-Version": "2026-07-28"},
            )
            return

        if method == "fixtures/receipts/list":
            self._write_json(
                HTTPStatus.OK,
                _jsonrpc_result(request_id, {"receipts": list(self._scope_receipts)}),
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
                            ],
                            **self._approved_scope_payload(scope_context),
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
                            **self._approved_scope_payload(scope_context),
                        },
                    ),
                    headers={"MCP-Protocol-Version": "2026-07-28"},
                )
                return
            if tool_name == "test_primitives":
                self._write_json(
                    HTTPStatus.OK,
                    _stateless_result(
                        request_id,
                        {
                            "content": [
                                {
                                    "type": "text",
                                    "text": json.dumps(
                                        {
                                            "string": "value",
                                            "number": 7,
                                            "boolean": True,
                                            "array": [1, "two", False],
                                            "object": {"nested": "ok"},
                                            "null": None,
                                        },
                                        sort_keys=True,
                                    ),
                                }
                            ],
                            **self._approved_scope_payload(scope_context),
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

    def _approved_scope_payload(
        self, scope_context: dict[str, Any] | None
    ) -> dict[str, Any]:
        if not scope_context:
            return {}
        operation_key = str(scope_context["operation_key"])
        count = self._handler_runs.get(operation_key, 0) + 1
        self._handler_runs[operation_key] = count
        receipt = {
            **scope_context["receipt"],
            "decision": "approved",
            "retry_result": "success",
            "handler_ran": True,
            "handlerRunCount": count,
        }
        self._scope_receipts.append(dict(receipt))
        return {"scopeStepUp": receipt}

    def _scope_context(
        self, *, request_id: Any, method: Any, params: dict[str, Any]
    ) -> dict[str, Any] | bool | None:
        if not self._scope_step_up_enabled():
            return None
        operation = str(method or "")
        if operation not in {"tools/call", "resources/read", "prompts/get"}:
            return None

        provenance = str(self.headers.get("X-EventRelay-Approval-Provenance", "") or "")
        if provenance.lower().startswith("peer-agent:"):
            return self._deny_scope(
                request_id=request_id,
                operation=operation,
                target="<unknown>",
                reason="invalid_provenance",
                challenged_scopes=(),
                resource_metadata={"resource_metadata_url": "about:blank"},
            )

        target = self._canonical_target(operation=operation, params=params)
        if target is None:
            return self._deny_scope(
                request_id=request_id,
                operation=operation,
                target="<invalid>",
                reason="malformed_target",
                challenged_scopes=(),
                resource_metadata={"resource_metadata_url": "about:blank"},
            )

        resource_metadata = {
            "resource_metadata_url": f"https://eventrelay.local/mcp/metadata/{operation}/{target}",
            "resource": target,
        }
        required_scopes = self._required_scopes(operation=operation, target=target)
        prior_scopes = self._granted_scopes()
        receipt = {
            "call_id": request_id,
            "operation": operation,
            "target": target,
            "prior_scopes": prior_scopes,
            "challenged_scopes": required_scopes,
            "resource_metadata": resource_metadata,
            "approval_provenance": provenance or "operator:fixture",
            "retry_result": "not_attempted",
            "handler_ran": False,
        }
        if not set(required_scopes).issubset(set(prior_scopes)):
            return self._deny_scope(
                request_id=request_id,
                operation=operation,
                target=target,
                reason="insufficient_scope",
                challenged_scopes=tuple(required_scopes),
                resource_metadata=resource_metadata,
                receipt=receipt,
            )
        return {"operation_key": f"{operation}:{target}", "receipt": receipt}

    def _deny_scope(
        self,
        *,
        request_id: Any,
        operation: str,
        target: str,
        reason: str,
        challenged_scopes: tuple[str, ...],
        resource_metadata: dict[str, str],
        receipt: dict[str, Any] | None = None,
    ) -> bool:
        prior_scopes = self._granted_scopes()
        denial_receipt = {
            "call_id": request_id,
            "operation": operation,
            "target": target,
            "prior_scopes": prior_scopes,
            "challenged_scopes": list(challenged_scopes),
            "resource_metadata": resource_metadata,
            "approval_provenance": str(
                self.headers.get("X-EventRelay-Approval-Provenance", "") or "operator:fixture"
            ),
            "decision": "challenge" if reason == "insufficient_scope" else "rejected",
            "retry_result": "not_attempted",
            "handler_ran": False,
            "reason": reason,
        }
        if receipt:
            denial_receipt = {**receipt, **denial_receipt}
        self._scope_receipts.append(dict(denial_receipt))
        headers = {"MCP-Protocol-Version": "2026-07-28"}
        if reason == "insufficient_scope":
            scope_value = " ".join(challenged_scopes)
            metadata_url = resource_metadata.get("resource_metadata_url", "about:blank")
            auth_scheme = "Bearer"
            headers["WWW-Authenticate"] = (
                f'{auth_scheme} error="insufficient_scope", scope="{scope_value}", '
                f'resource_metadata="{metadata_url}"'
            )
        message = (
            "insufficient_scope"
            if reason == "insufficient_scope"
            else "authorization_rejected"
        )
        payload = _jsonrpc_error(request_id, -32003, message)
        payload["error"]["data"] = denial_receipt
        self._write_json(
            HTTPStatus.FORBIDDEN,
            payload,
            headers=headers,
        )
        return False

    def _scope_step_up_enabled(self) -> bool:
        return os.getenv(SCOPE_STEP_UP_FLAG, "").lower() in {"1", "true", "yes", "on"}

    def _granted_scopes(self) -> list[str]:
        scopes = str(self.headers.get("X-EventRelay-Fixture-Scopes", "") or "")
        values = sorted({part.strip() for part in scopes.split(" ") if part.strip()})
        return values

    def _canonical_target(self, *, operation: str, params: dict[str, Any]) -> str | None:
        if operation == "tools/call":
            name = str(params.get("name") or "")
            return name if TARGET_NAME_PATTERN.fullmatch(name) else None
        if operation == "resources/read":
            uri = str(params.get("uri") or "")
            if "\n" in uri or "\r" in uri:
                return None
            parsed = urlparse(uri)
            if not parsed.scheme or not parsed.netloc:
                return None
            return uri
        if operation == "prompts/get":
            name = str(params.get("name") or "")
            return name if TARGET_NAME_PATTERN.fullmatch(name) else None
        return None

    def _required_scopes(self, *, operation: str, target: str) -> list[str]:
        if operation == "tools/call":
            return ["mcp:tools:call", f"tool:{target}:execute"]
        if operation == "resources/read":
            return ["mcp:resources:read", f"resource:{target}:read"]
        if operation == "prompts/get":
            return ["mcp:prompts:get", f"prompt:{target}:read"]
        return []


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
