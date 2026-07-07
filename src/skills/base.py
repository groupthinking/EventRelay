"""Base class for all GTM skills."""

from __future__ import annotations

import abc
import logging
import os
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class SkillResult:
    """Result returned by a skill execution."""

    status: str  # "success", "error", "skipped"
    output: dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None


class BaseSkill(abc.ABC):
    """Abstract base class for GTM skills.

    Each skill must define:
      - skill_id: unique identifier
      - name: human-readable name
      - version: semver version string
      - triggers: list of event types that trigger this skill
      - required_env_vars: env vars needed at runtime
    """

    skill_id: str
    name: str
    version: str
    triggers: list[str]
    required_env_vars: list[str] = []

    def get_env(self) -> dict[str, str]:
        """Collect required environment variables for subprocess pass-through.

        Returns only the vars that are set in the current process environment.
        This implements the MCP environment pass-through requirement (no
        reliance on environment inheritance).
        """
        env: dict[str, str] = {}
        for var in self.required_env_vars:
            val = os.environ.get(var)
            if val is not None:
                env[var] = val
        return env

    @abc.abstractmethod
    async def execute(self, payload: dict[str, Any]) -> SkillResult:
        """Execute the skill with the given payload."""
        ...

    def matches_trigger(self, event_type: str) -> bool:
        """Check if this skill should be triggered by the given event."""
        return event_type in self.triggers

    def to_dict(self) -> dict[str, Any]:
        """Serialize skill metadata."""
        return {
            "id": self.skill_id,
            "name": self.name,
            "version": self.version,
            "triggers": self.triggers,
            "required_env_vars": self.required_env_vars,
        }
