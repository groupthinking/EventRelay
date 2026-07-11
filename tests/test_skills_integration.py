import os
import json
import pytest
import asyncio
from unittest.mock import MagicMock, patch
import sys

# Ensure src is in path
sys.path.append(os.path.join(os.getcwd(), "src"))

# Mock dependencies that cause issues during import
# Using MagicMock for packages needs __path__ to be set if they are used in imports
mock_google = MagicMock()
mock_google.__path__ = []
sys.modules['google'] = mock_google

mock_google_cloud = MagicMock()
mock_google_cloud.__path__ = []
sys.modules['google.cloud'] = mock_google_cloud

sys.modules['google.genai'] = MagicMock()
sys.modules['google.generativeai'] = MagicMock()
sys.modules['google.cloud.aiplatform'] = MagicMock()
sys.modules['vertexai'] = MagicMock()
sys.modules['vertexai.generative_models'] = MagicMock()

sys.modules['aiohttp'] = MagicMock()
sys.modules['pandas'] = MagicMock()
sys.modules['youtube_transcript_api'] = MagicMock()
sys.modules['youtube_extension.processors.enhanced_extractor'] = MagicMock()
sys.modules['youtube_extension.services.pipeline_audit_store'] = MagicMock()

# Import SkillRegistry after mocking
from agents.mcp_ecosystem_coordinator import SkillRegistry

@pytest.fixture
def skill_registry():
    # Use the real skills-lock.json created during the task
    return SkillRegistry(lock_file="skills-lock.json")

def test_skill_discovery(skill_registry):
    """Verify that all 7 GTM skills are discovered from skills-lock.json."""
    skills = skill_registry.list_skills(source="uvai-skills")
    assert len(skills) == 7

    expected_ids = [
        "content-generation",
        "seo-optimizer",
        "social-scheduler",
        "lead-scorer",
        "email-campaign",
        "analytics-dashboard",
        "ab-testing"
    ]

    discovered_ids = [s["id"] for s in skills]
    for skill_id in expected_ids:
        assert skill_id in discovered_ids

@pytest.mark.asyncio
async def test_skill_invocation(skill_registry):
    """Verify that a skill can be invoked and returns the expected result."""
    # We use content-generation for testing invocation
    skill_id = "content-generation"
    context = {"video_id": "test_123", "transcript": "Hello world"}

    # We expect this to work because we created the thin wrapper main.py
    result = await skill_registry.invoke_skill(skill_id, context)

    assert result["status"] == "success"
    assert result["skill"] == skill_id

@pytest.mark.asyncio
async def test_skill_invocation_env_vars(skill_registry):
    """Verify that environment variables are passed (simulated)."""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value.stdout = json.dumps({"status": "success"})
        mock_run.return_value.returncode = 0

        os.environ["GEMINI_API_KEY"] = "test_key"

        await skill_registry.invoke_skill("content-generation", {})

        # Check that the env passed to subprocess.run contains GEMINI_API_KEY
        args, kwargs = mock_run.call_args
        passed_env = kwargs.get("env", {})
        assert passed_env.get("GEMINI_API_KEY") == "test_key"
        assert "SKILL_CONTEXT" in passed_env
