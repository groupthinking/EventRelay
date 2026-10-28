#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Lock
from typing import Any
from urllib.parse import quote, urlparse

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
    "test://static-text": {
        "mimeType": "text/plain",
        "text": "fixture static text",
    },
    "test://template/123/data": {
        "mimeType": "application/json",
        "text": json.dumps({"templateId": "123", "value": "fixture template data"}, sort_keys=True),
    },
}
PROMPTS = {
    "test_simple_prompt": {
        "description": "Return a deterministic fixture prompt.",
        "arguments": [{"name": "video_id", "required": False}],
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
APPROVAL_ID_PATTERN = re.compile(r"^[A-Za-z0-9_.:-]{1,128}$")
OPERATOR_PROVENANCE_PATTERN = re.compile(r"^operator:[A-Za-z0-9_.-]{1,64}$")
SCOPE_TOKEN_PATTERN = re.compile(r"^[A-Za-z0-9:._/-]{1,256}$")


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


def _quoted_header_value(value: str) -> str:
    return _safe_header_part(value).replace("\\", "\\\\").replace('"', '\\"')


def _immutable_snapshot(value: dict[str, Any]) -> dict[str, Any]:
    return json.loads(json.dumps(value, sort_keys=True))


class ConformanceFixtureHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    _handler_runs: dict[str, int] = {}
    _scope_receipts: list[dict[str, Any]] = []
    _state_lock = Lock()

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

        if not isinstance(payload, dict):
            self._write_json(
                HTTPStatus.BAD_REQUEST,
                _jsonrpc_error(None, -32600, "Invalid Request"),
            )
            return

        request_id = payload.get("id")
        method = payload.get("method")
        params = payload.get("params") or {}
        if not isinstance(params, dict):
            self._write_json(
                HTTPStatus.BAD_REQUEST,
                _jsonrpc_error(request_id, -32602, "Invalid params"),
            )
            return
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
                        "capabilities": {"tools": {}, "resources": {}, "prompts": {}},
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
                        "capabilities": {"tools": {}, "resources": {}, "prompts": {}},
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
                _jsonrpc_result(request_id, {"receipts": self._receipt_snapshot()}),
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
        with self._state_lock:
            count = self._handler_runs.get(operation_key, 0) + 1
            self._handler_runs[operation_key] = count
            receipt = {
                **scope_context["receipt"],
                "decision": "approved",
                "retry_result": "success",
                "handler_ran": True,
                "handlerRunCount": count,
            }
            immutable_receipt = _immutable_snapshot(receipt)
            self._scope_receipts.append(immutable_receipt)
        return {"scopeStepUp": immutable_receipt}

    def _scope_context(
        self, *, request_id: Any, method: Any, params: dict[str, Any]
    ) -> dict[str, Any] | bool | None:
        if not self._scope_step_up_enabled():
            return None
        operation = str(method or "")
        if operation not in {"tools/call", "resources/read", "prompts/get"}:
            return None

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

        encoded_target = quote(target, safe="")
        metadata_url = f"https://eventrelay.local/mcp/metadata/{quote(operation, safe='')}/{encoded_target}"
        resource_metadata = {
            "resource_metadata_url": metadata_url,
            "resource": target,
        }
        required_scopes = self._required_scopes(operation=operation, target=target)
        prior_scopes = self._granted_scopes()
        if prior_scopes is None:
            return self._deny_scope(
                request_id=request_id,
                operation=operation,
                target=target,
                reason="malformed_scope_set",
                challenged_scopes=tuple(required_scopes),
                resource_metadata=resource_metadata,
            )

        provenance = str(self.headers.get("X-EventRelay-Approval-Provenance", "") or "")
        receipt = {
            "call_id": request_id,
            "operation": operation,
            "target": target,
            "prior_scopes": prior_scopes,
            "challenged_scopes": required_scopes,
            "resource_metadata": resource_metadata,
            "approval_provenance": provenance or None,
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

        approval_binding, rejection_reason = self._approval_binding(
            operation=operation,
            target=target,
            required_scopes=required_scopes,
            metadata_url=metadata_url,
        )
        if approval_binding is None:
            return self._deny_scope(
                request_id=request_id,
                operation=operation,
                target=target,
                reason=rejection_reason,
                challenged_scopes=tuple(required_scopes),
                resource_metadata=resource_metadata,
                receipt=receipt,
            )
        receipt["approval_binding"] = approval_binding
        receipt["approval_provenance"] = approval_binding["provenance"]
        return {"operation_key": f"{operation}:{target}", "receipt": receipt}

    def _approval_binding(
        self,
        *,
        operation: str,
        target: str,
        required_scopes: list[str],
        metadata_url: str,
    ) -> tuple[dict[str, Any] | None, str]:
        provenance = str(self.headers.get("X-EventRelay-Approval-Provenance", "") or "")
        approval_id = str(self.headers.get("X-EventRelay-Approval-Id", "") or "")
        bound_operation = str(self.headers.get("X-EventRelay-Approval-Operation", "") or "")
        bound_target = str(self.headers.get("X-EventRelay-Approval-Target", "") or "")
        bound_metadata = str(self.headers.get("X-EventRelay-Approval-Resource-Metadata", "") or "")
        bound_scopes = self._parse_scope_header("X-EventRelay-Approval-Scopes")
        state = str(self.headers.get("X-EventRelay-Approval-State", "") or "")
        expires_at_raw = str(self.headers.get("X-EventRelay-Approval-Expires-At", "") or "")

        if not OPERATOR_PROVENANCE_PATTERN.fullmatch(provenance):
            return None, "invalid_provenance"
        if not APPROVAL_ID_PATTERN.fullmatch(approval_id):
            return None, "invalid_approval_id"
        if bound_operation != operation or bound_target != target:
            return None, "approval_binding_mismatch"
        if bound_metadata != metadata_url:
            return None, "resource_metadata_mismatch"
        if bound_scopes is None or bound_scopes != sorted(required_scopes):
            return None, "approval_scope_mismatch"
        if state != "active":
            return None, "approval_revoked" if state == "revoked" else "approval_inactive"
        try:
            expires_at = int(expires_at_raw)
        except ValueError:
            return None, "invalid_approval_expiry"
        if expires_at <= int(time.time()):
            return None, "approval_expired"

        return {
            "approval_id": approval_id,
            "provenance": provenance,
            "operation": operation,
            "target": target,
            "scope_set": sorted(required_scopes),
            "resource_metadata_url": metadata_url,
            "expires_at": expires_at,
            "revocation_state": state,
        }, ""

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
        prior_scopes = self._granted_scopes() or []
        denial_receipt = {
            "call_id": request_id,
            "operation": operation,
            "target": target,
            "prior_scopes": prior_scopes,
            "challenged_scopes": list(challenged_scopes),
            "resource_metadata": resource_metadata,
            "approval_provenance": str(
                self.headers.get("X-EventRelay-Approval-Provenance", "") or ""
            )
            or None,
            "decision": "challenge" if reason == "insufficient_scope" else "rejected",
            "retry_result": "not_attempted",
            "handler_ran": False,
            "reason": reason,
        }
        if receipt:
            denial_receipt = {**receipt, **denial_receipt}
        self._append_receipt(denial_receipt)
        headers = {"MCP-Protocol-Version": "2026-07-28"}
        if reason == "insufficient_scope":
            scope_value = _quoted_header_value(" ".join(challenged_scopes))
            metadata_url = _quoted_header_value(
                resource_metadata.get("resource_metadata_url", "about:blank")
            )
            headers["WWW-Authenticate"] = (
                f'Bearer error="insufficient_scope", scope="{scope_value}", '
                f'resource_metadata="{metadata_url}"'
            )
        message = (
            "insufficient_scope"
            if reason == "insufficient_scope"
            else "authorization_rejected"
        )
        payload = _jsonrpc_error(request_id, -32003, message)
        payload["error"]["data"] = _immutable_snapshot(denial_receipt)
        self._write_json(
            HTTPStatus.FORBIDDEN,
            payload,
            headers=headers,
        )
        return False

    def _append_receipt(self, receipt: dict[str, Any]) -> None:
        with self._state_lock:
            self._scope_receipts.append(_immutable_snapshot(receipt))

    def _receipt_snapshot(self) -> list[dict[str, Any]]:
        with self._state_lock:
            return [_immutable_snapshot(receipt) for receipt in self._scope_receipts]

    def _scope_step_up_enabled(self) -> bool:
        return os.getenv(SCOPE_STEP_UP_FLAG, "").lower() in {"1", "true", "yes", "on"}

    def _parse_scope_header(self, name: str) -> list[str] | None:
        raw_value = str(self.headers.get(name, "") or "")
        values = sorted({part.strip() for part in raw_value.split(" ") if part.strip()})
        if any(not SCOPE_TOKEN_PATTERN.fullmatch(value) for value in values):
            return None
        return values

    def _granted_scopes(self) -> list[str] | None:
        return self._parse_scope_header("X-EventRelay-Fixture-Scopes")

    def _canonical_target(self, *, operation: str, params: dict[str, Any]) -> str | None:
        if operation == "tools/call":
            name = params.get("name")
            arguments = params.get("arguments", {})
            if not isinstance(arguments, dict):
                return None
            return name if isinstance(name, str) and TARGET_NAME_PATTERN.fullmatch(name) else None
        if operation == "resources/read":
            uri = params.get("uri")
            if not isinstance(uri, str) or uri not in RESOURCES:
                return None
            parsed = urlparse(uri)
            if parsed.scheme != "test" or not parsed.netloc:
                return None
            return uri
        if operation == "prompts/get":
            name = params.get("name")
            arguments = params.get("arguments", {})
            if not isinstance(arguments, dict):
                return None
            if not isinstance(name, str) or name not in PROMPTS:
                return None
            return name
        return None

    def _required_scopes(self, *, operation: str, target: str) -> list[str]:
        if operation == "tools/call":
            return [
                "mcp:conformance:tools:call",
                f"mcp:conformance:tools:{target}",
            ]
        if operation == "resources/read":
            resource_scope = (
                "mcp:conformance:resources:static"
                if target == "test://static-text"
                else "mcp:conformance:resources:template:123"
            )
            return ["mcp:conformance:resources:read", resource_scope]
        if operation == "prompts/get":
            return [
                "mcp:conformance:prompts:get",
                "mcp:conformance:prompts:test_simple_prompt",
            ]
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
