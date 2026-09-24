"""Runtime skill for evidence-backed product positioning synthesis."""

from __future__ import annotations

from typing import Any

from skills.base import SkillResult
from skills.repository_research_common import EvidenceBackedSkill


class ProductPositioningAndBuyerFitSkill(EvidenceBackedSkill):
    """Separate repo facts from market judgment in product-fit analysis."""

    skill_id = "product-positioning-and-buyer-fit"
    name = "Product Positioning And Buyer Fit"
    version = "1.0.0"
    triggers: list[str] = []
    required_env_vars: list[str] = []

    def __init__(self, dependencies: dict[str, Any] | None = None):
        super().__init__(dependencies)

    async def execute(self, payload: dict[str, Any]) -> SkillResult:
        evidence_sources = self._evidence_sources(payload)
        if evidence_sources is None:
            return self._evidence_error()

        missing = self._missing_fields(payload, ["product_fit_memo"])
        if missing:
            return self._missing_fields_error(missing)

        return SkillResult(
            status="success",
            output={
                "evidence_sources": evidence_sources,
                "product_fit_memo": payload["product_fit_memo"],
                "recommended_actions": self._recommended_actions(payload),
            },
        )
