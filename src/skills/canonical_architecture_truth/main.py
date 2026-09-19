"""Runtime skill for canonical architecture truth synthesis."""

from __future__ import annotations

from typing import Any

from skills.base import SkillResult
from skills.repository_research_common import EvidenceBackedSkill


class CanonicalArchitectureTruthSkill(EvidenceBackedSkill):
    """Determine canonical versus legacy architecture surfaces from verified evidence."""

    skill_id = "canonical-architecture-truth"
    name = "Canonical Architecture Truth"
    version = "1.0.0"
    triggers: list[str] = []
    required_env_vars: list[str] = []

    def __init__(self, dependencies: dict[str, Any] | None = None):
        super().__init__(dependencies)

    async def execute(self, payload: dict[str, Any]) -> SkillResult:
        evidence_sources = self._evidence_sources(payload)
        if evidence_sources is None:
            return self._evidence_error()

        required = [
            "canonical_paths",
            "legacy_surfaces",
            "public_product_name",
            "internal_runtime_name",
            "deployment_truth",
            "runtime_boundaries",
        ]
        missing = self._missing_fields(payload, required)
        if missing:
            return self._missing_fields_error(missing)

        return SkillResult(
            status="success",
            output={
                "evidence_sources": evidence_sources,
                "canonical_vs_legacy_map": {
                    "canonical_paths": payload["canonical_paths"],
                    "legacy_surfaces": payload["legacy_surfaces"],
                    "public_product_name": payload["public_product_name"],
                    "internal_runtime_name": payload["internal_runtime_name"],
                    "deployment_truth": payload["deployment_truth"],
                    "runtime_boundaries": payload["runtime_boundaries"],
                },
                "recommended_actions": self._recommended_actions(payload),
            },
        )
