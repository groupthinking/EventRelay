"""Unit tests for agents.skills_event_validator.

Tests cover:
- SkillsEventValidator.validate() happy and error paths
- SkillsEventValidator.validate_file() with temp JSON files
- SkillsEventValidator.get_disconnected_triggers() return shape
- validate_skills_lock() convenience wrapper
- Backward-compat: skills without subscribed_triggers pass unchanged
"""

from __future__ import annotations

import importlib
import json
import sys
import types
from pathlib import Path
from typing import Any

import pytest

# -------------------------------------------------------------------------
# Ensure src is on the import path and stub heavy agents/__init__.py to
# avoid transitive aiohttp / websockets dependencies at collection time.
# -------------------------------------------------------------------------
_SRC = Path(__file__).resolve().parents[2] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

# Stub the agents package so its __init__.py (which imports aiohttp etc.)
# is never executed.  The same technique is used in test_skill_builder.py
# for the youtube_extension.services package.
if "agents" not in sys.modules:
    _agents_stub = types.ModuleType("agents")
    _agents_stub.__path__ = [str(_SRC / "agents")]
    _agents_stub.__package__ = "agents"
    sys.modules["agents"] = _agents_stub

# Force fresh import of the specific submodule we want to test.
sys.modules.pop("agents.skills_event_validator", None)

from agents.skills_event_validator import (  # noqa: E402
    SkillEventContractError,
    SkillsEventValidator,
    validate_skills_lock,
)

# -------------------------------------------------------------------------
# Fixtures / helpers
# -------------------------------------------------------------------------

_KNOWN_EVENTS = [
    "pipeline.event",
    "com.eventrelay.transcript.received",
    "com.eventrelay.transcript.completed",
]


def _lock(
    emitted: list[str] | None = None,
    skills: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a minimal skills-lock dict for testing."""
    return {
        "version": 2,
        "emitted_events": emitted if emitted is not None else list(_KNOWN_EVENTS),
        "skills": skills or {},
    }


def _skill(triggers: list[str]) -> dict[str, Any]:
    """Return a minimal skill entry with the given subscribed_triggers."""
    return {
        "source": "test/repo",
        "sourceType": "github",
        "skillPath": "skills/test/SKILL.md",
        "computedHash": "abc123",
        "subscribed_triggers": triggers,
    }


# =========================================================================
# SkillEventContractError
# =========================================================================


class TestSkillEventContractError:
    def test_is_exception_subclass(self):
        assert issubclass(SkillEventContractError, Exception)

    def test_message_preserved(self):
        err = SkillEventContractError("broken contract")
        assert "broken contract" in str(err)


# =========================================================================
# SkillsEventValidator.get_disconnected_triggers
# =========================================================================


class TestGetDisconnectedTriggers:
    def setup_method(self):
        self.validator = SkillsEventValidator()

    def test_empty_skills_returns_empty_list(self):
        assert self.validator.get_disconnected_triggers(_lock()) == []

    def test_skill_with_no_triggers_returns_empty(self):
        lock = _lock(skills={"my-skill": _skill([])})
        assert self.validator.get_disconnected_triggers(lock) == []

    def test_skill_without_triggers_key_returns_empty(self):
        lock = _lock(
            skills={
                "my-skill": {
                    "source": "a/b",
                    "sourceType": "github",
                    "skillPath": "x.md",
                    "computedHash": "ff",
                }
            }
        )
        assert self.validator.get_disconnected_triggers(lock) == []

    def test_trigger_in_emitted_events_no_disconnect(self):
        lock = _lock(skills={"my-skill": _skill(["pipeline.event"])})
        assert self.validator.get_disconnected_triggers(lock) == []

    def test_trigger_not_in_emitted_events_returns_disconnect(self):
        lock = _lock(skills={"my-skill": _skill(["content_generated"])})
        result = self.validator.get_disconnected_triggers(lock)
        assert len(result) == 1
        assert result[0]["skill"] == "my-skill"
        assert result[0]["trigger"] == "content_generated"

    def test_multiple_disconnected_triggers_all_returned(self):
        lock = _lock(
            skills={
                "skill-a": _skill(["content_generated", "lead_scored"]),
            }
        )
        result = self.validator.get_disconnected_triggers(lock)
        triggers = {r["trigger"] for r in result}
        assert "content_generated" in triggers
        assert "lead_scored" in triggers
        assert all(r["skill"] == "skill-a" for r in result)

    def test_multiple_skills_each_violation_reported(self):
        lock = _lock(
            skills={
                "skill-a": _skill(["unknown.event.a"]),
                "skill-b": _skill(["unknown.event.b"]),
            }
        )
        result = self.validator.get_disconnected_triggers(lock)
        assert len(result) == 2
        skill_names = {r["skill"] for r in result}
        assert "skill-a" in skill_names
        assert "skill-b" in skill_names

    def test_partial_match_only_unknown_triggers_reported(self):
        lock = _lock(
            skills={
                "skill-mixed": _skill(["pipeline.event", "unknown.event"]),
            }
        )
        result = self.validator.get_disconnected_triggers(lock)
        assert len(result) == 1
        assert result[0]["trigger"] == "unknown.event"

    def test_missing_emitted_events_key_treats_as_empty_set(self):
        lock = {"version": 2, "skills": {"skill-x": _skill(["pipeline.event"])}}
        result = self.validator.get_disconnected_triggers(lock)
        assert len(result) == 1
        assert result[0]["trigger"] == "pipeline.event"

    def test_empty_emitted_events_list_triggers_all_fail(self):
        lock = _lock(emitted=[], skills={"s": _skill(["any.event"])})
        result = self.validator.get_disconnected_triggers(lock)
        assert len(result) == 1

    def test_result_items_have_skill_and_trigger_keys(self):
        lock = _lock(skills={"s": _skill(["gone.event"])})
        result = self.validator.get_disconnected_triggers(lock)
        assert "skill" in result[0]
        assert "trigger" in result[0]

    def test_non_dict_skill_entry_is_skipped(self):
        lock = _lock(skills={"broken": "not-a-dict"})
        assert self.validator.get_disconnected_triggers(lock) == []


# =========================================================================
# SkillsEventValidator.validate
# =========================================================================


class TestValidate:
    def setup_method(self):
        self.validator = SkillsEventValidator()

    def test_valid_lock_does_not_raise(self):
        lock = _lock(skills={"s": _skill(["pipeline.event"])})
        self.validator.validate(lock)  # must not raise

    def test_no_skills_does_not_raise(self):
        self.validator.validate(_lock())  # must not raise

    def test_invalid_trigger_raises_skill_event_contract_error(self):
        lock = _lock(skills={"s": _skill(["content_generated"])})
        with pytest.raises(SkillEventContractError):
            self.validator.validate(lock)

    def test_error_message_contains_skill_name(self):
        lock = _lock(skills={"my-bad-skill": _skill(["ghost.event"])})
        with pytest.raises(SkillEventContractError, match="my-bad-skill"):
            self.validator.validate(lock)

    def test_error_message_contains_trigger_name(self):
        lock = _lock(skills={"s": _skill(["ghost.event"])})
        with pytest.raises(SkillEventContractError, match="ghost.event"):
            self.validator.validate(lock)

    def test_error_message_contains_violation_count(self):
        lock = _lock(
            skills={
                "a": _skill(["event.x"]),
                "b": _skill(["event.y"]),
            }
        )
        with pytest.raises(SkillEventContractError, match="2 event contract violation"):
            self.validator.validate(lock)

    def test_mixed_valid_invalid_triggers_raises(self):
        # skill-a is fine, skill-b is broken
        lock = _lock(
            skills={
                "skill-a": _skill(["pipeline.event"]),
                "skill-b": _skill(["lead_scored"]),
            }
        )
        with pytest.raises(SkillEventContractError):
            self.validator.validate(lock)

    def test_all_skills_with_empty_triggers_passes(self):
        lock = _lock(
            skills={
                "a": _skill([]),
                "b": _skill([]),
                "c": _skill([]),
            }
        )
        self.validator.validate(lock)  # must not raise

    def test_backward_compat_v1_format_without_triggers(self):
        """v1 skills-lock without subscribed_triggers or emitted_events should pass."""
        lock_v1 = {
            "version": 1,
            "skills": {
                "firebase-basics": {
                    "source": "firebase/agent-skills",
                    "sourceType": "github",
                    "skillPath": "skills/firebase-basics/SKILL.md",
                    "computedHash": "88fb9ee785fa7aaa74b2c662e53b2aca0b9ee4b67c84587ee017460f54b97471",
                }
            },
        }
        self.validator.validate(lock_v1)  # must not raise (backward compat)


# =========================================================================
# SkillsEventValidator.validate_file
# =========================================================================


class TestValidateFile:
    def setup_method(self):
        self.validator = SkillsEventValidator()

    def test_valid_file_does_not_raise(self, tmp_path):
        lock_file = tmp_path / "skills-lock.json"
        lock_file.write_text(json.dumps(_lock(skills={"s": _skill(["pipeline.event"])})))
        self.validator.validate_file(lock_file)  # must not raise

    def test_invalid_file_raises_skill_event_contract_error(self, tmp_path):
        lock_file = tmp_path / "skills-lock.json"
        lock_file.write_text(json.dumps(_lock(skills={"s": _skill(["ghost.event"])})))
        with pytest.raises(SkillEventContractError):
            self.validator.validate_file(lock_file)

    def test_missing_file_raises_file_not_found(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            self.validator.validate_file(tmp_path / "nonexistent.json")

    def test_invalid_json_raises_json_decode_error(self, tmp_path):
        bad = tmp_path / "bad.json"
        bad.write_text("{not valid json")
        with pytest.raises(json.JSONDecodeError):
            self.validator.validate_file(bad)

    def test_accepts_string_path(self, tmp_path):
        lock_file = tmp_path / "skills-lock.json"
        lock_file.write_text(json.dumps(_lock()))
        self.validator.validate_file(str(lock_file))  # must not raise


# =========================================================================
# validate_skills_lock convenience wrapper
# =========================================================================


class TestValidateSkillsLock:
    def test_valid_custom_path_does_not_raise(self, tmp_path):
        lock_file = tmp_path / "skills-lock.json"
        lock_file.write_text(json.dumps(_lock()))
        validate_skills_lock(lock_file)  # must not raise

    def test_custom_path_with_disconnect_raises(self, tmp_path):
        lock_file = tmp_path / "skills-lock.json"
        lock_file.write_text(json.dumps(_lock(skills={"x": _skill(["bad.event"])})))
        with pytest.raises(SkillEventContractError):
            validate_skills_lock(lock_file)


# =========================================================================
# Integration: validate the real skills-lock.json in the repo
# =========================================================================

# Resolve the repo-root skills-lock.json relative to this test file.
_REPO_ROOT = Path(__file__).resolve().parents[2]
_SKILLS_LOCK_PATH = _REPO_ROOT / "skills-lock.json"


class TestRealSkillsLock:
    """Validates that the committed skills-lock.json satisfies the event contract.

    This acts as a living regression guard: if a developer adds a skill with
    a ``subscribed_triggers`` entry that has no corresponding ``emitted_events``
    entry, this test will fail loudly instead of silently.
    """

    def test_skills_lock_file_exists(self):
        assert _SKILLS_LOCK_PATH.exists(), (
            f"skills-lock.json not found at {_SKILLS_LOCK_PATH}; "
            "did the file get moved or deleted?"
        )

    def test_skills_lock_is_valid_json(self):
        content = _SKILLS_LOCK_PATH.read_text(encoding="utf-8")
        lock = json.loads(content)
        assert isinstance(lock, dict)

    def test_skills_lock_has_emitted_events_key(self):
        lock = json.loads(_SKILLS_LOCK_PATH.read_text(encoding="utf-8"))
        assert "emitted_events" in lock, (
            "skills-lock.json is missing the 'emitted_events' manifest. "
            "Add an emitted_events list so trigger→emitter contracts can be validated."
        )

    def test_emitted_events_is_non_empty_list(self):
        lock = json.loads(_SKILLS_LOCK_PATH.read_text(encoding="utf-8"))
        assert isinstance(lock.get("emitted_events"), list)
        assert len(lock["emitted_events"]) > 0

    def test_no_event_contract_violations(self):
        """Main contract gate: all subscribed_triggers must have registered emitters."""
        validate_skills_lock(_SKILLS_LOCK_PATH)  # raises SkillEventContractError on violation

    def test_all_skill_entries_have_subscribed_triggers_key(self):
        lock = json.loads(_SKILLS_LOCK_PATH.read_text(encoding="utf-8"))
        missing = [
            name
            for name, data in lock.get("skills", {}).items()
            if isinstance(data, dict) and "subscribed_triggers" not in data
        ]
        assert not missing, (
            f"The following skills are missing 'subscribed_triggers' (add [] if none): "
            f"{missing}"
        )


# =========================================================================
# Integration: emit → skill trigger flow simulation
# =========================================================================


class TestEmitToSkillTriggerFlow:
    """Verifies the full emit → skill trigger resolution path.

    Uses a simple in-process event bus to ensure that when an event is
    emitted that matches a skill's subscribed_triggers, the skill is
    correctly identified as triggered.
    """

    def _build_trigger_index(self, skills_lock: dict) -> dict[str, list[str]]:
        """Build {event_type: [skill_name, ...]} index from skills-lock."""
        index: dict[str, list[str]] = {}
        for skill_name, skill_data in skills_lock.get("skills", {}).items():
            if not isinstance(skill_data, dict):
                continue
            for trigger in skill_data.get("subscribed_triggers", []):
                index.setdefault(trigger, []).append(skill_name)
        return index

    def test_emitting_known_event_triggers_subscribed_skills(self):
        lock = _lock(
            emitted=["pipeline.event", "com.eventrelay.transcript.completed"],
            skills={
                "skill-pipeline": _skill(["pipeline.event"]),
                "skill-transcript": _skill(["com.eventrelay.transcript.completed"]),
                "skill-nothing": _skill([]),
            },
        )
        index = self._build_trigger_index(lock)

        # Simulate: orchestrator emits pipeline.event
        triggered = index.get("pipeline.event", [])
        assert "skill-pipeline" in triggered
        assert "skill-transcript" not in triggered
        assert "skill-nothing" not in triggered

    def test_emitting_event_not_subscribed_by_anyone_triggers_nothing(self):
        lock = _lock(
            emitted=["pipeline.event"],
            skills={
                "skill-a": _skill(["pipeline.event"]),
            },
        )
        index = self._build_trigger_index(lock)
        triggered = index.get("com.eventrelay.transcript.completed", [])
        assert triggered == []

    def test_multiple_skills_can_subscribe_to_same_event(self):
        lock = _lock(
            emitted=["pipeline.event"],
            skills={
                "skill-a": _skill(["pipeline.event"]),
                "skill-b": _skill(["pipeline.event"]),
            },
        )
        index = self._build_trigger_index(lock)
        triggered = index.get("pipeline.event", [])
        assert "skill-a" in triggered
        assert "skill-b" in triggered

    def test_disconnect_means_event_never_reaches_skill(self):
        """Demonstrates the bug: skill subscribes to event that is never emitted."""
        emitted = {"pipeline.event"}  # orchestrator only emits this
        skills_subscriptions = {"ghost-skill": {"content_generated"}}

        # Check which skills would be triggered by each emitted event
        triggered_skills: set[str] = set()
        for event in emitted:
            for skill, triggers in skills_subscriptions.items():
                if event in triggers:
                    triggered_skills.add(skill)

        # ghost-skill subscribed to content_generated which is never emitted
        assert "ghost-skill" not in triggered_skills, (
            "ghost-skill should never fire because 'content_generated' is not "
            "in the emitted_events set. This is the quiet failure the validator prevents."
        )

    def test_validator_would_catch_the_disconnect(self):
        """The validator raises loudly before the system can silently fail."""
        lock = _lock(
            emitted=["pipeline.event"],
            skills={"ghost-skill": _skill(["content_generated"])},
        )
        with pytest.raises(SkillEventContractError) as exc_info:
            SkillsEventValidator().validate(lock)
        assert "ghost-skill" in str(exc_info.value)
        assert "content_generated" in str(exc_info.value)
