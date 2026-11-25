"""Model migration contract, using the real SDK config and an offline transport."""
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from src.agents.specialized.precision_extractor import PrecisionExtractorAgent


@pytest.mark.asyncio
@pytest.mark.parametrize("override", [None, "gemini-2.5-flash"])
async def test_precision_model_and_json_request(monkeypatch, override):
    if override is None:
        monkeypatch.delenv("GEMINI_VIDEO_MODEL", raising=False)
    else:
        monkeypatch.setenv("GEMINI_VIDEO_MODEL", override)
    output = '{"physical_entities": [], "visual_steps": [], "discrepancies": []}'
    generate = Mock(return_value=SimpleNamespace(text=output))
    client = SimpleNamespace(models=SimpleNamespace(generate_content=generate))
    monkeypatch.setattr("src.agents.specialized.precision_extractor.genai.Client", lambda **kwargs: client)
    agent = PrecisionExtractorAgent(api_key="test-key")
    result = await agent.extract_precision_data("https://youtu.be/auJzb1D-fag", "recipe")
    request = generate.call_args.kwargs
    assert request["model"] == (override or "gemini-3.8-flash")
    assert request["contents"][0].file_data.file_uri == "https://youtu.be/auJzb1D-fag"
    assert "CONTEXT: recipe" in request["contents"][1].text
    config = request["config"].model_dump(exclude_none=True)
    assert config == {"response_mime_type": "application/json"}
    assert result == {"physical_entities": [], "visual_steps": [], "discrepancies": []}
