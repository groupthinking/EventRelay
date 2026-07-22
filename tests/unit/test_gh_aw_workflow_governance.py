from __future__ import annotations

import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]



def _load_yaml(path: Path) -> dict:
    assert path.exists(), f"Expected file to exist: {path}"
    return yaml.safe_load(path.read_text())



def test_coverage_workflow_is_authoritative() -> None:
    workflow = _load_yaml(ROOT / ".github/workflows/coverage.yml")
    steps = workflow["jobs"]["coverage"]["steps"]
    run_step = next(step for step in steps if step.get("name") == "Run tests with coverage")

    assert "continue-on-error" not in run_step
    run_script = run_step["run"]
    assert "--cov-fail-under=90" in run_script
    assert "|| true" not in run_script



def test_obsolete_agentic_verification_loop_removed() -> None:
    assert not (ROOT / ".github/agentic/verification-loop.aw.yml").exists()



def test_gh_aw_validation_pins_runtime_version() -> None:
    workflow = _load_yaml(ROOT / ".github/workflows/gh-aw-validation.yml")
    actions_lock = json.loads((ROOT / ".github/aw/actions-lock.json").read_text())

    assert workflow["name"] == "gh-aw Validation"
    entry = actions_lock["entries"]["github/gh-aw-actions/setup@v0.82.14"]
    assert entry["sha"] == "b6d1443e05b8716267fa19425b99aa4f12006b4a"
    step_scripts = [step.get("run", "") for step in workflow["jobs"]["validate-gh-aw"]["steps"]]
    combined = "\n".join(step_scripts)
    assert "gh extension install github/gh-aw --pin v0.82.14" in combined
    assert "eventrelay-ci-investigator" in combined
    assert "canonical-pr-remediator" in combined
    assert "focused-coverage-controller" in combined
