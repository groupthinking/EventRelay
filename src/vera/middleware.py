"""
VERA FastAPI Middleware — HTTP-level integration for the input firewall.

Scans incoming request bodies for prompt injection patterns before they
reach any endpoint handler. In "enforce" mode, malicious requests are
rejected with 403. In "monitor" mode, threats are logged but allowed.

Also provides a VERA status endpoint at /vera/status for health checks.

Usage in main.py:
    from vera.middleware import VeraFirewallMiddleware
    app.add_middleware(VeraFirewallMiddleware)
"""

import json
import logging
import time
from typing import Optional

from .config import get_vera_config
from .firewall import FirewallAction, InputFirewall, get_firewall

logger = logging.getLogger("vera.middleware")


# Max body size to scan (don't try to parse multi-MB uploads)
_MAX_SCAN_BODY_BYTES = 65_536  # 64 KB


class VeraFirewallMiddleware:
    """ASGI middleware that scans request bodies through the VERA firewall.

    Plugs into FastAPI's middleware stack. For JSON request bodies:
      - Extracts text fields and scans each through the firewall
      - In enforce mode: blocks requests with HIGH/CRITICAL threats (403)
      - In monitor mode: logs threats, allows all requests
      - In disabled mode: passes through without scanning

    Non-JSON bodies and bodies larger than 64KB are passed through unscanned.
    """

    def __init__(self, app):
        self.app = app
        self._config = get_vera_config()

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Skip health check and VERA status endpoints
        path = scope.get("path", "")
        if path in ("/health", "/vera/status", "/favicon.ico"):
            await self.app(scope, receive, send)
            return

        # Only scan POST/PUT/PATCH (requests with bodies)
        method = scope.get("method", "GET")
        if method not in ("POST", "PUT", "PATCH"):
            await self.app(scope, receive, send)
            return

        # Read body for scanning
        body_parts = []
        body_complete = False

        async def receive_wrapper():
            nonlocal body_complete
            message = await receive()
            if message["type"] == "http.request":
                body_parts.append(message.get("body", b""))
                if not message.get("more_body", False):
                    body_complete = True
            return message

        # We need the body for scanning, then replay it for the handler
        # Collect the full body first
        collected_body = b""
        original_messages = []

        async def collecting_receive():
            nonlocal collected_body
            message = await receive()
            if message["type"] == "http.request":
                collected_body += message.get("body", b"")
                original_messages.append(message)
            return message

        # Collect body
        while True:
            msg = await receive()
            if msg["type"] == "http.request":
                collected_body += msg.get("body", b"")
                more = msg.get("more_body", False)
                if not more:
                    break
            else:
                # Non-HTTP message, pass through
                await self.app(scope, receive, send)
                return

        # Scan the body if it's small enough and looks like JSON
        scan_result = None
        if len(collected_body) <= _MAX_SCAN_BODY_BYTES and collected_body:
            scan_result = self._scan_body(collected_body, path)

        # If firewall blocks the request, send 403
        if scan_result and scan_result.action == FirewallAction.BLOCK:
            response_body = json.dumps({
                "error": "Request blocked by security policy",
                "details": "Input contains content that violates security rules",
                "threat_level": scan_result.threat_level.value,
            }).encode()

            await send({
                "type": "http.response.start",
                "status": 403,
                "headers": [
                    [b"content-type", b"application/json"],
                    [b"x-vera-action", b"blocked"],
                ],
            })
            await send({
                "type": "http.response.body",
                "body": response_body,
            })
            return

        # Replay the collected body for the actual handler
        body_sent = False

        async def replay_receive():
            nonlocal body_sent
            if not body_sent:
                body_sent = True
                return {
                    "type": "http.request",
                    "body": collected_body,
                    "more_body": False,
                }
            # After body is replayed, return disconnect
            return {"type": "http.disconnect"}

        # Add VERA headers to the response
        async def send_wrapper(message):
            if message["type"] == "http.response.start" and scan_result:
                headers = list(message.get("headers", []))
                action_value = scan_result.action.value.encode()
                headers.append([b"x-vera-scan", action_value])
                message = {**message, "headers": headers}
            await send(message)

        await self.app(scope, replay_receive, send_wrapper)

    def _scan_body(self, body: bytes, path: str):
        """Scan a request body through the firewall."""
        try:
            text = body.decode("utf-8")
        except UnicodeDecodeError:
            return None

        # Try to parse as JSON and scan text fields
        try:
            data = json.loads(text)
            if isinstance(data, dict):
                return self._scan_dict(data, path)
        except (json.JSONDecodeError, ValueError):
            pass

        # If not JSON, scan raw text
        firewall = get_firewall()
        return firewall.scan_input(text, context=f"raw_body:{path}")

    def _scan_dict(self, data: dict, path: str):
        """Scan all string values in a JSON dict."""
        firewall = get_firewall()
        worst_result = None

        for key, value in data.items():
            if isinstance(value, str) and len(value) > 5:
                result = firewall.scan_input(value, context=f"{path}.{key}")
                if worst_result is None or (
                    result.threat_level.value > worst_result.threat_level.value
                ):
                    worst_result = result

                # Short-circuit on BLOCK
                if result.action == FirewallAction.BLOCK:
                    return result

        return worst_result


def vera_status_dict() -> dict:
    """Build VERA status summary for the /vera/status endpoint."""
    from .enforcement import get_breaker_manager
    from .maturity import get_maturity_runtime

    config = get_vera_config()
    firewall = get_firewall()
    breakers = get_breaker_manager()
    maturity = get_maturity_runtime()

    warnings = config.validate()

    return {
        "vera_enabled": True,
        "environment": config.environment,
        "configuration_warnings": warnings,
        "pillars": {
            "identity": {
                "mode": "jwt" if config.has_signing_key else "hmac_fallback",
                "token_lifetime_hours": config.token_lifetime_hours,
            },
            "proof_chain": {
                "storage": "database" if config.has_database else "in_process",
            },
            "firewall": {
                "mode": config.firewall_mode,
                "stats": firewall.stats,
            },
            "gateway": {
                "capabilities_dir": config.capabilities_dir,
            },
            "enforcement": {
                "breaker_snapshots": breakers.all_snapshots(),
                "error_threshold": config.breaker_error_threshold,
                "cooldown_seconds": config.breaker_cooldown_seconds,
            },
        },
        "maturity": {
            "agents": maturity.all_records(),
        },
    }
