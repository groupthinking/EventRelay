"""Tests for the MCPC Python adapter.

These tests validate the adapter logic in isolation by mocking the subprocess
so no compiled Node.js binary is required.
"""

from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Ensure src is importable
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from mcp.mcpc_adapter import MCPCAdapter, MCPCError  # noqa: E402


# ── Helpers ────────────────────────────────────────────────────────────────────


def make_response(request_id: str, result: object) -> bytes:
    return (json.dumps({"jsonrpc": "2.0", "id": request_id, "result": result}) + "\n").encode()


def make_error_response(request_id: str, code: int, message: str) -> bytes:
    return (
        json.dumps({"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}})
        + "\n"
    ).encode()


class FakeProcess:
    """Minimal fake asyncio subprocess that returns pre-canned responses."""

    def __init__(self, response_factory):
        self._response_factory = response_factory
        self._written: list[bytes] = []

        stdin = MagicMock()

        async def write_and_drain(data: bytes) -> None:
            self._written.append(data)
            # Schedule the response into the output queue
            response = self._response_factory(data)
            if response:
                await asyncio.sleep(0)  # yield
                self._output_queue.put_nowait(response)

        stdin.write = lambda data: self._written.append(data)
        stdin.drain = AsyncMock()
        self.stdin = stdin

        self._output_queue: asyncio.Queue[bytes] = asyncio.Queue()

        async def readline() -> bytes:
            return await self._output_queue.get()

        stdout = MagicMock()
        stdout.readline = readline
        self.stdout = stdout

        self.stderr = MagicMock()
        self.terminate = MagicMock()
        self.wait = AsyncMock(return_value=0)
        self.returncode = 0

    def push_response(self, data: bytes) -> None:
        self._output_queue.put_nowait(data)


# ── Fixtures ───────────────────────────────────────────────────────────────────


@pytest.fixture()
def adapter():
    return MCPCAdapter(server_path="/fake/index.js")


# ── Tests ──────────────────────────────────────────────────────────────────────


class TestMCPCAdapterInit:
    def test_default_server_path_is_mcpc_dist(self):
        a = MCPCAdapter()
        assert "mcpc" in str(a._server_path)
        assert a._server_path.name == "index.js"

    def test_custom_server_path(self):
        a = MCPCAdapter(server_path="/custom/path/server.js")
        assert str(a._server_path) == "/custom/path/server.js"

    def test_not_initialized_by_default(self):
        a = MCPCAdapter()
        assert not a._initialized


class TestMCPCAdapterCallTool:
    @pytest.mark.asyncio
    async def test_call_tool_returns_parsed_json(self, adapter: MCPCAdapter):
        """call_tool should parse the text content returned by the server."""
        tool_result = {"topic": "test", "consensus": "ok", "agreement_score": 1.0}

        proc = FakeProcess(response_factory=lambda _: None)

        with patch("asyncio.create_subprocess_exec", return_value=proc):
            # We'll manually push responses for each expected request
            async def fake_initialize():
                adapter._initialized = True
                adapter._process = proc
                adapter._reader_task = asyncio.create_task(adapter._read_loop())

            adapter.initialize = fake_initialize  # type: ignore[assignment]
            await adapter.initialize()

            # Push the tools/call response matching the next request id
            async def push_and_call():
                # Give the reader loop time to start
                await asyncio.sleep(0)
                # We need to intercept the pending future; instead we patch _send_request
                pass

            # Patch _send_request to avoid needing real subprocess
            adapter._send_request = AsyncMock(  # type: ignore[assignment]
                return_value={
                    "content": [{"type": "text", "text": json.dumps(tool_result)}]
                }
            )
            result = await adapter.call_tool("round_table", {"topic": "test", "agents": ["a"]})
            assert result == tool_result

    @pytest.mark.asyncio
    async def test_call_tool_raises_on_error_flag(self, adapter: MCPCAdapter):
        """call_tool should raise MCPCError when isError is True."""
        adapter._initialized = True
        adapter._send_request = AsyncMock(  # type: ignore[assignment]
            return_value={
                "content": [{"type": "text", "text": "Something went wrong"}],
                "isError": True,
            }
        )
        with pytest.raises(MCPCError) as exc_info:
            await adapter.call_tool("bad_tool", {})
        assert "Something went wrong" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_call_tool_raises_on_jsonrpc_error(self, adapter: MCPCAdapter):
        """_send_request raising MCPCError should propagate through call_tool."""
        adapter._initialized = True
        adapter._send_request = AsyncMock(  # type: ignore[assignment]
            side_effect=MCPCError(-32601, "Method not found: unknown_tool")
        )
        with pytest.raises(MCPCError) as exc_info:
            await adapter.call_tool("unknown_tool", {})
        assert exc_info.value.code == -32601

    @pytest.mark.asyncio
    async def test_list_tools_returns_list(self, adapter: MCPCAdapter):
        """list_tools should return the tools array from the server."""
        adapter._initialized = True
        adapter._send_request = AsyncMock(  # type: ignore[assignment]
            return_value={"tools": [{"name": "round_table"}, {"name": "state_get"}]}
        )
        tools = await adapter.list_tools()
        assert len(tools) == 2
        assert tools[0]["name"] == "round_table"

    @pytest.mark.asyncio
    async def test_call_tool_returns_raw_text_on_non_json(self, adapter: MCPCAdapter):
        """call_tool should return raw string when content is not valid JSON."""
        adapter._initialized = True
        adapter._send_request = AsyncMock(  # type: ignore[assignment]
            return_value={"content": [{"type": "text", "text": "plain string output"}]}
        )
        result = await adapter.call_tool("some_tool", {})
        assert result == "plain string output"

    @pytest.mark.asyncio
    async def test_close_cancels_reader_task(self, adapter: MCPCAdapter):
        """close() should cancel the reader task and terminate the process."""
        # Create a real asyncio.Task backed by a coroutine that just sleeps,
        # so it can be properly awaited and cancelled.
        async def _sleeper():
            await asyncio.sleep(100)

        loop = asyncio.get_event_loop()
        real_task = loop.create_task(_sleeper())

        adapter._reader_task = real_task  # type: ignore[assignment]

        mock_process = MagicMock()
        mock_process.terminate = MagicMock()
        mock_process.wait = AsyncMock(return_value=0)
        adapter._process = mock_process  # type: ignore[assignment]
        adapter._initialized = True

        await adapter.close()
        assert real_task.cancelled()
        assert not adapter._initialized


class TestMCPCAdapterContextManager:
    @pytest.mark.asyncio
    async def test_context_manager_initializes_and_closes(self, adapter: MCPCAdapter):
        adapter.initialize = AsyncMock()  # type: ignore[assignment]
        adapter.close = AsyncMock()  # type: ignore[assignment]

        async with adapter:
            adapter.initialize.assert_called_once()

        adapter.close.assert_called_once()


class TestMCPCError:
    def test_mcpc_error_attributes(self):
        err = MCPCError(-32601, "Method not found")
        assert err.code == -32601
        assert err.message == "Method not found"
        assert "Method not found" in str(err)
