import importlib
import json
import sys
import types
from pathlib import Path

import pytest


def _load_coordinator_types():
    stub = types.ModuleType("youtube_extension.processors.enhanced_extractor")
    stub.EnhancedVideoExtractor = object
    stub.VideoContent = object
    sys.modules["youtube_extension.processors.enhanced_extractor"] = stub
    module = importlib.import_module("src.agents.mcp_ecosystem_coordinator")
    return module.MCPEcosystemCoordinator, module.SkillRegistry


def test_skill_registry_discovers_gtm_skills() -> None:
    _, SkillRegistry = _load_coordinator_types()
    repo_root = Path(__file__).resolve().parents[1]
    registry = SkillRegistry(lock_file=repo_root / "skills-lock.json")

    skill_ids = {skill["id"] for skill in registry.list_skills()}
    assert skill_ids == {
        "content-generation",
        "seo-optimizer",
        "social-scheduler",
        "lead-scorer",
        "email-campaign",
        "analytics-dashboard",
        "ab-testing",
    }


def test_skill_registry_filters_by_trigger() -> None:
    _, SkillRegistry = _load_coordinator_types()
    repo_root = Path(__file__).resolve().parents[1]
    registry = SkillRegistry(lock_file=repo_root / "skills-lock.json")

    uploaded_skills = {skill["id"] for skill in registry.list_skills(trigger="video_uploaded")}
    assert uploaded_skills == {"seo-optimizer", "ab-testing"}


@pytest.mark.asyncio
async def test_skill_invocation_passes_explicit_env(tmp_path: Path) -> None:
    MCPEcosystemCoordinator, SkillRegistry = _load_coordinator_types()
    skill_script = tmp_path / "skill_main.py"
    skill_script.write_text(
        "import json, os, sys\n"
        "payload = json.loads(sys.stdin.read() or '{}')\n"
        "print(json.dumps({'status': 'success', 'payload': payload, 'env': os.getenv('GEMINI_API_KEY')}))\n"
    )

    lock_file = tmp_path / "skills-lock.json"
    lock_file.write_text(
        json.dumps(
            {
                "eventrelay_skills": [
                    {
                        "id": "content-generation",
                        "name": "Content Generation",
                        "version": "1.0.0",
                        "source": "uvai-skills",
                        "entry_point": str(skill_script),
                        "triggers": ["video_published"],
                        "dependencies": ["gemini_service", "database_service"],
                        "required_env_vars": ["GEMINI_API_KEY"],
                    }
                ]
            }
        )
    )

    coordinator = MCPEcosystemCoordinator(skill_registry=SkillRegistry(lock_file=lock_file))
    result = await coordinator.invoke_skill(
        "content-generation",
        {"video_id": "abc123"},
        env_vars={"GEMINI_API_KEY": "test-key"},
    )

    assert result["status"] == "success"
    assert result["payload"]["video_id"] == "abc123"
    assert result["env"] == "test-key"
