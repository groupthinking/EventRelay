#!/usr/bin/env python3
"""
Skill Builder — Learning System
=================================

Tracks deployment outcomes and improves the pipeline by learning from failures
and successes. Each "skill" represents a lesson derived from a deployment
attempt: what worked, what didn't, and how to adjust future prompts or configs.

Ported from the EventRelay fork (January 2026) into the canonical
YOUTUBE-EXTENSION repository as part of the EventRelay merge.

Architecture
------------
- ``SkillBuilder`` records deployment events and derives lessons.
- Lessons are persisted as JSON in a local skills store (``~/.uvai/skills/``
  or a path provided at construction time).
- The ``AICodeGenerator`` can call ``SkillBuilder.get_context()`` to inject
  relevant lessons into its LLM prompts.
- Skill weights are updated via exponential moving average so that recent
  lessons carry more influence than older ones.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_DEFAULT_SKILLS_DIR = Path.home() / ".uvai" / "skills"
_SKILL_FILE_SUFFIX = ".skill.json"
_EMA_ALPHA = 0.3  # weight for the most recent observation
_MAX_LESSONS_PER_SKILL = 20

# ---------------------------------------------------------------------------
# Data helpers
# ---------------------------------------------------------------------------


def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def _skill_id(framework: str, deployment_target: str) -> str:
    """Stable, filesystem-safe identifier for a (framework, target) pair."""
    raw = f"{framework.lower()}::{deployment_target.lower()}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


# ---------------------------------------------------------------------------
# Core class
# ---------------------------------------------------------------------------


class SkillBuilder:
    """
    Learns from deployment outcomes and surfaces actionable lessons for
    future code generation passes.

    Usage::

        builder = SkillBuilder()

        # Record a deployment result
        await builder.record_deployment(
            framework="nextjs",
            deployment_target="vercel",
            success=True,
            error_message=None,
            config={"node_version": "20"},
        )

        # Retrieve context for AICodeGenerator
        context = builder.get_context(framework="nextjs", deployment_target="vercel")
        # → {"lessons": ["Always set NODE_VERSION=20 for Next.js on Vercel", ...], ...}
    """

    def __init__(self, skills_dir: Path | None = None) -> None:
        self.skills_dir: Path = skills_dir or Path(
            os.getenv("UVAI_SKILLS_DIR", str(_DEFAULT_SKILLS_DIR))
        )
        self.skills_dir.mkdir(parents=True, exist_ok=True)
        logger.info("SkillBuilder initialised (skills_dir=%s)", self.skills_dir)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def record_deployment(
        self,
        framework: str,
        deployment_target: str,
        success: bool,
        error_message: str | None = None,
        config: dict[str, Any] | None = None,
        generated_files: list[str] | None = None,
    ) -> None:
        """
        Record the outcome of a deployment attempt and update skill weights.

        This method is intentionally synchronous so callers do not need to
        ``await`` it inside fire-and-forget post-processing hooks.
        """
        sid = _skill_id(framework, deployment_target)
        skill = self._load_skill(sid)

        event: dict[str, Any] = {
            "timestamp": _now_iso(),
            "framework": framework,
            "deployment_target": deployment_target,
            "success": success,
            "error_message": error_message,
            "config": config or {},
            "generated_files": generated_files or [],
        }

        skill["events"].append(event)

        # Derive a lesson from this event
        lesson = self._derive_lesson(event)
        if lesson:
            self._add_lesson(skill, lesson, success)

        # Update success-rate EMA
        outcome = 1.0 if success else 0.0
        prev_rate = skill.get("success_rate", 0.5)
        skill["success_rate"] = round(
            _EMA_ALPHA * outcome + (1 - _EMA_ALPHA) * prev_rate, 4
        )
        skill["last_updated"] = _now_iso()
        skill["framework"] = framework
        skill["deployment_target"] = deployment_target

        self._save_skill(sid, skill)
        logger.info(
            "Skill recorded: %s/%s success=%s (rate=%.2f)",
            framework,
            deployment_target,
            success,
            skill["success_rate"],
        )

    def get_context(
        self,
        framework: str,
        deployment_target: str,
        max_lessons: int = 5,
    ) -> dict[str, Any]:
        """
        Return a context dict suitable for injecting into LLM prompts.

        Returns::

            {
                "lessons": ["...", ...],          # top ranked lessons
                "success_rate": 0.82,             # historical success rate
                "framework": "nextjs",
                "deployment_target": "vercel",
                "has_data": True,
            }
        """
        sid = _skill_id(framework, deployment_target)
        skill = self._load_skill(sid)

        lessons = sorted(
            skill.get("lessons", {}).items(),
            key=lambda kv: kv[1]["weight"],
            reverse=True,
        )
        top_lessons = [meta["text"] for _, meta in lessons[:max_lessons]]

        return {
            "lessons": top_lessons,
            "success_rate": skill.get("success_rate", None),
            "framework": framework,
            "deployment_target": deployment_target,
            "has_data": bool(skill.get("events")),
        }

    def list_skills(self) -> list[dict[str, Any]]:
        """Return a summary of all stored skills."""
        summaries = []
        for path in sorted(self.skills_dir.glob(f"*{_SKILL_FILE_SUFFIX}")):
            try:
                data = json.loads(path.read_text())
                summaries.append(
                    {
                        "skill_id": path.stem.replace(_SKILL_FILE_SUFFIX.lstrip("."), ""),
                        "framework": data.get("framework", "unknown"),
                        "deployment_target": data.get("deployment_target", "unknown"),
                        "success_rate": data.get("success_rate"),
                        "lesson_count": len(data.get("lessons", {})),
                        "event_count": len(data.get("events", [])),
                        "last_updated": data.get("last_updated"),
                    }
                )
            except Exception:  # noqa: BLE001
                pass
        return summaries

    def reset_skill(self, framework: str, deployment_target: str) -> None:
        """Delete the stored skill for a (framework, target) pair."""
        sid = _skill_id(framework, deployment_target)
        skill_path = self.skills_dir / f"{sid}{_SKILL_FILE_SUFFIX}"
        if skill_path.exists():
            skill_path.unlink()
            logger.info("Skill reset: %s/%s", framework, deployment_target)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load_skill(self, skill_id: str) -> dict[str, Any]:
        skill_path = self.skills_dir / f"{skill_id}{_SKILL_FILE_SUFFIX}"
        if skill_path.exists():
            try:
                return json.loads(skill_path.read_text())
            except Exception:  # noqa: BLE001
                pass
        return {"events": [], "lessons": {}, "success_rate": 0.5}

    def _save_skill(self, skill_id: str, skill: dict[str, Any]) -> None:
        skill_path = self.skills_dir / f"{skill_id}{_SKILL_FILE_SUFFIX}"
        # Keep events list bounded to avoid unbounded growth
        skill["events"] = skill["events"][-100:]
        skill_path.write_text(json.dumps(skill, indent=2))

    def _derive_lesson(self, event: dict[str, Any]) -> str | None:
        """
        Heuristically derive a human-readable lesson from a deployment event.

        This is intentionally simple — the real intelligence comes from
        accumulating many events and letting the success-rate weight guide
        which lessons the AICodeGenerator should prioritise.
        """
        error = event.get("error_message") or ""
        framework = event.get("framework", "")
        target = event.get("deployment_target", "")
        config = event.get("config", {})

        if not event["success"] and error:
            return self._lesson_from_error(framework, target, error, config)

        if event["success"] and config:
            return self._lesson_from_success(framework, target, config)

        return None

    @staticmethod
    def _lesson_from_error(
        framework: str,
        target: str,
        error: str,
        config: dict[str, Any],
    ) -> str:
        error_lower = error.lower()

        # Node version mismatch
        if "node" in error_lower and ("version" in error_lower or "engine" in error_lower):
            node_ver = config.get("node_version", "18")
            return (
                f"Pin NODE_VERSION={node_ver} in {target} config to avoid engine "
                f"mismatch errors when deploying {framework} projects."
            )

        # Python version mismatch
        if "python" in error_lower and "version" in error_lower:
            py_ver = config.get("python_version", "3.11")
            return (
                f"Specify python-{py_ver} runtime in {target} config for {framework} "
                "to prevent Python version conflicts."
            )

        # Missing environment variable
        env_match = re.search(r"(?:env(?:ironment)? variable|env var)[:\s]+([A-Z_]+)", error, re.I)
        if env_match:
            var_name = env_match.group(1)
            return (
                f"Set the {var_name} environment variable in {target} before deploying "
                f"{framework} projects to prevent runtime failures."
            )

        # Build command failure
        if "build" in error_lower and "fail" in error_lower:
            return (
                f"Build failure detected for {framework} on {target}. "
                "Verify build command and output directory in deployment config."
            )

        # Generic lesson
        return (
            f"Deployment of {framework} to {target} failed: {error[:120]}. "
            "Review logs and adjust config accordingly."
        )

    @staticmethod
    def _lesson_from_success(
        framework: str,
        target: str,
        config: dict[str, Any],
    ) -> str | None:
        if not config:
            return None
        key_settings = {k: v for k, v in config.items() if v}
        if not key_settings:
            return None
        settings_str = ", ".join(f"{k}={v}" for k, v in list(key_settings.items())[:3])
        return (
            f"Successful {framework} deployment to {target} used: {settings_str}."
        )

    def _add_lesson(
        self, skill: dict[str, Any], lesson: str, success: bool
    ) -> None:
        """Add or update a lesson entry with an EMA-based weight."""
        lessons: dict[str, Any] = skill.setdefault("lessons", {})

        # Use a short hash as key to de-duplicate near-identical lessons
        key = hashlib.sha256(lesson.encode()).hexdigest()[:12]

        if key in lessons:
            prev_weight = lessons[key]["weight"]
            # Successes reinforce; failures penalise slightly less
            delta = _EMA_ALPHA if success else -(_EMA_ALPHA * 0.5)
            lessons[key]["weight"] = round(
                max(0.0, min(1.0, prev_weight + delta)), 4
            )
            lessons[key]["count"] += 1
            lessons[key]["last_seen"] = _now_iso()
        else:
            lessons[key] = {
                "text": lesson,
                "weight": 0.5 if success else 0.3,
                "count": 1,
                "first_seen": _now_iso(),
                "last_seen": _now_iso(),
            }

        # Prune to keep only the highest-weighted lessons
        if len(lessons) > _MAX_LESSONS_PER_SKILL:
            pruned = sorted(lessons.items(), key=lambda kv: kv[1]["weight"], reverse=True)
            skill["lessons"] = dict(pruned[:_MAX_LESSONS_PER_SKILL])


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

_skill_builder: SkillBuilder | None = None


def get_skill_builder(skills_dir: Path | None = None) -> SkillBuilder:
    """Return (or create) the module-level SkillBuilder singleton."""
    global _skill_builder  # noqa: PLW0603
    if _skill_builder is None:
        _skill_builder = SkillBuilder(skills_dir=skills_dir)
    return _skill_builder
