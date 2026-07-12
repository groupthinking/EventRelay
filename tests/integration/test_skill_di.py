import pytest
import asyncio
from unittest.mock import MagicMock
import sys
from pathlib import Path

# Add src to sys.path if not already there
src_path = str(Path(__file__).resolve().parents[2] / "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from agents.mcp_ecosystem_coordinator import SkillRegistry
from youtube_extension.backend.containers.service_container import get_service_container

@pytest.mark.asyncio
async def test_skill_di_wiring():
    """Verify that skills are correctly instantiated with their dependencies from the ServiceContainer."""
    container = get_service_container()

    # Mock services in the container
    mock_gemini = MagicMock()
    mock_db = MagicMock()

    # We can inject mocks into the container's _singletons for testing
    container._singletons["gemini_service"] = mock_gemini
    container._singletons["database_service"] = mock_db

    registry = SkillRegistry()

    # Test ContentGenerationSkill (requires gemini_service and database_service)
    skill_id = "content-generation"
    instance = registry._load_skill_instance(skill_id)

    assert instance.gemini == mock_gemini
    assert instance.db == mock_db

    # Test LeadScorerSkill (requires database_service)
    skill_id = "lead-scorer"
    instance = registry._load_skill_instance(skill_id)

    assert instance.db == mock_db
    assert not hasattr(instance, "gemini") or instance.gemini is None

@pytest.mark.asyncio
async def test_invoke_skill_with_di():
    """Verify that invoking a skill uses the DI-injected instance."""
    registry = SkillRegistry()

    # Mock the execute method
    skill_id = "seo-optimizer"
    instance = registry._load_skill_instance(skill_id)

    from skills.base import SkillResult
    instance.execute = asyncio.Future()
    instance.execute.set_result(SkillResult(status="success", output={"test": "ok"}))

    payload = {"video_id": "test_video"}
    result = await registry.invoke_skill(skill_id, payload)

    assert result["status"] == "success"
    assert result["output"]["test"] == "ok"
