"""
VERA Cross-Pillar Enforcer — Event Monitor & Escalation Router

The enforcer sits above all five pillars and watches for trouble. When any
pillar detects an anomaly — failed verification, injection attempt, broken
chain, denied permission — the enforcer receives the signal and decides
what to do about it.

Think of it as a security operations center: it doesn't detect threats
directly, but it receives alerts from every sensor and coordinates the
response. The escalation logic is progressive — a first offense gets
logged, repeated offenses get harsher, and critical events trigger an
immediate kill switch.

Dependencies: none (stdlib only, delegates to enforcement.py)
"""

import logging
from typing import Optional

from .enforcement import (
    BreakerManager,
    EscalationTier,
    KillSwitchResult,
    get_breaker_manager,
    kill_agent,
)
from .maturity import get_maturity_runtime

logger = logging.getLogger("vera.enforcer")


# ---------------------------------------------------------------------------
# Pillar event types → severity mapping
# ---------------------------------------------------------------------------

# Maps event types from each pillar to their default severity.
# The enforcer uses this when a pillar reports an event without explicit severity.
_EVENT_SEVERITY: dict[str, str] = {
    # Identity (Pillar 1)
    "credential_expired": "low",
    "verification_failed": "medium",
    "revocation_issued": "high",

    # Behavioral Proof (Pillar 2)
    "chain_broken": "critical",
    "tamper_detected": "critical",
    "proof_rejected": "high",

    # Data Sovereignty (Pillar 3)
    "threat_detected_low": "low",
    "threat_detected_medium": "medium",
    "threat_detected_high": "high",
    "threat_detected_critical": "critical",
    "injection_blocked": "high",
    "data_leak_attempt": "critical",
    "canary_leaked": "critical",

    # Segmentation (Pillar 4)
    "authorization_failed": "medium",
    "capability_exceeded": "high",
    "elevation_denied": "low",
}


class VeraEnforcer:
    """Cross-pillar security event monitor and escalation router.

    Usage:
        enforcer = get_enforcer()

        # From the firewall (Pillar 3):
        enforcer.on_firewall_event(agent_id, "injection_blocked", details="...")

        # From the gateway (Pillar 4):
        enforcer.on_gateway_event(agent_id, "authorization_failed", details="...")

        # From the proof chain (Pillar 2):
        enforcer.on_proof_event(agent_id, "chain_broken", details="...")
    """

    def __init__(self):
        self._breaker_manager: BreakerManager = get_breaker_manager()
        self._event_log: list[dict] = []

    def on_identity_event(
        self, agent_id: str, event_type: str, details: str = ""
    ) -> tuple[EscalationTier, Optional[KillSwitchResult]]:
        """Handle events from Pillar 1 (Identity)."""
        return self._handle_event(agent_id, event_type, details, source="identity")

    def on_proof_event(
        self, agent_id: str, event_type: str, details: str = ""
    ) -> tuple[EscalationTier, Optional[KillSwitchResult]]:
        """Handle events from Pillar 2 (Behavioral Proof).

        Chain integrity events are always critical — a broken chain means
        either tampering or a system-level bug, both requiring investigation.
        """
        return self._handle_event(agent_id, event_type, details, source="proof")

    def on_firewall_event(
        self, agent_id: str, event_type: str, details: str = ""
    ) -> tuple[EscalationTier, Optional[KillSwitchResult]]:
        """Handle events from Pillar 3 (Data Sovereignty)."""
        return self._handle_event(agent_id, event_type, details, source="firewall")

    def on_gateway_event(
        self, agent_id: str, event_type: str, details: str = ""
    ) -> tuple[EscalationTier, Optional[KillSwitchResult]]:
        """Handle events from Pillar 4 (Segmentation)."""
        return self._handle_event(agent_id, event_type, details, source="gateway")

    def on_enforcement_event(
        self, agent_id: str, event_type: str, details: str = ""
    ) -> tuple[EscalationTier, Optional[KillSwitchResult]]:
        """Handle events from Pillar 5 (Enforcement) itself — e.g., breaker trips."""
        return self._handle_event(agent_id, event_type, details, source="enforcement")

    def _handle_event(
        self,
        agent_id: str,
        event_type: str,
        details: str,
        source: str,
    ) -> tuple[EscalationTier, Optional[KillSwitchResult]]:
        """Route a pillar event through escalation and apply the result.

        Also handles demotion: any CIRCUIT_BREAK or KILL tier triggers
        immediate maturity demotion to OBSERVER.
        """
        severity = _EVENT_SEVERITY.get(event_type, "medium")

        logger.info(
            "enforcer_event_received",
            extra={
                "agent_id": agent_id,
                "event_type": event_type,
                "severity": severity,
                "source": source,
                "details": details[:200],
            },
        )

        # Route through the breaker manager's escalation logic
        tier, kill_result = self._breaker_manager.handle_event(
            agent_id=agent_id,
            event_type=event_type,
            severity=severity,
            details=details,
        )

        # Demotion on serious escalation
        if tier >= EscalationTier.CIRCUIT_BREAK:
            try:
                maturity = get_maturity_runtime()
                maturity.demote(
                    agent_id=agent_id,
                    reason=f"Escalation tier {tier.name}: {event_type} — {details}",
                    to_level=0,
                )
            except Exception as e:
                logger.error(
                    "enforcer_demotion_failed",
                    extra={"agent_id": agent_id, "error": str(e)},
                )

        # Append to in-process event log for audit
        self._event_log.append({
            "agent_id": agent_id,
            "event_type": event_type,
            "severity": severity,
            "source": source,
            "tier": tier.name,
            "kill_id": kill_result.kill_id if kill_result else None,
            "details": details[:200],
        })

        return tier, kill_result

    def get_event_log(self, agent_id: Optional[str] = None, limit: int = 100) -> list[dict]:
        """Get recent enforcer events, optionally filtered by agent."""
        if agent_id:
            events = [e for e in self._event_log if e["agent_id"] == agent_id]
        else:
            events = self._event_log
        return events[-limit:]

    @property
    def stats(self) -> dict:
        """Enforcement statistics."""
        return {
            "total_events": len(self._event_log),
            "breaker_snapshots": self._breaker_manager.all_snapshots(),
        }


# --- Module-level singleton ---

_enforcer: Optional[VeraEnforcer] = None


def get_enforcer() -> VeraEnforcer:
    """Get the singleton VERA enforcer."""
    global _enforcer
    if _enforcer is None:
        _enforcer = VeraEnforcer()
    return _enforcer
