"""Runtime skill for engineering risk and duplication audit synthesis."""

from __future__ import annotations

from typing import Any

from skills.base import SkillResult
from skills.repository_research_common import EvidenceBackedSkill

_SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}


class EngineeringRiskAndDuplicationAuditSkill(EvidenceBackedSkill):
    """Produce an evidence-backed, severity-ranked engineering risk register."""

    skill_id = "engineering-risk-and-duplication-audit"
    name = "Engineering Risk And Duplication Audit"
    version = "1.0.0"
    triggers: list[str] = []
    required_env_vars: list[str] = []

    def __init__(self, dependencies: dict[str, Any] | None = None):
        super().__init__(dependencies)

    async def execute(self, payload: dict[str, Any]) -> SkillResult:
        evidence_sources = self._evidence_sources(payload)
        if evidence_sources is None:
            return self._evidence_error()

        missing = self._missing_fields(payload, ["risk_register"])
        if missing:
            return self._missing_fields_error(missing)

        risks = payload["risk_register"]
        if not isinstance(risks, list):
            return SkillResult(status="error", error="'risk_register' must be a list")

        sorted_risks = sorted(
            risks,
            key=lambda item: _SEVERITY_ORDER.get(str(item.get("severity", "")).lower(), 99)
            if isinstance(item, dict)
            else 99,
        )
        return SkillResult(
            status="success",
            output={
                "evidence_sources": evidence_sources,
                "risk_register": sorted_risks,
                "recommended_actions": self._recommended_actions(payload),
            },
        )
