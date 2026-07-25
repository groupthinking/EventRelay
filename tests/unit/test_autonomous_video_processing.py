"""Unit tests for the extracted autonomous video processing batch runner."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = REPO_ROOT / "scripts" / "ci"

TEST_VIDEO_ID = "auJzb1D-fag"
OTHER_VIDEO_ID = "Ks-_Mh1QhMc"


def _load(module_name: str):
    path = SCRIPTS_DIR / f"{module_name}.py"
    spec = importlib.util.spec_from_file_location(module_name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


avp = _load("autonomous_video_processing")
plan = _load("autonomous_video_plan")
summary = _load("autonomous_video_summary")


class _FakeResponse:
    def __init__(self, payload: dict[str, Any]) -> None:
        self._payload = payload

    def read(self) -> bytes:
        return json.dumps(self._payload).encode()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def _opener_for(video_ids: list[str]):
    def opener(_request, timeout=None):  # noqa: ANN001
        return _FakeResponse(
            {"items": [{"id": {"videoId": vid}} for vid in video_ids]}
        )

    return opener


# --- guardrails ---------------------------------------------------------


def test_guardrails_allow_a_budgeted_run() -> None:
    budget = avp.enforce_guardrails(
        categories=["tech", "science"], videos_per_category=5, mode="full"
    )
    assert budget == {"planned_videos": 10, "planned_model_calls": 40}


def test_discovery_mode_plans_zero_model_calls() -> None:
    budget = avp.enforce_guardrails(
        categories=["tech"], videos_per_category=25, mode="discovery"
    )
    assert budget["planned_model_calls"] == 0


def test_guardrail_fails_closed_on_video_cap() -> None:
    with pytest.raises(avp.GuardrailError, match="max_videos_per_run"):
        avp.enforce_guardrails(
            categories=["a", "b", "c", "d"],
            videos_per_category=25,
            mode="discovery",
            max_videos_per_run=50,
        )


def test_guardrail_fails_closed_on_model_call_cap() -> None:
    with pytest.raises(avp.GuardrailError, match="max_model_calls"):
        avp.enforce_guardrails(
            categories=["tech"],
            videos_per_category=40,
            mode="full",
            max_videos_per_run=100,
            max_model_calls=100,
        )


# --- secrets ------------------------------------------------------------


def test_missing_secrets_reported_per_mode() -> None:
    assert avp.check_required_secrets("full", {}) == ["YOUTUBE_API_KEY", "GEMINI_API_KEY"]
    assert avp.check_required_secrets("discovery", {"YOUTUBE_API_KEY": "k"}) == []
    assert avp.check_required_secrets("full", {"YOUTUBE_API_KEY": " "}) == [
        "YOUTUBE_API_KEY",
        "GEMINI_API_KEY",
    ]


# --- correlation IDs ----------------------------------------------------


def test_correlation_id_is_deterministic_and_carries_video_id() -> None:
    first = avp.correlation_id_for("42", "tech", TEST_VIDEO_ID)
    second = avp.correlation_id_for("42", "tech", TEST_VIDEO_ID)
    assert first == second
    assert first.startswith(f"{TEST_VIDEO_ID}-")
    assert first != avp.correlation_id_for("43", "tech", TEST_VIDEO_ID)


# --- status derivation --------------------------------------------------


def _records(**statuses: str) -> list[dict[str, Any]]:
    return [
        {"stage": stage, "status": statuses.get(stage, "success"), "error": None}
        for stage, _role, _pipeline in avp.STAGES
    ]


def test_video_is_delivered_only_when_every_stage_succeeds() -> None:
    assert avp.video_status(_records(), "full") == "delivered"


def test_terminal_qa_stage_blocks_delivery() -> None:
    assert avp.video_status(_records(sentinel="not_implemented"), "full") == "blocked"


def test_failed_stage_yields_failed_video() -> None:
    assert avp.video_status(_records(prism="failed"), "full") == "failed"


def test_discovery_mode_never_claims_delivery() -> None:
    assert avp.video_status(_records(), "discovery") == "discovered"


# --- stage execution ----------------------------------------------------


def test_unimplemented_stage_halts_and_skips_downstream() -> None:
    records = avp.run_stages(
        video_id=TEST_VIDEO_ID, correlation_id="cid", mode="full", runners={}
    )
    assert [record["status"] for record in records] == [
        "not_implemented",
        "skipped",
        "skipped",
        "skipped",
    ]
    assert all(record["correlation_id"] == "cid" for record in records)


def test_stage_failure_is_recorded_as_evidence() -> None:
    def boom(_context: dict[str, Any]) -> dict[str, Any]:
        raise ValueError("no transcript")

    runners = {stage: (boom if stage == "atlas" else (lambda _c: {})) for stage, _r, _p in avp.STAGES}
    records = avp.run_stages(
        video_id=TEST_VIDEO_ID, correlation_id="cid", mode="full", runners=runners
    )
    assert records[0]["status"] == "failed"
    assert "ValueError: no transcript" in records[0]["error"]


def test_all_stages_succeed_when_runners_registered() -> None:
    runners = {stage: (lambda _c: {"ok": True}) for stage, _r, _p in avp.STAGES}
    records = avp.run_stages(
        video_id=TEST_VIDEO_ID, correlation_id="cid", mode="full", runners=runners
    )
    assert all(record["status"] == "success" for record in records)
    assert avp.video_status(records, "full") == "delivered"


# --- end to end over the manifest tree ----------------------------------


def test_process_category_writes_manifest_tree(tmp_path: Path) -> None:
    manifest = avp.process_category(
        category="tech",
        videos_per_category=2,
        mode="discovery",
        run_id="99",
        output_dir=tmp_path,
        api_key="key",
        opener=_opener_for([TEST_VIDEO_ID, OTHER_VIDEO_ID]),
    )

    assert manifest["final_status"] == "discovery-only"
    assert manifest["discovered"] == 2
    assert manifest["counts"]["delivered"] == 0

    run_json = json.loads((tmp_path / "run.json").read_text())
    assert run_json["schema_version"] == avp.SCHEMA_VERSION

    video_manifest = json.loads(
        (tmp_path / "videos" / TEST_VIDEO_ID / "manifest.json").read_text()
    )
    assert video_manifest["correlation_id"] == avp.correlation_id_for(
        "99", "tech", TEST_VIDEO_ID
    )
    assert [stage["stage"] for stage in video_manifest["stages"]] == [
        "atlas",
        "prism",
        "forge",
        "sentinel",
    ]

    for stage, _role, _pipeline in avp.STAGES:
        stage_path = tmp_path / "videos" / TEST_VIDEO_ID / "stages" / f"{stage}.json"
        record = json.loads(stage_path.read_text())
        assert record["correlation_id"] == video_manifest["correlation_id"]


def test_full_mode_without_agents_is_blocked_not_processed(tmp_path: Path) -> None:
    manifest = avp.process_category(
        category="tech",
        videos_per_category=1,
        mode="full",
        run_id="99",
        output_dir=tmp_path,
        api_key="key",
        opener=_opener_for([TEST_VIDEO_ID]),
        runners={},
    )
    assert manifest["final_status"] == "blocked"
    assert manifest["counts"]["delivered"] == 0


def test_zero_discovery_fails_closed(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match="zero videos"):
        avp.process_category(
            category="tech",
            videos_per_category=3,
            mode="discovery",
            run_id="99",
            output_dir=tmp_path,
            api_key="key",
            opener=_opener_for([]),
        )


def test_dry_run_skips_stage_execution(tmp_path: Path) -> None:
    manifest = avp.process_category(
        category="tech",
        videos_per_category=1,
        mode="full",
        run_id="99",
        output_dir=tmp_path,
        api_key="key",
        dry_run=True,
        opener=_opener_for([TEST_VIDEO_ID]),
    )
    assert manifest["final_status"] == "dry-run"
    assert not (tmp_path / "videos").exists()


def test_discovery_deduplicates_and_truncates() -> None:
    ids = avp.discover_videos(
        "tech", 2, "key", opener=_opener_for([TEST_VIDEO_ID, TEST_VIDEO_ID, OTHER_VIDEO_ID, "aaaaaaaaaaa"])
    )
    assert ids == [TEST_VIDEO_ID, OTHER_VIDEO_ID]


# --- plan script --------------------------------------------------------


def test_plan_builds_matrix(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    output = tmp_path / "gh_output"
    monkeypatch.setenv("CATEGORIES", "tech, science ,")
    monkeypatch.setenv("VIDEOS_PER_CATEGORY", "5")
    monkeypatch.setenv("PIPELINE_MODE", "discovery")
    monkeypatch.setenv("GITHUB_OUTPUT", str(output))
    assert plan.main() == 0
    line = output.read_text().strip()
    assert json.loads(line.split("matrix=", 1)[1]) == {
        "include": [{"category": "tech"}, {"category": "science"}]
    }


def test_plan_fails_closed_over_cap(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CATEGORIES", "tech,science,education,news")
    monkeypatch.setenv("VIDEOS_PER_CATEGORY", "25")
    monkeypatch.setenv("PIPELINE_MODE", "discovery")
    monkeypatch.setenv("MAX_VIDEOS_PER_RUN", "50")
    monkeypatch.delenv("GITHUB_OUTPUT", raising=False)
    assert plan.main() == 1


# --- summary script -----------------------------------------------------


def test_summary_takes_worst_category_status() -> None:
    result = summary.aggregate(
        [
            {"category": "tech", "final_status": "delivered", "discovered": 2,
             "counts": {"delivered": 2, "blocked": 0, "failed": 0}},
            {"category": "news", "final_status": "blocked", "discovered": 2,
             "counts": {"delivered": 0, "blocked": 2, "failed": 0}},
        ],
        "success",
    )
    assert result["final_status"] == "blocked"
    assert result["delivered"] == 2
    assert result["blocked"] == 2


def test_summary_without_manifests_is_failed() -> None:
    result = summary.aggregate([], "success")
    assert result["final_status"] == "failed"
    assert "no run manifests" in result["reason"]


def test_summary_downgrades_delivery_when_a_matrix_job_failed() -> None:
    result = summary.aggregate(
        [{"category": "tech", "final_status": "delivered", "discovered": 1,
          "counts": {"delivered": 1, "blocked": 0, "failed": 0}}],
        "failure",
    )
    assert result["final_status"] == "blocked"
