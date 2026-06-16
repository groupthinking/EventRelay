"""
VERA Maturity Runtime — Agent Progression & Demotion

Agents don't get full permissions on Day 1. Like a new employee's probation:
start with read-only access, earn more autonomy through demonstrated competence.
The maturity runtime tracks each agent's level and decides when promotion is
warranted — or when demotion is necessary.

Levels:
  0 OBSERVER    → Read-only, human approval required for every write
  1 ASSISTED    → Pre-approved action sets, human in the loop
  2 SUPERVISED  → Autonomous within boundaries, async human review
  3 AUTONOMOUS  → Full capability set, real-time monitoring only

Dependencies: none (stdlib only)
Env vars: uses maturity_config from VeraConfig
"""

import logging
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import IntEnum
from typing import Optional

from .config import get_vera_config

logger = logging.getLogger("vera.maturity")


class MaturityLevel(IntEnum):
    """Agent maturity levels — higher means more autonomy."""
    OBSERVER = 0
    ASSISTED = 1
    SUPERVISED = 2
    AUTONOMOUS = 3


# Human-readable descriptions for each level
LEVEL_DESCRIPTIONS: dict[int, str] = {
    0: "Read-only, all write actions require human approval",
    1: "Pre-approved action sets, human in the loop",
    2: "Autonomous within boundaries, async human review",
    3: "Full capability set, real-time monitoring only",
}


@dataclass
class AgentMaturityRecord:
    """Tracks an agent's current maturity state."""
    agent_id: str
    agent_name: str
    current_level: int = 0
    promoted_at: Optional[str] = None     # ISO timestamp of last promotion
    demoted_at: Optional[str] = None      # ISO timestamp of last demotion
    demotion_reason: Optional[str] = None
    registered_at: str = ""
    total_promotions: int = 0
    total_demotions: int = 0

    def __post_init__(self):
        if not self.registered_at:
            self.registered_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "current_level": self.current_level,
            "level_name": MaturityLevel(self.current_level).name,
            "level_description": LEVEL_DESCRIPTIONS.get(self.current_level, ""),
            "promoted_at": self.promoted_at,
            "demoted_at": self.demoted_at,
            "demotion_reason": self.demotion_reason,
            "registered_at": self.registered_at,
            "total_promotions": self.total_promotions,
            "total_demotions": self.total_demotions,
        }


@dataclass
class PromotionEvaluation:
    """Result of evaluating an agent for promotion."""
    agent_id: str
    eligible: bool
    current_level: int
    target_level: int
    checks: dict = field(default_factory=dict)
    requires_human_approval: bool = True
    reason: str = ""
    portfolio_summary: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "eligible": self.eligible,
            "current_level": self.current_level,
            "target_level": self.target_level,
            "current_level_name": MaturityLevel(self.current_level).name,
            "target_level_name": MaturityLevel(self.target_level).name if self.target_level <= 3 else "N/A",
            "checks": self.checks,
            "requires_human_approval": self.requires_human_approval,
            "reason": self.reason,
            "portfolio_summary": self.portfolio_summary,
        }


class MaturityRuntime:
    """Manages agent maturity levels, promotion, and demotion.

    In-process registry by default. When VERA_DATABASE_URL is configured,
    persists to the agent_maturity table (see 002_vera_tables.sql).
    """

    def __init__(self):
        self.config = get_vera_config()
        self._agents: dict[str, AgentMaturityRecord] = {}
        self._lock = threading.Lock()

    def register_agent(self, agent_id: str, agent_name: str, initial_level: int = 0) -> AgentMaturityRecord:
        """Register an agent in the maturity system.

        All agents start at OBSERVER (level 0) unless explicitly overridden.
        """
        with self._lock:
            if agent_id in self._agents:
                return self._agents[agent_id]

            record = AgentMaturityRecord(
                agent_id=agent_id,
                agent_name=agent_name,
                current_level=min(initial_level, MaturityLevel.AUTONOMOUS),
            )
            self._agents[agent_id] = record

            logger.info(
                "agent_registered",
                extra={
                    "agent_id": agent_id,
                    "agent_name": agent_name,
                    "level": record.current_level,
                    "level_name": MaturityLevel(record.current_level).name,
                },
            )
            return record

    def get_level(self, agent_id: str) -> int:
        """Get an agent's current maturity level. Returns 0 (OBSERVER) for unknown agents."""
        with self._lock:
            record = self._agents.get(agent_id)
            return record.current_level if record else MaturityLevel.OBSERVER

    def get_record(self, agent_id: str) -> Optional[AgentMaturityRecord]:
        """Get the full maturity record for an agent."""
        with self._lock:
            return self._agents.get(agent_id)

    def evaluate_promotion(self, agent_id: str, portfolio: dict) -> PromotionEvaluation:
        """Evaluate whether an agent qualifies for promotion.

        Uses the evidence portfolio from the proof chain store to verify
        the agent has met all requirements for the next level.

        Args:
            agent_id: The agent to evaluate.
            portfolio: Evidence portfolio from ProofChainStore.get_evidence_portfolio().

        Returns:
            PromotionEvaluation with eligibility and check details.
        """
        with self._lock:
            record = self._agents.get(agent_id)

        if record is None:
            return PromotionEvaluation(
                agent_id=agent_id,
                eligible=False,
                current_level=0,
                target_level=1,
                reason="Agent not registered in maturity system",
            )

        current = record.current_level
        target = current + 1

        if target > MaturityLevel.AUTONOMOUS:
            return PromotionEvaluation(
                agent_id=agent_id,
                eligible=False,
                current_level=current,
                target_level=target,
                reason="Already at maximum maturity level (AUTONOMOUS)",
            )

        # Get requirements for this transition
        level_key = f"level_{current}_to_{target}"
        requirements = self.config.maturity_config.get(level_key, {})

        if not requirements:
            return PromotionEvaluation(
                agent_id=agent_id,
                eligible=False,
                current_level=current,
                target_level=target,
                reason=f"No promotion config for {level_key}",
            )

        # Run checks against portfolio
        min_actions = requirements.get("min_actions", 50)
        max_violations = requirements.get("max_violations", 0)

        checks = {
            "min_actions": portfolio.get("total_actions", 0) >= min_actions,
            "max_violations": portfolio.get("policy_violations", 0) <= max_violations,
            "chain_integrity": portfolio.get("chain_integrity") == "verified",
        }

        all_passed = all(checks.values())

        return PromotionEvaluation(
            agent_id=agent_id,
            eligible=all_passed,
            current_level=current,
            target_level=target,
            checks=checks,
            requires_human_approval=True,  # Always require human approval
            reason="All checks passed" if all_passed else "One or more checks failed",
            portfolio_summary=portfolio,
        )

    def promote(self, agent_id: str, approved_by: str = "system") -> bool:
        """Promote an agent to the next maturity level.

        Should only be called after evaluate_promotion() returns eligible=True
        AND human approval is obtained.

        Returns True if promoted, False if already at max or not found.
        """
        with self._lock:
            record = self._agents.get(agent_id)
            if record is None:
                return False

            if record.current_level >= MaturityLevel.AUTONOMOUS:
                return False

            prev_level = record.current_level
            record.current_level += 1
            record.promoted_at = datetime.now(timezone.utc).isoformat()
            record.total_promotions += 1

            logger.info(
                "agent_promoted",
                extra={
                    "agent_id": agent_id,
                    "from_level": prev_level,
                    "to_level": record.current_level,
                    "from_name": MaturityLevel(prev_level).name,
                    "to_name": MaturityLevel(record.current_level).name,
                    "approved_by": approved_by,
                },
            )
            return True

    def demote(self, agent_id: str, reason: str, to_level: int = 0) -> bool:
        """Demote an agent immediately.

        Demotion is always immediate. The agent must re-earn its level
        from scratch — prior evidence portfolios are archived, not counted.

        Args:
            agent_id: The agent to demote.
            reason: Why the demotion occurred.
            to_level: Level to demote to (default: 0 / OBSERVER).

        Returns True if demoted, False if not found or already at target level.
        """
        with self._lock:
            record = self._agents.get(agent_id)
            if record is None:
                return False

            if record.current_level <= to_level:
                return False

            prev_level = record.current_level
            record.current_level = max(0, to_level)
            record.demoted_at = datetime.now(timezone.utc).isoformat()
            record.demotion_reason = reason
            record.total_demotions += 1

            logger.warning(
                "agent_demoted",
                extra={
                    "agent_id": agent_id,
                    "from_level": prev_level,
                    "to_level": record.current_level,
                    "from_name": MaturityLevel(prev_level).name,
                    "to_name": MaturityLevel(record.current_level).name,
                    "reason": reason,
                },
            )
            return True

    def all_records(self) -> list[dict]:
        """Get all agent maturity records."""
        with self._lock:
            return [r.to_dict() for r in self._agents.values()]


# --- Module-level singleton ---

_maturity_runtime: Optional[MaturityRuntime] = None


def get_maturity_runtime() -> MaturityRuntime:
    """Get the singleton maturity runtime."""
    global _maturity_runtime
    if _maturity_runtime is None:
        _maturity_runtime = MaturityRuntime()
    return _maturity_runtime
