"""Regression coverage for model-aware provider request configuration."""

import ast
from pathlib import Path

import pytest

from youtube_extension.utils.gemini_parameters import without_deprecated_sampling


@pytest.mark.parametrize("model", ["gemini-3.5-flash", "gemini-3.8-flash", "models/gemini-3-pro-preview", "google/gemini-3.7-flash", "projects/p/locations/global/publishers/google/models/gemini-3.6-flash", "gemini-4-flash"])
def test_new_gemini_omits_sampling_without_mutating_config(model):
    config = {"temperature": .4, "top_p": .95, "top_k": 40, "topP": .9, "topK": 32, "max_output_tokens": 8192, "response_schema": {"type": "object"}}
    result = without_deprecated_sampling(model, config)
    assert result == {"max_output_tokens": 8192, "response_schema": {"type": "object"}}
    assert config["temperature"] == .4


@pytest.mark.parametrize("model", ["gemini-2.5-pro", "gemini-2.0-flash", "gemini-pro", "gemma-3-27b-it", "veo-3.1", "openai/gpt-4o", "not-gemini-3.8-flash"])
def test_older_and_other_models_keep_overrides(model):
    config = {"temperature": .4, "top_p": .95, "top_k": 40}
    assert without_deprecated_sampling(model, config) == config


def test_ai_studio_utility_keeps_supported_25_dynamic_budget():
    tree = ast.parse((Path(__file__).parents[2] / "scripts/utilities/ai_studio_code.py").read_text())
    model = next(node.value.value for node in ast.walk(tree) if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == "model" for target in node.targets))
    budget = next(kw.value for node in ast.walk(tree) if isinstance(node, ast.Call) for kw in node.keywords if kw.arg == "thinking_budget")
    assert model == "gemini-2.5-pro"
    assert ast.literal_eval(budget) == -1


@pytest.mark.parametrize("module_name", ["integration.gemini_video", "integration.gemini_video_fix"])
@pytest.mark.parametrize("model", ["gemini-2.5-pro", "gemini-3.8-flash"])
async def test_rest_request_payload_policy(module_name, model):
    import importlib
    from types import SimpleNamespace
    from unittest.mock import AsyncMock
    module = importlib.import_module(module_name)
    service = object.__new__(module.GeminiVideoService)
    service.api_key = "test-key"
    response = SimpleNamespace(raise_for_status=lambda: None, json=lambda: {"ok": True})
    service.client = SimpleNamespace(post=AsyncMock(return_value=response))
    payload = {"contents": [{"parts": [{"text": "test"}]}], "generationConfig": {"temperature": .4, "topP": .9, "topK": 32, "maxOutputTokens": 8192}}
    await service._make_request(model, payload)
    sent = service.client.post.call_args.kwargs["json"]
    assert ("temperature" in sent["generationConfig"]) == model.startswith("gemini-2")
    assert sent["generationConfig"]["maxOutputTokens"] == 8192
    assert "temperature" in payload["generationConfig"]


@pytest.mark.parametrize("model", ["google/gemini-2.5-flash", "google/gemini-3.8-flash", "openai/gpt-4o"])
def test_python_gateway_payload_policy(monkeypatch, model):
    import json
    from unittest.mock import MagicMock

    from youtube_extension.services.ai import vercel_gateway_provider as gateway
    monkeypatch.setenv("AI_GATEWAY_API_KEY", "test-key")
    response = MagicMock()
    response.__enter__.return_value.read.return_value = b'{"choices":[{"message":{"content":"result"}}]}'
    transport = MagicMock(return_value=response)
    monkeypatch.setattr(gateway.urllib.request, "urlopen", transport)
    assert gateway.chat([{"role": "user", "content": "test"}], model=model) == "result"
    payload = json.loads(transport.call_args.args[0].data)
    assert ("temperature" in payload) == (model != "google/gemini-3.8-flash")
    assert payload["max_tokens"] == 1024


@pytest.mark.parametrize("path", ["src/agents/mcp_tools/build_validator_tool.py", "src/agents/mcp_tools/tri_model_consensus_tool.py"])
def test_fixed_gemini_3_tool_calls_omit_sampling(path):
    tree = ast.parse((Path(__file__).parents[2] / path).read_text())
    calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "generate_content"]
    assert calls
    for call in calls:
        kwargs = {kw.arg: kw.value for kw in call.keywords}
        assert ast.literal_eval(kwargs["model"]) == "gemini-3-pro-preview"
        assert isinstance(kwargs["config"], ast.Call)
        assert not {"temperature", "top_p", "top_k"}.intersection(kw.arg for kw in kwargs["config"].keywords)
