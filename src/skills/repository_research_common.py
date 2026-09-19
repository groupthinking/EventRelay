"""Shared helpers for evidence-backed repository research skills."""

from __future__ import annotations

from typing import Any

from skills.base import BaseSkill, SkillResult


class EvidenceBackedSkill(BaseSkill):
    """Base class for repository research skills that fail closed on evidence gaps."""

    def _evidence_sources(self, payload: dict[str, Any]) -> list[str] | None:
        evidence = payload.get("evidence_sources")
        if not isinstance(evidence, list):
            return None
        normalized = [
            item.strip()
            for item in evidence
            if isinstance(item, str) and item.strip()
        ]
        return normalized or None

    def _recommended_actions(self, payload: dict[str, Any]) -> list[str]:
        actions = payload.get("recommended_actions", [])
        if not isinstance(actions, list):
            return []
        return [item.strip() for item in actions if isinstance(item, str) and item.strip()]

    def _missing_fields(self, payload: dict[str, Any], required: list[str]) -> list[str]:
        missing: list[str] = []
        for field in required:
            value = payload.get(field)
            if value is None:
                missing.append(field)
            elif isinstance(value, (list, dict, str)) and not value:
                missing.append(field)
        return missing

    def _evidence_error(self) -> SkillResult:
        return SkillResult(
            status="error",
            error="Missing non-empty 'evidence_sources'; fail closed on missing evidence",
        )

    def _missing_fields_error(self, missing: list[str]) -> SkillResult:
        return SkillResult(
            status="error",
            error=f"Missing required fields: {', '.join(missing)}",
        )
