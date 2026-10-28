import asyncio
import json

import pytest

anthropic = pytest.importorskip("anthropic", minversion="2.0")
httpx = pytest.importorskip("httpx2")

from agents.mcp_tools.tri_model_consensus_tool import TriModelConsensusTool
from unified_ai_sdk import AIRequest, ModelProvider, TaskType, UnifiedAISDK
from youtube_extension.core.mcp.context_manager import MCPContext
from youtube_extension.core.mcp.protocol_bridge import AnthropicAdapter

calls = []


def respond(request: httpx.Request) -> httpx.Response:
    payload = json.loads(request.content)
    calls.append((request.url.path, request.headers.get("anthropic-version"), payload))
    if request.url.path.endswith("/count_tokens"):
        return httpx.Response(200, json={"input_tokens": 1})
    return httpx.Response(
        200,
        json={
            "id": "msg_test",
            "type": "message",
            "role": "assistant",
            "content": [{"type": "text", "text": "mocked response"}],
            "model": "claude-opus-4-8",
            "stop_reason": "end_turn",
            "stop_sequence": None,
            "usage": {"input_tokens": 11, "output_tokens": 22},
        },
    )


async def main():
    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as http_client:
        client = anthropic.AsyncAnthropic(
            api_key="sk-ant-test", http_client=http_client
        )
        sdk = UnifiedAISDK({"anthropic_api_key": "sk-ant-test", "retry_attempts": 1})
        sdk._anthropic_client = client
        result = await sdk.unified_request(
            AIRequest(
                prompt="Summarize this",
                model="claude-opus-4-8",
                provider=ModelProvider.CLAUDE,
                task_type=TaskType.SUMMARIZATION,
            )
        )
        assert (
            result.success
            and result.content == "mocked response"
            and result.tokens_used == 33
        )

        adapter = AnthropicAdapter()
        assert await adapter.initialize({"api_key": "sk-ant-test"})
        adapter._client = client
        context = MCPContext(user="test", task="compat", intent="test Anthropic v2")
        adapter_result = await adapter.send_request({"prompt": "hello"}, context)
        assert adapter_result["content"] == "mocked response"
        assert adapter_result["usage"] == {"input_tokens": 11, "output_tokens": 22}
        assert await adapter.health_check()

        consensus = object.__new__(TriModelConsensusTool)
        consensus.claude_client = client
        consensus_result = await consensus._query_claude("reason", "generic")
        assert (
            consensus_result.response == "mocked response"
            and not consensus_result.error
        )

    assert len(calls) == 4 and all(version == "2026-10-21" for _, version, _ in calls)
    assert calls[2][0].endswith("/count_tokens")
    assert anthropic.__version__.startswith("2.")


def test_anthropic_v2_app_callsites():
    asyncio.run(main())
