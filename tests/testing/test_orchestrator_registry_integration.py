import pytest
from src.youtube_extension.services.agents.adapters.agent_orchestrator import AgentOrchestrator
from src.youtube_extension.services.agents.adapters.transcript_action_agent import TranscriptActionAgent

@pytest.mark.asyncio
async def test_orchestrator_get_agent():
    orchestrator = AgentOrchestrator()
    agent = await orchestrator.get_agent("transcript_action")
    assert isinstance(agent, TranscriptActionAgent)
