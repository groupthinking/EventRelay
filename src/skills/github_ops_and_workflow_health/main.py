"""Runtime skill for GitHub workflow and automation health synthesis."""

from __future__ import annotations

from typing import Any

from skills.base import SkillResult
from skills.repository_research_common import EvidenceBackedSkill


class GitHubOpsAndWorkflowHealthSkill(EvidenceBackedSkill):
    """Summarize GitHub workflow health from verified repo and run evidence."""

    skill_id = "github-ops-and-workflow-health"
    name = "GitHub Ops And Workflow Health"
    version = "1.0.0"
    triggers: list[str] = []
    required_env_vars: list[str] = []

    def __init__(self, dependencies: dict[str, Any] | None = None):
        super().__init__(dependencies)

    async def execute(self, payload: dict[str, Any]) -> SkillResult:
        evidence_sources = self._evidence_sources(payload)
        if evidence_sources is None:
            return self._evidence_error()

        missing = self._missing_fields(payload, ["workflow_health_report"])
        if missing:
            return self._missing_fields_error(missing)

        return SkillResult(
            status="success",
            output={
                "evidence_sources": evidence_sources,
                "workflow_health_report": payload["workflow_health_report"],
                "recommended_actions": self._recommended_actions(payload),
            },
        )
