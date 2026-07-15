"""
Skills Event Contract Validator
================================

Validates that every event trigger subscribed to by a skill has a
corresponding registered emitter in the system.

Problem being solved
--------------------
``skills-lock.json`` validates *structure* at discovery time (source, path,
hash) but silently ignores whether the orchestrator actually **emits** the
events a skill is waiting for.  A skill that subscribes to
``content_generated`` or ``lead_scored`` will register cleanly, pass
discovery, and then *never fire* — producing quiet missing-output failures
that are invisible in tests.

This module closes that gap:

1.  ``skills-lock.json`` is extended with an ``emitted_events`` list that
    enumerates every event type the orchestrator / router chains can emit.
2.  Each skill entry may declare an optional ``subscribed_triggers`` list.
3.  ``SkillsEventValidator.validate()`` cross-references the two lists and
    raises ``SkillEventContractError`` loudly for every disconnected trigger.

Usage
-----
::

    from agents.skills_event_validator import SkillsEventValidator

    validator = SkillsEventValidator()
    validator.validate_file(Path("skills-lock.json"))  # raises on mismatch

Or imperatively::

    disconnects = validator.get_disconnected_triggers(skills_lock_dict)
    if disconnects:
        raise SkillEventContractError(...)
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class SkillEventContractError(Exception):
    """Raised when a skill subscribes to a trigger that has no registered emitter.

    This is an explicit contract violation: the skill declares it listens for
    an event that the orchestrator (or any registered emitter) never emits.
    The failure is surfaced at validation time so it is loud and testable,
    not a silent runtime no-op.
    """


# ---------------------------------------------------------------------------
# Validator
# ---------------------------------------------------------------------------


class SkillsEventValidator:
    """Validates the event contract expressed in ``skills-lock.json``.

    The ``skills-lock.json`` format is expected to contain:

    .. code-block:: json

        {
          "version": 1,
          "emitted_events": ["pipeline.event", "com.eventrelay.transcript.received", ...],
          "skills": {
            "my-skill": {
              "subscribed_triggers": ["pipeline.event"],
              ...
            }
          }
        }

    If a skill omits ``subscribed_triggers`` (or lists an empty array) the
    skill is treated as trigger-agnostic and no check is performed for it.

    If ``emitted_events`` is absent from the lock file the validator treats
    the emitted set as empty, so any skill that *does* declare triggers will
    fail the contract check.
    """

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def validate(self, skills_lock: dict[str, Any]) -> None:
        """Validate the event contract in *skills_lock*.

        Args:
            skills_lock: Parsed ``skills-lock.json`` content as a dict.

        Raises:
            SkillEventContractError: If one or more skills subscribe to a
                trigger that is not present in the ``emitted_events`` manifest.
        """
        disconnects = self.get_disconnected_triggers(skills_lock)
        if disconnects:
            lines = [
                f"  - skill '{d['skill']}' subscribes to '{d['trigger']}' "
                f"but no emitter is registered for it"
                for d in disconnects
            ]
            raise SkillEventContractError(
                f"{len(disconnects)} event contract violation(s) detected in "
                f"skills-lock.json:\n" + "\n".join(lines)
            )

    def validate_file(self, skills_lock_path: str | Path) -> None:
        """Load *skills_lock_path* as JSON and run :meth:`validate`.

        Args:
            skills_lock_path: Path to ``skills-lock.json``.

        Raises:
            FileNotFoundError: If the file does not exist.
            json.JSONDecodeError: If the file is not valid JSON.
            SkillEventContractError: If a trigger–emitter disconnect is found.
        """
        path = Path(skills_lock_path)
        skills_lock = json.loads(path.read_text(encoding="utf-8"))
        self.validate(skills_lock)
        logger.info(
            "skills-lock.json event contract OK — %d skill(s) validated",
            len(skills_lock.get("skills", {})),
        )

    def get_disconnected_triggers(
        self, skills_lock: dict[str, Any]
    ) -> list[dict[str, str]]:
        """Return all trigger–emitter disconnects without raising.

        Each item in the returned list is a dict with keys:
        - ``skill``: the skill name
        - ``trigger``: the event type that has no registered emitter

        An empty list means the contract is fully satisfied.

        Args:
            skills_lock: Parsed ``skills-lock.json`` content as a dict.
        """
        emitted_events: set[str] = set(skills_lock.get("emitted_events", []))
        disconnects: list[dict[str, str]] = []

        for skill_name, skill_data in skills_lock.get("skills", {}).items():
            if not isinstance(skill_data, dict):
                continue
            for trigger in skill_data.get("subscribed_triggers", []):
                if trigger not in emitted_events:
                    disconnects.append({"skill": skill_name, "trigger": trigger})
                    logger.warning(
                        "Event contract violation: skill '%s' subscribes to "
                        "'%s' but no emitter is registered",
                        skill_name,
                        trigger,
                    )

        return disconnects


# ---------------------------------------------------------------------------
# Module-level convenience
# ---------------------------------------------------------------------------

_DEFAULT_SKILLS_LOCK = Path(__file__).resolve().parents[2] / "skills-lock.json"


def validate_skills_lock(skills_lock_path: str | Path | None = None) -> None:
    """Convenience wrapper: validate the project ``skills-lock.json``.

    Uses the repo-root ``skills-lock.json`` by default.

    Raises:
        SkillEventContractError: On any trigger–emitter disconnect.
    """
    path = Path(skills_lock_path) if skills_lock_path else _DEFAULT_SKILLS_LOCK
    SkillsEventValidator().validate_file(path)
