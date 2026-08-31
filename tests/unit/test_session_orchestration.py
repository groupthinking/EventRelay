import asyncio

from scripts.maintenance.session_orchestration_manager import (
    SessionOrchestrationManager,
)


def test_session_orchestration_manager_basics(tmp_path):
    state_file = tmp_path / "test_state.json"
    manager = SessionOrchestrationManager(state_path=state_file)

    # 1. Test state initialization
    assert len(manager.list_playbooks()) == 4
    assert len(manager.list_suggestions()) == 1

    # 2. Test Playbook management
    manager.create_playbook("test-playbook", "Test description", ["macro_1"])
    assert "test-playbook" in manager.list_playbooks()

    manager.update_playbook("test-playbook", description="New description")
    assert manager.list_playbooks()["test-playbook"]["description"] == "New description"

    manager.delete_playbook("test-playbook")
    assert "test-playbook" not in manager.list_playbooks()

    # 3. Test Session management
    s = manager.create_session(
        prompt="Test optimization",
        playbook="bolt-performance-remediation",
        tags=["performance"],
        acu_limit=100
    )
    session_id = s["id"]
    assert s["acu_limit"] == 100
    assert s["status"] == "running"

    # Search session
    results = manager.search_sessions(tag="performance")
    assert len(results) == 1
    assert results[0]["id"] == session_id

    # Timeline inspection
    timeline = manager.inspect_timeline(session_id)
    assert len(timeline) == 1
    assert "Session initialized" in timeline[0]["summary"]

    # Send message
    assert manager.send_message(session_id, "Hello Agent") is True
    assert len(manager.inspect_timeline(session_id)) == 2

    # Terminate session
    assert manager.terminate_session(session_id, archive=True) is True
    assert manager.state["sessions"][session_id]["status"] == "archived"


def test_session_orchestration_manager_async_parallel(tmp_path):
    state_file = tmp_path / "test_state_async.json"
    manager = SessionOrchestrationManager(state_path=state_file)

    packages = [
        {"prompt": "Audit performance", "playbook": "bolt-performance-remediation", "tags": ["perf"], "acu_limit": 50},
        {"prompt": "Audit security", "playbook": "sentinel-security-audit-and-remediation", "tags": ["sec"], "acu_limit": 60}
    ]

    completed_sessions = asyncio.run(manager.run_parallel_sessions(packages))
    assert len(completed_sessions) == 2
    for s in completed_sessions:
        assert s["status"] == "completed"
        timeline = s["timeline"]
        assert any("Parallel run complete" in event["summary"] for event in timeline)


def test_session_orchestration_manager_knowledge_and_schedule(tmp_path):
    state_file = tmp_path / "test_state_extra.json"
    manager = SessionOrchestrationManager(state_path=state_file)

    # Knowledge Note CRUD
    manager.create_knowledge_note("note_99", "event-relay", "security", "Security Headers", "headers", "Ensure X-Frame-Options is set")
    notes = manager.get_knowledge_notes(repo="event-relay", folder="security")
    assert len(notes) == 1
    assert notes[0]["id"] == "note_99"

    manager.delete_knowledge_note("note_99")
    assert len(manager.get_knowledge_notes(repo="event-relay", folder="security")) == 0

    # Suggestions Review
    suggestions = manager.list_suggestions()
    assert len(suggestions) == 1
    assert manager.review_suggestion(suggestions[0]["id"], "accepted") is True
    assert manager.list_suggestions()[0]["status"] == "accepted"

    # Schedules
    manager.create_schedule("sched_daily", "0 0 * * *", "Jules", active=True)
    assert "sched_daily" in manager.state["schedules"]
    assert manager.toggle_schedule("sched_daily", active=False) is True
    assert manager.state["schedules"]["sched_daily"]["active"] is False

    # Integrations
    integrations = manager.get_integrations()
    assert "github" in integrations
    assert integrations["github"]["installed"] is True
