"""Runtime skill for persistence and security boundary synthesis."""

from __future__ import annotations

from typing import Any

from skills.base import SkillResult
from skills.repository_research_common import EvidenceBackedSkill


class PersistenceAndBoundaryTruthSkill(EvidenceBackedSkill):
    """Map persistence surfaces and security boundaries from verified evidence."""

    skill_id = "persistence-and-boundary-truth"
    name = "Persistence And Boundary Truth"
    version = "1.0.0"
    triggers: list[str] = []
    required_env_vars: list[str] = []

    def __init__(self, dependencies: dict[str, Any] | None = None):
        super().__init__(dependencies)

    async def execute(self, payload: dict[str, Any]) -> SkillResult:
        evidence_sources = self._evidence_sources(payload)
        if evidence_sources is None:
            return self._evidence_error()

        required = ["persistence_truth_map", "security_boundary_map"]
        missing = self._missing_fields(payload, required)
        if missing:
            return self._missing_fields_error(missing)

        return SkillResult(
            status="success",
            output={
                "evidence_sources": evidence_sources,
                "persistence_truth_map": payload["persistence_truth_map"],
                "security_boundary_map": payload["security_boundary_map"],
                "contradictions": payload.get("contradictions", []),
                "recommended_actions": self._recommended_actions(payload),
            },
        )
