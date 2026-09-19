"""Runtime skill for orchestrating repository research outputs."""

from __future__ import annotations

from typing import Any

from skills.base import SkillResult
from skills.repository_research_common import EvidenceBackedSkill

_EXECUTION_ORDER = [
    "canonical-architecture-truth",
    "persistence-and-boundary-truth",
    "engineering-risk-and-duplication-audit",
    "github-ops-and-workflow-health",
    "product-positioning-and-buyer-fit",
]

_REQUIRED_CHILD_OUTPUTS = {
    "canonical-architecture-truth": ["canonical_vs_legacy_map"],
    "persistence-and-boundary-truth": [
        "persistence_truth_map",
        "security_boundary_map",
    ],
    "engineering-risk-and-duplication-audit": ["risk_register"],
    "github-ops-and-workflow-health": ["workflow_health_report"],
    "product-positioning-and-buyer-fit": ["product_fit_memo"],
}


class AgentOperatingHarnessSkill(EvidenceBackedSkill):
    """Compose repository research skill outputs under a fail-closed harness."""

    skill_id = "agent-operating-harness"
    name = "Agent Operating Harness"
    version = "1.0.0"
    triggers: list[str] = []
    required_env_vars: list[str] = []

    def __init__(self, dependencies: dict[str, Any] | None = None):
        super().__init__(dependencies)

    async def execute(self, payload: dict[str, Any]) -> SkillResult:
        evidence_sources = self._evidence_sources(payload)
        if evidence_sources is None:
            return self._evidence_error()

        skill_outputs = payload.get("skill_outputs")
        if not isinstance(skill_outputs, dict):
            return SkillResult(status="error", error="Missing required fields: skill_outputs")

        missing_skills = [
            skill_id for skill_id in _EXECUTION_ORDER if skill_id not in skill_outputs
        ]
        if missing_skills:
            return SkillResult(
                status="error",
                error=f"missing skill outputs: {', '.join(missing_skills)}",
            )

        aggregated_evidence = list(evidence_sources)
        remediation_sequence: list[dict[str, str]] = []
        output: dict[str, Any] = {
            "evidence_sources": aggregated_evidence,
            "execution_order": list(_EXECUTION_ORDER),
        }

        output_aliases = {
            "canonical-architecture-truth": "canonical-vs-legacy map",
            "persistence-and-boundary-truth": "persistence truth map",
            "github-ops-and-workflow-health": "workflow health report",
            "product-positioning-and-buyer-fit": "product-fit memo",
        }

        for skill_id in _EXECUTION_ORDER:
            child = skill_outputs[skill_id]
            if not isinstance(child, dict):
                return SkillResult(status="error", error=f"{skill_id} output must be a dict")
            child_evidence = child.get("evidence_sources")
            if not isinstance(child_evidence, list) or not child_evidence:
                return SkillResult(
                    status="error",
                    error=f"{skill_id} missing evidence_sources; fail closed on missing evidence",
                )
            aggregated_evidence.extend(
                item for item in child_evidence if isinstance(item, str) and item not in aggregated_evidence
            )

            required_outputs = _REQUIRED_CHILD_OUTPUTS[skill_id]
            missing_outputs = [name for name in required_outputs if name not in child]
            if missing_outputs:
                return SkillResult(
                    status="error",
                    error=f"{skill_id} missing required outputs: {', '.join(missing_outputs)}",
                )

            for required_name in required_outputs:
                alias = output_aliases.get(skill_id)
                value = child[required_name]
                if required_name == "security_boundary_map":
                    output["security boundary map"] = value
                elif alias:
                    output[alias] = value
                else:
                    output[required_name.replace("_", " ")] = value

            for action in child.get("recommended_actions", []):
                if isinstance(action, str) and action.strip():
                    remediation_sequence.append(
                        {
                            "skill": skill_id,
                            "action": action.strip(),
                            "verification_gate": "fresh first-hand evidence recorded",
                        }
                    )

        output["remediation sequence with verification gates"] = remediation_sequence
        return SkillResult(status="success", output=output)
