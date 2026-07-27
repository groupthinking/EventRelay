"""Contract tests for the autonomous video processing workflow definition."""

from __future__ import annotations

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOW_PATH = REPO_ROOT / ".github/workflows/autonomous-video-processing.yml"

# PyYAML parses the bare `on:` key as the boolean True.
ON_KEY = True


def _workflow() -> dict:
    assert WORKFLOW_PATH.exists()
    return yaml.safe_load(WORKFLOW_PATH.read_text(encoding="utf-8"))


def test_workflow_is_reusable_via_workflow_call() -> None:
    triggers = _workflow()[ON_KEY]
    assert "workflow_call" in triggers
    assert "workflow_dispatch" in triggers


def test_workflow_call_inputs_mirror_dispatch_inputs() -> None:
    triggers = _workflow()[ON_KEY]
    dispatch = set(triggers["workflow_dispatch"]["inputs"])
    call = set(triggers["workflow_call"]["inputs"])
    assert dispatch == call


def test_workflow_call_declares_secrets_and_outputs() -> None:
    call = _workflow()[ON_KEY]["workflow_call"]
    assert call["secrets"]["YOUTUBE_API_KEY"]["required"] is True
    assert "GEMINI_API_KEY" in call["secrets"]
    assert set(call["outputs"]) == {"final_status", "delivered", "blocked"}


def test_no_inline_python_heredoc_remains() -> None:
    body = WORKFLOW_PATH.read_text(encoding="utf-8")
    assert "python - <<" not in body
    assert "processed += 1" not in body
    assert "scripts/ci/autonomous_video_processing.py" in body


def test_referenced_scripts_exist() -> None:
    for script in (
        "autonomous_video_plan.py",
        "autonomous_video_processing.py",
        "autonomous_video_summary.py",
    ):
        assert (REPO_ROOT / "scripts" / "ci" / script).exists()


def test_secrets_are_validated_before_processing() -> None:
    prepare = _workflow()["jobs"]["prepare"]
    step = next(
        step for step in prepare["steps"] if step.get("name") == "Validate required secrets"
    )
    assert "exit 1" in step["run"]


def test_evidence_retained_for_thirty_days() -> None:
    steps = _workflow()["jobs"]["process"]["steps"]
    upload = next(step for step in steps if step.get("name") == "Upload run evidence")
    assert upload["with"]["retention-days"] == 30


def test_deliverables_published_only_when_delivered() -> None:
    steps = _workflow()["jobs"]["process"]["steps"]
    publish = next(step for step in steps if step.get("name") == "Publish deliverables")
    assert publish["if"] == "steps.process.outputs.final_status == 'delivered'"
    assert publish["with"]["retention-days"] == 30


def test_workflow_has_a_concurrency_guard() -> None:
    workflow = _workflow()
    assert workflow["concurrency"]["group"].startswith("autonomous-video-processing-")


def test_guardrail_inputs_are_exposed() -> None:
    inputs = _workflow()[ON_KEY]["workflow_dispatch"]["inputs"]
    assert "max_videos_per_run" in inputs
    assert "max_model_calls" in inputs
    assert inputs["pipeline_mode"]["options"] == ["discovery", "full"]
