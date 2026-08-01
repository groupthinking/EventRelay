import json

from scripts.maintenance.automated_orchestration_scheduler import OrchestrationScheduler


def test_orchestration_scheduler_logic(tmp_path):
    # Setup a mock database path and reports directory
    db_file = tmp_path / "mock_kb.json"
    reports_dir = tmp_path / "reports"

    # Minimal kb structure
    mock_db = {
        "technologies": {},
        "videos": []
    }
    with open(db_file, "w") as f:
        json.dump(mock_db, f)

    scheduler = OrchestrationScheduler(db_path=str(db_file), reports_dir=str(reports_dir))

    # 1. Test PR scanning
    pr_review = scheduler.review_pending_prs()
    assert pr_review["total_pending_prs"] > 0
    assert "629" in pr_review["prs"]

    # 2. Test conflict/guidance resolution
    resolutions = scheduler.resolve_conflicting_guidance(pr_review)
    assert resolutions["conflicts_identified"] == 4
    types = [r["type"] for r in resolutions["resolutions"]]
    assert "tailwind_conflict" in types
    assert "ssl_duplicate_cluster" in types
    assert "obsolete_conflict_marker_fixes" in types
    assert "binary_search_duplicates" in types

    # 3. Test running full cycle
    report = scheduler.run_review_cycle(dry_run=False, consolidate_similar=False)
    assert report["dry_run"] is False
    assert report["pr_review_summary"]["total_prs_reviewed"] == 11
    assert report["guidance_resolutions"]["conflicts_identified"] == 4

    # Verify report was saved to file
    report_files = list(reports_dir.glob("auto-orchestration-report-*.json"))
    assert len(report_files) == 1
