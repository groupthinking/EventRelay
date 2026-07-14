from unittest.mock import MagicMock

import pytest

from agents.mcp_ecosystem_coordinator import SkillRegistry
from skills.base import SkillResult
from youtube_extension.backend.containers.service_container import (
    get_service_container,
)


@pytest.mark.asyncio
async def test_skill_di_wiring():
    """Verify skills are instantiated with their dependencies from the ServiceContainer."""
    container = get_service_container()

    # Inject mock services into the container for testing.
    mock_gemini = MagicMock()
    mock_db = MagicMock()
    container._singletons["gemini_service"] = mock_gemini
    container._singletons["database_service"] = mock_db

    registry = SkillRegistry()

    # ContentGenerationSkill requires gemini_service and database_service.
    instance = registry._load_skill_instance("content-generation")
    assert instance.gemini is mock_gemini
    assert instance.db is mock_db

    # LeadScorerSkill requires only database_service.
    instance = registry._load_skill_instance("lead-scorer")
    assert instance.db is mock_db
    assert not hasattr(instance, "gemini") or instance.gemini is None


@pytest.mark.asyncio
async def test_invoke_skill_with_di():
    """Verify that invoking a skill routes the payload to the DI-injected instance."""
    registry = SkillRegistry()

    instance = registry._load_skill_instance("seo-optimizer")

    # Replace execute with an async callable (a coroutine function), so that
    # `await instance.execute(payload)` inside invoke_skill works correctly.
    async def fake_execute(payload):
        return SkillResult(status="success", output={"test": "ok"})

    instance.execute = fake_execute

    result = await registry.invoke_skill("seo-optimizer", {"video_id": "test_video"})

    assert result["status"] == "success"
    assert result["output"]["test"] == "ok"
