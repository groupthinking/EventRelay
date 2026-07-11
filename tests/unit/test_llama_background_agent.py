import pytest
import asyncio
import sys
from unittest.mock import MagicMock, patch

# We must mock module-level imports that are not available in the environment.
# Since agents/__init__.py imports many things, we need to stub them out
# BEFORE they are ever imported.

# List of known missing dependencies that cause import errors in src/agents/
MISSING_DEPS = [
    "llama_cpp",
    "sentence_transformers",
    "aiohttp",
    "dotenv",
    "google",
    "google.genai",
    "pydantic",
    "pydantic_settings",
    "anthropic",
    "openai"
]

def setup_mocks():
    for dep in MISSING_DEPS:
        if dep not in sys.modules:
            sys.modules[dep] = MagicMock()

setup_mocks()

# Now we can safely import from agents
from agents.llama_background_agent import LlamaBackgroundAgent, LlamaAgentMCPTool

@pytest.fixture
def llama_agent():
    # Patch the classes that are imported inside LlamaBackgroundAgent.__init__
    with patch("agents.llama_background_agent.QualityAgent"), \
         patch("agents.llama_background_agent.ActionImplementer"), \
         patch("agents.llama_background_agent.UVAIObservability"):
        agent = LlamaBackgroundAgent(model_path="mock/path/model.gguf")
        return agent

def run_async(coro):
    """Helper to run async functions without pytest-asyncio if it's missing."""
    return asyncio.run(coro)

def test_get_performance_stats(llama_agent):
    """Test LlamaBackgroundAgent.get_performance_stats()"""
    # Initialize some stats
    llama_agent.total_videos_processed = 5
    llama_agent.average_processing_time = 12.5

    stats = run_async(llama_agent.get_performance_stats())

    assert stats["total_videos_processed"] == 5
    assert stats["average_processing_time"] == 12.5
    assert stats["model_path"] == "mock/path/model.gguf"
    assert "last_updated" in stats
    assert stats["learning_insights_count"] == 0

def test_mcp_tool_get_stats(llama_agent):
    """Test LlamaAgentMCPTool.get_stats()"""
    # Setup agent stats
    llama_agent.total_videos_processed = 10
    llama_agent.average_processing_time = 8.0

    mcp_tool = LlamaAgentMCPTool(llama_agent)
    stats = run_async(mcp_tool.get_stats())

    assert stats["total_videos_processed"] == 10
    assert stats["average_processing_time"] == 8.0
    assert stats["model_path"] == "mock/path/model.gguf"
