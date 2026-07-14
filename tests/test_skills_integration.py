"""Integration tests for GTM skill discovery and invocation.

Tests verify:
- SkillRegistry discovers all 7 GTM skills from skills-lock.json
- Skills can be invoked and return expected results
- Trigger-based skill matching works correctly
- Env var pass-through works without relying on inheritance
"""

from __future__ import annotations

import json
import os
import sys
import types
from pathlib import Path
from unittest.mock import patch

import pytest

# Ensure src is on path for imports
_SRC = Path(__file__).resolve().parents[1] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

_REPO_ROOT = Path(__file__).resolve().parents[1]

# Avoid importing the full agents package (which pulls heavy deps like aiohttp).
# Instead, import the coordinator module directly.
_agents_pkg = sys.modules.get("agents")
if _agents_pkg is None:
    _agents_pkg = types.ModuleType("agents")
    _agents_pkg.__path__ = [str(_SRC / "agents")]  # type: ignore[attr-defined]
    _agents_pkg.__package__ = "agents"
    sys.modules["agents"] = _agents_pkg

# Stub youtube_extension.processors to avoid pulling in heavy ML deps
for _mod_name in [
    "youtube_extension",
    "youtube_extension.processors",
    "youtube_extension.processors.enhanced_extractor",
]:
    if _mod_name not in sys.modules:
        _stub = types.ModuleType(_mod_name)
        _stub.__path__ = []  # type: ignore[attr-defined]
        _stub.__package__ = _mod_name
        # Provide stub classes so the coordinator imports fine
        if _mod_name == "youtube_extension.processors.enhanced_extractor":
            _stub.EnhancedVideoExtractor = type("EnhancedVideoExtractor", (), {})  # type: ignore[attr-defined]
            _stub.VideoContent = type("VideoContent", (), {})  # type: ignore[attr-defined]
        sys.modules[_mod_name] = _stub

# Now we can safely import the skill registry and concrete skill classes
from agents.mcp_ecosystem_coordinator import SkillRegistry  # noqa: E402
from skills.ab_testing.main import ABTestingSkill  # noqa: E402


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

LOCK_FILE = str(_REPO_ROOT / "skills-lock.json")


@pytest.fixture
def registry() -> SkillRegistry:
    """Create a SkillRegistry pointed at the repo's skills-lock.json."""
    return SkillRegistry(lock_file_path=LOCK_FILE)


# ---------------------------------------------------------------------------
# Discovery tests
# ---------------------------------------------------------------------------


class TestSkillDiscovery:
    """Verify that SkillRegistry can discover all 7 GTM skills."""

    def test_list_skills_returns_seven(self, registry: SkillRegistry) -> None:
        skills = registry.list_skills()
        assert len(skills) == 7

    def test_all_expected_skill_ids_present(self, registry: SkillRegistry) -> None:
        skills = registry.list_skills()
        skill_ids = {s["id"] for s in skills}
        expected = {
            "content-generation",
            "seo-optimizer",
            "social-scheduler",
            "lead-scorer",
            "email-campaign",
            "analytics-dashboard",
            "ab-testing",
        }
        assert skill_ids == expected

    def test_each_skill_has_required_metadata(self, registry: SkillRegistry) -> None:
        skills = registry.list_skills()
        for skill in skills:
            assert "id" in skill
            assert "name" in skill
            assert "version" in skill
            assert "triggers" in skill
            assert "entry_point" in skill
            assert isinstance(skill["triggers"], list)
            assert len(skill["triggers"]) >= 1

    def test_get_skill_by_id(self, registry: SkillRegistry) -> None:
        skill = registry.get_skill("content-generation")
        assert skill is not None
        assert skill["id"] == "content-generation"
        assert skill["name"] == "Content Generation"
        assert skill["class_name"] == "ContentGenerationSkill"
        assert skill["version"] == "1.0.0"
        assert "youtube.video.published" in skill["triggers"]

    def test_get_nonexistent_skill_returns_none(self, registry: SkillRegistry) -> None:
        assert registry.get_skill("nonexistent-skill") is None


# ---------------------------------------------------------------------------
# Trigger matching tests
# ---------------------------------------------------------------------------


class TestSkillTriggerMatching:
    """Verify trigger-based skill discovery."""

    def test_video_published_triggers_content_generation(
        self, registry: SkillRegistry
    ) -> None:
        skills = registry.get_skills_for_trigger("youtube.video.published")
        skill_ids = {s["id"] for s in skills}
        assert "content-generation" in skill_ids

    def test_video_uploaded_triggers_seo_and_ab(
        self, registry: SkillRegistry
    ) -> None:
        skills = registry.get_skills_for_trigger("youtube.video.uploaded")
        skill_ids = {s["id"] for s in skills}
        assert "seo-optimizer" in skill_ids
        assert "ab-testing" in skill_ids

    def test_content_generated_triggers_social_scheduler(
        self, registry: SkillRegistry
    ) -> None:
        skills = registry.get_skills_for_trigger("ai.content.generated")
        skill_ids = {s["id"] for s in skills}
        assert "social-scheduler" in skill_ids

    def test_analytics_updated_triggers_lead_scorer(
        self, registry: SkillRegistry
    ) -> None:
        skills = registry.get_skills_for_trigger("youtube.analytics.updated")
        skill_ids = {s["id"] for s in skills}
        assert "lead-scorer" in skill_ids

    def test_lead_scored_triggers_email_campaign(
        self, registry: SkillRegistry
    ) -> None:
        skills = registry.get_skills_for_trigger("crm.lead.scored")
        skill_ids = {s["id"] for s in skills}
        assert "email-campaign" in skill_ids

    def test_daily_cron_triggers_analytics_dashboard(
        self, registry: SkillRegistry
    ) -> None:
        skills = registry.get_skills_for_trigger("system.cron.daily")
        skill_ids = {s["id"] for s in skills}
        assert "analytics-dashboard" in skill_ids

    def test_unknown_trigger_returns_empty(self, registry: SkillRegistry) -> None:
        skills = registry.get_skills_for_trigger("unknown.event.type")
        assert skills == []


# ---------------------------------------------------------------------------
# Invocation tests
# ---------------------------------------------------------------------------


class TestSkillInvocation:
    """Verify that skills can be invoked with payloads."""

    @pytest.mark.asyncio
    async def test_invoke_content_generation_success(
        self, registry: SkillRegistry
    ) -> None:
        result = await registry.invoke_skill(
            "content-generation",
            {"transcript": "Hello world test transcript", "video_id": "auJzb1D-fag"},
        )
        assert result["status"] == "success"
        assert result["output"]["video_id"] == "auJzb1D-fag"
        assert result["output"]["generated"] is True

    @pytest.mark.asyncio
    async def test_invoke_content_generation_missing_transcript(
        self, registry: SkillRegistry
    ) -> None:
        result = await registry.invoke_skill(
            "content-generation",
            {"video_id": "auJzb1D-fag"},
        )
        assert result["status"] == "error"
        assert "transcript" in (result.get("error") or "")

    @pytest.mark.asyncio
    async def test_invoke_seo_optimizer_success(
        self, registry: SkillRegistry
    ) -> None:
        result = await registry.invoke_skill(
            "seo-optimizer",
            {"video_id": "auJzb1D-fag", "title": "Test Video", "tags": ["ai"]},
        )
        assert result["status"] == "success"
        assert result["output"]["optimized"] is True

    @pytest.mark.asyncio
    async def test_invoke_social_scheduler_success(
        self, registry: SkillRegistry
    ) -> None:
        result = await registry.invoke_skill(
            "social-scheduler",
            {"content": "Check out this video!", "platforms": ["twitter"]},
        )
        assert result["status"] == "success"
        assert result["output"]["scheduled"] is True

    @pytest.mark.asyncio
    async def test_invoke_lead_scorer_success(
        self, registry: SkillRegistry
    ) -> None:
        result = await registry.invoke_skill(
            "lead-scorer",
            {"lead_id": "lead_001", "signals": {"views": 100, "comments": 5}},
        )
        assert result["status"] == "success"
        assert result["output"]["lead_id"] == "lead_001"

    @pytest.mark.asyncio
    async def test_invoke_email_campaign_success(
        self, registry: SkillRegistry
    ) -> None:
        result = await registry.invoke_skill(
            "email-campaign",
            {"lead_id": "lead_001", "campaign_type": "nurture"},
        )
        assert result["status"] == "success"
        assert result["output"]["campaign_type"] == "nurture"

    @pytest.mark.asyncio
    async def test_invoke_analytics_dashboard_success(
        self, registry: SkillRegistry
    ) -> None:
        result = await registry.invoke_skill(
            "analytics-dashboard",
            {"date_range": "2024-01-01/2024-01-31"},
        )
        assert result["status"] == "success"
        assert result["output"]["generated"] is True

    @pytest.mark.asyncio
    async def test_invoke_ab_testing_success(
        self, registry: SkillRegistry
    ) -> None:
        result = await registry.invoke_skill(
            "ab-testing",
            {
                "video_id": "auJzb1D-fag",
                "test_type": "thumbnail",
                "variants": [{"url": "thumb1.jpg"}, {"url": "thumb2.jpg"}],
            },
        )
        assert result["status"] == "success"
        assert result["output"]["variant_count"] == 2

    @pytest.mark.asyncio
    async def test_invoke_nonexistent_skill(self, registry: SkillRegistry) -> None:
        result = await registry.invoke_skill("nonexistent", {"foo": "bar"})
        assert result["status"] == "error"


# ---------------------------------------------------------------------------
# MCP env pass-through tests
# ---------------------------------------------------------------------------


class TestEnvPassthrough:
    """Verify explicit env var pass-through for skill subprocesses."""

    def test_gemini_skill_gets_api_key(self, registry: SkillRegistry) -> None:
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test-key-123"}):
            env = registry.get_env_for_skill("content-generation")
            assert env["GEMINI_API_KEY"] == "test-key-123"

    def test_database_skill_gets_database_url(
        self, registry: SkillRegistry
    ) -> None:
        with patch.dict(os.environ, {"DATABASE_URL": "sqlite:///test.db"}):
            env = registry.get_env_for_skill("lead-scorer")
            assert env["DATABASE_URL"] == "sqlite:///test.db"

    def test_multi_dep_skill_gets_both_vars(self, registry: SkillRegistry) -> None:
        with patch.dict(
            os.environ,
            {"GEMINI_API_KEY": "gkey", "DATABASE_URL": "sqlite:///test.db"},
        ):
            env = registry.get_env_for_skill("ab-testing")
            assert env["GEMINI_API_KEY"] == "gkey"
            assert env["DATABASE_URL"] == "sqlite:///test.db"

    def test_missing_env_var_not_included(self, registry: SkillRegistry) -> None:
        with patch.dict(os.environ, {}, clear=True):
            # Remove the vars if they exist
            os.environ.pop("GEMINI_API_KEY", None)
            os.environ.pop("DATABASE_URL", None)
            env = registry.get_env_for_skill("content-generation")
            assert "GEMINI_API_KEY" not in env

    def test_nonexistent_skill_env_empty(self, registry: SkillRegistry) -> None:
        env = registry.get_env_for_skill("nonexistent")
        assert env == {}

    def test_skill_class_env_matches_declared_requirements(self) -> None:
        with patch.dict(
            os.environ,
            {"GEMINI_API_KEY": "gkey", "DATABASE_URL": "sqlite:///test.db"},
        ):
            env = ABTestingSkill().get_env()
            assert env == {
                "GEMINI_API_KEY": "gkey",
                "DATABASE_URL": "sqlite:///test.db",
            }


# ---------------------------------------------------------------------------
# Lock file validation
# ---------------------------------------------------------------------------


class TestSkillsLockFile:
    """Verify skills-lock.json structure and validity."""

    def test_lock_file_is_valid_json(self) -> None:
        with open(LOCK_FILE) as f:
            data = json.load(f)
        assert "skills" in data
        assert isinstance(data["skills"], dict)

    def test_lock_file_contains_gtm_skills(self) -> None:
        with open(LOCK_FILE) as f:
            data = json.load(f)
        gtm_skills = {
            k: v
            for k, v in data["skills"].items()
            if v.get("source") == "uvai-skills"
        }
        assert len(gtm_skills) == 7

    def test_each_gtm_skill_has_required_fields(self) -> None:
        with open(LOCK_FILE) as f:
            data = json.load(f)
        for skill_id, meta in data["skills"].items():
            if meta.get("source") != "uvai-skills":
                continue
            assert "skillPath" in meta, f"{skill_id} missing skillPath"
            assert "className" in meta, f"{skill_id} missing className"
            assert "version" in meta, f"{skill_id} missing version"
            assert "triggers" in meta, f"{skill_id} missing triggers"
            assert "dependencies" in meta, f"{skill_id} missing dependencies"
