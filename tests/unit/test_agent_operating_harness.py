from __future__ import annotations

import importlib.util
import json
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SCRIPT_PATH = _REPO_ROOT / "scripts/testing/agent_operating_harness.py"


def _load_module():
    assert _SCRIPT_PATH.exists(), f"missing harness script: {_SCRIPT_PATH}"
    spec = importlib.util.spec_from_file_location("agent_operating_harness", _SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_summarize_checks_fails_closed_on_warning() -> None:
    module = _load_module()

    summary = module.summarize_checks(
        [
            {"id": "skill-docs", "status": "SUCCESS"},
            {"id": "skills-lock", "status": "WARNING"},
        ],
        required=True,
        exit_code=0,
    )

    assert summary["ok"] is False
    assert summary["blocking"] == ["skills-lock:WARNING"]


def test_summarize_checks_fails_closed_on_runner_exit_code() -> None:
    module = _load_module()

    summary = module.summarize_checks(
        [{"id": "skill-docs", "status": "SUCCESS"}],
        required=True,
        exit_code=2,
    )

    assert summary["ok"] is False
    assert summary["blocking"] == ["runner-exit-code:2"]


def test_validate_repository_skill_bundle_reports_expected_outputs() -> None:
    module = _load_module()
    summary = module.validate_repository_skill_bundle(_REPO_ROOT)

    assert summary["ok"] is True
    assert summary["required_skill_count"] == 6
    assert "canonical-vs-legacy map" in summary["outputs"]
    assert "risk register" in summary["outputs"]
    assert "product-fit memo" in summary["outputs"]


def test_validate_repository_skill_bundle_fails_when_a_required_skill_is_missing(tmp_path: Path) -> None:
    module = _load_module()
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".claude" / "skills" / "canonical-architecture-truth").mkdir(parents=True)
    (repo / ".claude" / "skills" / "canonical-architecture-truth" / "SKILL.md").write_text(
        "---\nname: canonical-architecture-truth\n---\n## Purpose\nx\n## When to Use\nx\n## Required Evidence\nx\n## Outputs\nx\n",
        encoding="utf-8",
    )
    (repo / "skills-lock.json").write_text(
        json.dumps(
            {
                "version": 2,
                "emitted_events": ["pipeline.event"],
                "skills": {
                    "canonical-architecture-truth": {
                        "source": "groupthinking/EventRelay",
                        "sourceType": "local",
                        "skillPath": ".claude/skills/canonical-architecture-truth/SKILL.md",
                        "computedHash": "test",
                        "subscribed_triggers": [],
                    }
                },
            }
        ),
        encoding="utf-8",
    )

    summary = module.validate_repository_skill_bundle(repo)

    assert summary["ok"] is False
    assert any(
        "missing required skill registrations" in item for item in summary["blocking"]
    )
