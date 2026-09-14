#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import socket
import subprocess
import sys
import tempfile
import time
from collections import Counter
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_SERVER = REPO_ROOT / "tests/testing/official_mcp_fixture_server.py"
AUTH_CLIENT = REPO_ROOT / "tests/testing/official_mcp_auth_client.mjs"
DEFAULT_RECEIPT = (
    REPO_ROOT / "tests/fixtures/mcp_conformance/official-2026-07-28-receipt.json"
)
CONFORMANCE_COMMIT = "7169291ec0b68eb370fddcd9947313ab0d5e4156"
CONFORMANCE_PACKAGE = (
    f"git+https://github.com/modelcontextprotocol/conformance.git#{CONFORMANCE_COMMIT}"
)
SERVER_SCENARIOS = (
    {"scenario": "tools-list", "spec_version": "2026-07-28", "required": True},
    {
        "scenario": "tools-call-simple-text",
        "spec_version": "2026-07-28",
        "required": True,
    },
    {"scenario": "tools-call-error", "spec_version": "2026-07-28", "required": True},
    {"scenario": "server-initialize", "spec_version": "2025-11-25", "required": True},
)
CLIENT_SCENARIOS = (
    {"scenario": "auth/metadata-var2", "spec_version": "2026-07-28", "required": True},
    {
        "scenario": "auth/token-endpoint-auth-basic",
        "spec_version": "2026-07-28",
        "required": True,
    },
    {
        "scenario": "auth/token-endpoint-auth-post",
        "spec_version": "2026-07-28",
        "required": True,
    },
    {
        "scenario": "auth/token-endpoint-auth-none",
        "spec_version": "2026-07-28",
        "required": True,
    },
)
EXCLUSIONS = {
    "server": [
        {
            "reason": "surface-not-implemented",
            "scenarios": [
                "server-stateless",
                "completion-complete",
                "tools-call-image",
                "tools-call-audio",
                "tools-call-embedded-resource",
                "tools-call-mixed-content",
                "tools-call-with-progress",
                "server-sse-multiple-streams",
                "resources-list",
                "resources-read-text",
                "resources-read-binary",
                "resources-templates-read",
                "sep-2164-resource-not-found",
                "prompts-list",
                "prompts-get-simple",
                "prompts-get-with-args",
                "prompts-get-embedded-resource",
                "prompts-get-with-image",
                "dns-rebinding-protection",
                "caching",
                "input-required-result-basic-elicitation",
                "input-required-result-basic-sampling",
                "input-required-result-basic-list-roots",
                "input-required-result-request-state",
                "input-required-result-multiple-input-requests",
                "input-required-result-multi-round",
                "input-required-result-missing-input-response",
                "input-required-result-non-tool-request",
                "input-required-result-result-type",
                "input-required-result-unsupported-methods",
                "input-required-result-tampered-state",
                "input-required-result-capability-check",
                "input-required-result-ignore-extra-params",
                "input-required-result-validate-input",
            ],
        },
        {
            "reason": "extension-not-implemented",
            "scenarios": [
                "tasks-lifecycle",
                "tasks-capability-negotiation",
                "tasks-wire-fields",
                "tasks-request-state-removal",
                "tasks-mrtr-input",
                "tasks-request-headers",
                "tasks-dispatch-and-envelope",
                "tasks-status-notifications",
                "tasks-required-task-error",
                "tasks-mrtr-composition",
                # SEP-2640 Skills server scenarios landed upstream after the
                # original baseline. EventRelay does not expose these server
                # methods yet, so account for them explicitly instead of
                # silently producing a stale green receipt.
                "sep-2640-skills-enumeration",
                "sep-2640-skills-manifest",
                "sep-2640-skills-directory",
            ],
        },
    ],
    "client": [
        {
            "reason": "surface-not-certified-in-this-baseline",
            "scenarios": [
                "tools_call",
                "request-metadata",
                "auth/metadata-default",
                "auth/metadata-var1",
                "auth/metadata-var3",
                "auth/basic-cimd",
                "auth/scope-from-www-authenticate",
                "auth/scope-from-scopes-supported",
                "auth/scope-omitted-when-undefined",
                "auth/scope-step-up",
                "auth/scope-retry-limit",
                "auth/pre-registration",
                "auth/resource-mismatch",
                "auth/offline-access-scope",
                "auth/offline-access-not-supported",
                "auth/authorization-server-migration",
                "auth/iss-supported",
                "auth/iss-not-advertised",
                "auth/iss-supported-missing",
                "auth/iss-wrong-issuer",
                "auth/iss-unexpected",
                "auth/iss-normalized",
                "auth/metadata-issuer-mismatch",
                "sep-2322-client-request-state",
                "http-standard-headers",
                "http-custom-headers",
                "http-invalid-tool-headers",
                "json-schema-ref-no-deref",
            ],
        },
        {
            "reason": "extension-not-implemented",
            "scenarios": [
                "auth/client-credentials-jwt",
                "auth/client-credentials-basic",
                "auth/enterprise-managed-authorization",
                "auth/dpop",
                "auth/dpop-nonce",
                "auth/wif-jwt-bearer",
                "json-schema-2020-12-preservation",
                # The closed Agent Factory host spike was not merged and has
                # not been exercised as a real MCP client. Keep every official
                # Skills client scenario visible as unsupported until a driver
                # runs against the upstream hostile servers.
                "sep-2640-client-no-prefetch",
                "sep-2640-client-verify-digest",
                "sep-2640-client-verify-size",
                "sep-2640-client-verify-frontmatter",
            ],
        },
    ],
}


def summarize_checks(
    checks: list[dict[str, Any]],
    *,
    required: bool,
    exit_code: int,
) -> dict[str, Any]:
    counts = Counter(str(check.get("status", "UNKNOWN")) for check in checks)
    blocking = [
        f"{check.get('id', '<unknown>')}:{check.get('status', 'UNKNOWN')}"
        for check in checks
        if required and str(check.get("status")) in {"FAILURE", "WARNING"}
    ]
    # Fail closed on a runner-level failure: a required scenario whose
    # conformance runner exits non-zero must never be reported as passing,
    # even when checks.json contains no FAILURE/WARNING entries.
    if required and exit_code != 0:
        blocking.append(f"runner-exit-code:{exit_code}")
    return {
        "ok": not blocking,
        "counts": dict(counts),
        "blocking": blocking,
    }


def _run(
    args: list[str],
    *,
    cwd: Path = REPO_ROOT,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=cwd,
        text=True,
        capture_output=True,
        check=False,
    )


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _wait_for_port(port: int, timeout: float = 10.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            if sock.connect_ex(("127.0.0.1", port)) == 0:
                return
        time.sleep(0.05)
    raise RuntimeError(f"fixture server did not start on port {port}")


def _load_checks(output_dir: Path) -> list[dict[str, Any]]:
    candidates = sorted(output_dir.glob("**/checks.json"))
    if not candidates:
        raise FileNotFoundError(f"no checks.json found under {output_dir}")
    return json.loads(candidates[-1].read_text())


def _npx_prefix() -> list[str]:
    return [
        "npx",
        "--yes",
        f"--package={CONFORMANCE_PACKAGE}",
        "conformance",
    ]


def _run_server_scenario(config: dict[str, Any]) -> dict[str, Any]:
    port = _free_port()
    with tempfile.TemporaryDirectory(prefix="mcp-conformance-server-") as tmpdir:
        output_dir = Path(tmpdir)
        server = subprocess.Popen(
            [sys.executable, str(FIXTURE_SERVER), "--port", str(port)],
            cwd=REPO_ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        try:
            _wait_for_port(port)
            cmd = _npx_prefix() + [
                "server",
                "--url",
