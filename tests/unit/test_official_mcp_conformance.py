from __future__ import annotations

import importlib.util
import json
import socket
import subprocess
import sys
import time
from pathlib import Path

import httpx


_ROOT = Path(__file__).resolve().parents[2]
_SCRIPT_PATH = _ROOT / "scripts/testing/official_mcp_conformance.py"
_FIXTURE_SERVER_PATH = _ROOT / "tests/testing/official_mcp_fixture_server.py"


def _load_module():
    assert _SCRIPT_PATH.exists(), f"missing harness script: {_SCRIPT_PATH}"
    spec = importlib.util.spec_from_file_location("official_mcp_conformance", _SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _wait_for_port(port: int, timeout: float = 5.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            if sock.connect_ex(("127.0.0.1", port)) == 0:
                return
        time.sleep(0.05)
    raise AssertionError(f"fixture server did not start on port {port}")


def test_required_checks_fail_closed_on_warning() -> None:
    module = _load_module()

    summary = module.summarize_checks(
        [
            {"id": "tools-list", "status": "SUCCESS"},
            {"id": "tools-list-deterministic-order", "status": "WARNING"},
        ],
        required=True,
        exit_code=0,
    )

    assert summary["ok"] is False
    assert summary["blocking"] == ["tools-list-deterministic-order:WARNING"]


def test_unscored_failures_do_not_block_receipt() -> None:
    module = _load_module()

    summary = module.summarize_checks(
        [{"id": "tasks-dispatch-and-envelope", "status": "FAILURE"}],
        required=False,
        exit_code=0,
    )

    assert summary["ok"] is True
    assert summary["counts"]["FAILURE"] == 1
    assert summary["blocking"] == []


def test_required_checks_fail_closed_on_runner_exit_code() -> None:
    module = _load_module()

    summary = module.summarize_checks(
        [{"id": "tools-list", "status": "SUCCESS"}],
        required=True,
        exit_code=1,
    )

    assert summary["ok"] is False
    assert summary["blocking"] == ["runner-exit-code:1"]


def test_fixture_server_keeps_tools_list_order_stable() -> None:
    port = _free_port()
    proc = subprocess.Popen(
        [sys.executable, str(_FIXTURE_SERVER_PATH), "--port", str(port)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        _wait_for_port(port)
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "MCP-Protocol-Version": "2026-07-28",
        }
        payload = {
            "jsonrpc": "2.0",
            "method": "tools/list",
            "params": {
                "_meta": {
                    "io.modelcontextprotocol/protocolVersion": "2026-07-28",
                    "io.modelcontextprotocol/clientCapabilities": {},
                    "io.modelcontextprotocol/clientInfo": {
                        "name": "pytest",
                        "version": "1.0.0",
                    },
                }
            },
        }

        orders = []
        with httpx.Client(timeout=5.0) as client:
            for index in range(1, 4):
                response = client.post(
                    f"http://127.0.0.1:{port}/mcp",
                    headers=headers,
                    json={**payload, "id": index},
                )
                response.raise_for_status()
                body = response.json()
                orders.append([tool["name"] for tool in body["result"]["tools"]])

        assert orders == [orders[0], orders[0], orders[0]]
    finally:
        proc.terminate()
        proc.wait(timeout=5)


def test_fixture_server_returns_202_for_initialized_notification() -> None:
    port = _free_port()
    proc = subprocess.Popen(
        [sys.executable, str(_FIXTURE_SERVER_PATH), "--port", str(port)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        _wait_for_port(port)
        with httpx.Client(timeout=5.0) as client:
            initialize = client.post(
                f"http://127.0.0.1:{port}/mcp",
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json, text/event-stream",
                    "MCP-Protocol-Version": "2025-11-25",
                },
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2025-11-25",
                        "capabilities": {},
                        "clientInfo": {"name": "pytest", "version": "1.0.0"},
                    },
                },
            )
            initialize.raise_for_status()
            notification = client.post(
                f"http://127.0.0.1:{port}/mcp",
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json, text/event-stream",
                    "MCP-Protocol-Version": "2025-11-25",
                },
                content=json.dumps(
                    {
                        "jsonrpc": "2.0",
                        "id": None,
                        "method": "notifications/initialized",
                        "params": {},
                    }
                ),
            )

        assert notification.status_code == 202
        assert notification.text == ""
    finally:
        proc.terminate()
        proc.wait(timeout=5)


def test_fixture_server_does_not_reflect_invalid_protocol_version_header() -> None:
    port = _free_port()
    proc = subprocess.Popen(
        [sys.executable, str(_FIXTURE_SERVER_PATH), "--port", str(port)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        _wait_for_port(port)
        with httpx.Client(timeout=5.0) as client:
            response = client.post(
                f"http://127.0.0.1:{port}/mcp",
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json, text/event-stream",
                    "MCP-Protocol-Version": "2025-11-25",
                },
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2025-11-25\r\nX-Injected: yes",
                        "capabilities": {},
                        "clientInfo": {"name": "pytest", "version": "1.0.0"},
                    },
                },
            )

        assert response.status_code == 200
        assert response.headers["MCP-Protocol-Version"] == "2025-11-25"
        assert response.json()["result"]["protocolVersion"] == "2025-11-25"
        assert "X-Injected" not in response.headers
    finally:
        proc.terminate()
        proc.wait(timeout=5)

def test_current_upstream_skills_suite_is_pinned_and_fully_accounted_for() -> None:
    module = _load_module()

    assert module.CONFORMANCE_COMMIT == "7169291ec0b68eb370fddcd9947313ab0d5e4156"

    certified_server = {entry["scenario"] for entry in module.SERVER_SCENARIOS}
    certified_client = {entry["scenario"] for entry in module.CLIENT_SCENARIOS}
    excluded_server = {
        scenario
        for group in module.EXCLUSIONS["server"]
        for scenario in group["scenarios"]
    }
    excluded_client = {
        scenario
        for group in module.EXCLUSIONS["client"]
        for scenario in group["scenarios"]
    }

    skills_server = {
        "sep-2640-skills-enumeration",
        "sep-2640-skills-manifest",
        "sep-2640-skills-directory",
    }
    skills_client = {
        "sep-2640-client-no-prefetch",
        "sep-2640-client-verify-digest",
        "sep-2640-client-verify-size",
        "sep-2640-client-verify-frontmatter",
    }

    assert skills_server <= excluded_server
    assert skills_client <= excluded_client
    assert skills_server.isdisjoint(certified_server)
    assert skills_client.isdisjoint(certified_client)
