"""AUDIT-009: MCP registry routing smoke test."""

from youtube_extension.services.mcp.registry import MCPServerRegistry
from youtube_extension.services.mcp.types import MCPCapability, ServerStatus


def test_get_best_server_requires_all_capabilities() -> None:
    registry = MCPServerRegistry()
    registry.register_server(
        "transcribe-a",
        "Transcribe A",
        "https://example.com/mcp-a",
        [MCPCapability.VIDEO_TRANSCRIPTION],
    )
    registry.register_server(
        "transcribe-b",
        "Transcribe B",
        "https://example.com/mcp-b",
        [MCPCapability.VIDEO_TRANSCRIPTION, MCPCapability.VIDEO_ANALYSIS],
    )
    for server_id in ("transcribe-a", "transcribe-b"):
        state = registry.get_server_state(server_id)
        assert state is not None
        state.status = ServerStatus.ONLINE

    only_transcribe = registry.get_best_server_for_task(
        [MCPCapability.VIDEO_TRANSCRIPTION]
    )
    assert only_transcribe in {"transcribe-a", "transcribe-b"}

    both = registry.get_best_server_for_task(
        [
            MCPCapability.VIDEO_TRANSCRIPTION,
            MCPCapability.VIDEO_ANALYSIS,
        ]
    )
    assert both == "transcribe-b"

    missing = registry.get_best_server_for_task([MCPCapability.AI_REASONING])
    assert missing is None
