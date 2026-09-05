"""Tests for the optional Agent Factory Antigravity backend."""

from __future__ import annotations

from typing import Any, Mapping

import pytest

from youtube_extension.services.agents.antigravity_backend import (
    AntigravityBackend,
    AntigravityBackendConfig,
    AntigravityConfigurationError,
    AntigravityExecutionBlocked,
    AntigravityMCPServer,
    compare_agent_factory_runs,
)


class FakeTransport:
    def __init__(
        self,
        response: Mapping[str, Any] | None = None,
        *,
        is_live: bool = False,
    ) -> None:
        self.is_live = is_live
        self.response = response or {
            "id": "interaction-1",
            "environment_id": "environment-1",
            "status": "completed",
            "output_text": "done",
            "steps": [{"type": "mcp_call", "name": "evidence_get"}],
            "usage": {"total_tokens": 321},
        }
        self.payloads: list[dict[str, Any]] = []

    async def create_interaction(self, payload: dict[str, Any]) -> Mapping[str, Any]:
        self.payloads.append(payload)
        return self.response


def config(**changes: Any) -> AntigravityBackendConfig:
    values = {
        "enabled": True,
        "max_total_tokens": 1_000,
        "mcp_servers": (
            AntigravityMCPServer(
                name="eventrelay",
                url="https://mcp.example.test/mcp",
                allowed_tools=("evidence_get",),
            ),
        ),
        "read_only_tools": frozenset({"evidence_get"}),
    }
    values.update(changes)
    return AntigravityBackendConfig(**values)


@pytest.mark.asyncio
async def test_execute_builds_bounded_request_and_receipt() -> None:
    transport = FakeTransport()
    backend = AntigravityBackend(config(), transport)

    receipt = await backend.execute("Review evidence", {"video_pack_id": "pack-1"})

    assert receipt.status == "completed"
    assert receipt.interaction_id == "interaction-1"
    assert receipt.environment_id == "environment-1"
    assert receipt.usage == {"total_tokens": 321}
    assert receipt.policy["mcp_access"] == "explicit_read_only_allowlist"
    assert receipt.policy["provider_hooks"] == "fail_open"
    assert len(receipt.request_sha256) == 64

    payload = transport.payloads[0]
    assert payload["agent"] == "antigravity-preview-05-2026"
    assert payload["agent_config"]["max_total_tokens"] == 1_000
    assert payload["tools"] == [
        {
            "type": "mcp_server",
            "name": "eventrelay",
            "url": "https://mcp.example.test/mcp",
            "allowed_tools": ["evidence_get"],
        }
    ]
    assert "headers" not in payload["tools"][0]
    assert "pack-1" in payload["input"]


@pytest.mark.asyncio
async def test_disabled_backend_cannot_execute() -> None:
    backend = AntigravityBackend(config(enabled=False), FakeTransport())

    with pytest.raises(AntigravityExecutionBlocked, match="disabled"):
        await backend.execute("do work")


@pytest.mark.asyncio
async def test_live_transport_requires_two_explicit_gates() -> None:
    backend = AntigravityBackend(config(), FakeTransport(is_live=True))
    with pytest.raises(AntigravityExecutionBlocked, match="explicit approval"):
        await backend.execute("do work")

    backend = AntigravityBackend(
        config(allow_live_execution=True), FakeTransport(is_live=True)
    )
    with pytest.raises(AntigravityExecutionBlocked, match="fail open"):
        await backend.execute("do work")


@pytest.mark.asyncio
async def test_direct_media_is_rejected_before_transport() -> None:
    transport = FakeTransport()
    backend = AntigravityBackend(config(), transport)

    with pytest.raises(AntigravityConfigurationError, match="direct media"):
        await backend.execute("analyze", {"video_uri": "gs://bucket/video.mp4"})
    assert transport.payloads == []


@pytest.mark.parametrize("name", ["EventRelay", "event relay", "eventrelay!"])
def test_mcp_name_must_match_provider_contract(name: str) -> None:
    invalid = config(
        mcp_servers=(
            AntigravityMCPServer(
                name=name,
                url="https://mcp.example.test/mcp",
                allowed_tools=("evidence_get",),
            ),
        )
    )
    with pytest.raises(AntigravityConfigurationError, match="server name"):
        invalid.validate()


def test_mcp_transport_and_read_only_allowlist_are_enforced() -> None:
    insecure = config(
        mcp_servers=(
            AntigravityMCPServer(
                name="eventrelay",
                url="http://mcp.example.test/sse",
                allowed_tools=("evidence_delete",),
            ),
        )
    )
    with pytest.raises(AntigravityConfigurationError, match="HTTPS"):
        insecure.validate()

    undeclared = config(
        mcp_servers=(
            AntigravityMCPServer(
                name="eventrelay",
                url="https://mcp.example.test/mcp",
                allowed_tools=("evidence_delete",),
            ),
        )
    )
    with pytest.raises(AntigravityConfigurationError, match="read-only"):
        undeclared.validate()


@pytest.mark.asyncio
async def test_receipt_records_transport_failure_and_budget_overrun() -> None:
    backend = AntigravityBackend(
        config(),
        FakeTransport(
            {
                "id": "interaction-2",
                "status": "incomplete",
                "usage": {"total_tokens": 1_050},
                "error": "token budget reached",
            }
        ),
    )
    receipt = await backend.execute("do work")

    assert receipt.status == "incomplete"
    assert receipt.budget_exceeded is True
    assert receipt.error == "token budget reached"


@pytest.mark.asyncio
async def test_receipt_survives_transport_exception() -> None:
    class BrokenTransport(FakeTransport):
        async def create_interaction(
            self, payload: dict[str, Any]
        ) -> Mapping[str, Any]:
            raise TimeoutError("provider timed out")

    receipt = await AntigravityBackend(config(), BrokenTransport()).execute("do work")

    assert receipt.status == "failed"
    assert receipt.error == "TimeoutError: provider timed out"


@pytest.mark.asyncio
async def test_orchestrator_records_managed_backend_dispatch() -> None:
    from youtube_extension.services.agents.adapters.agent_orchestrator import (
        AgentOrchestrator,
    )

    orchestrator = AgentOrchestrator()
    receipt = await orchestrator.execute_antigravity_backend(
        backend=AntigravityBackend(config(), FakeTransport()),
        task="review",
        context={"video_pack_id": "pack-2"},
    )

    assert receipt.status == "completed"
    entry = orchestrator.get_a2a_log(limit=1)[0]["content"]
    assert entry["type"] == "managed_backend_dispatch"
    assert entry["backend"] == "google_antigravity"
    assert entry["receipt_id"] == receipt.receipt_id
    assert "context" not in entry


@pytest.mark.asyncio
async def test_comparison_artifact_is_provider_neutral() -> None:
    transport = FakeTransport()
    receipt = await AntigravityBackend(config(), transport).execute("compare")

    comparison = compare_agent_factory_runs(
        {"success": True, "total_processing_time": 0.5, "results": {"a": "b"}},
        receipt,
    )
    assert comparison["native"]["success"] is True
    assert comparison["antigravity"]["total_tokens"] == 321
