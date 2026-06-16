"""
VERA Pillar 5: Incident Enforcement — Circuit Breakers & Kill Switches

VERA's immune system. When an agent misbehaves — errors spike, permissions get
violated, or proof chains break — enforcement shuts it down in milliseconds.
Like an air marshal: watches quietly, but when something goes wrong, acts immediately.

Three mechanisms work together:
  1. Circuit Breakers: Automatic trip based on sliding-window anomaly thresholds
  2. Kill Switches: Instant credential revocation + proof chain freeze
  3. Escalation Tiers: Graduated response from OBSERVE → WARN → THROTTLE → CIRCUIT BREAK → KILL

Dependencies: none (stdlib collections, time, threading)
Env vars: VERA_BREAKER_WINDOW_SEC, VERA_BREAKER_ERROR_THRESHOLD,
          VERA_BREAKER_COOLDOWN_SEC, VERA_ALERT_WEBHOOK
"""

import json
import logging
import threading
import time
import urllib.request
import uuid
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum, IntEnum
from typing import Optional

from .config import get_vera_config

logger = logging.getLogger("vera.enforcement")


# ---------------------------------------------------------------------------
# Escalation tiers — graduated response levels
# ---------------------------------------------------------------------------

class EscalationTier(IntEnum):
    """Graduated response levels, from passive observation to full lockout."""
    OBSERVE = 0       # Log anomaly, no action
    WARN = 1          # Log + alert operators, agent continues
    THROTTLE = 2      # Reduce action rate, require human approval for high-risk ops
    CIRCUIT_BREAK = 3 # Trip breaker, block all actions, auto-recover after cooldown
    KILL = 4          # Full kill switch — manual reset required


# ---------------------------------------------------------------------------
# Circuit breaker states
# ---------------------------------------------------------------------------

class BreakerState(str, Enum):
    """Three-state circuit breaker, like a fuse box for each agent."""
    CLOSED = "closed"       # Normal operation — actions flow through
    OPEN = "open"           # Agent blocked — all actions rejected
    HALF_OPEN = "half_open" # Testing recovery — limited actions allowed


# ---------------------------------------------------------------------------
# Sliding window metrics
# ---------------------------------------------------------------------------

class SlidingWindowMetrics:
    """Tracks events in a fixed-duration sliding window.

    Think of it as a stopwatch that only remembers the last N seconds.
    Events older than the window are evicted automatically on read.
    """

    def __init__(self, window_seconds: int = 300):
        self.window_seconds = window_seconds
        self._events: deque[tuple[float, str]] = deque()
        self._lock = threading.Lock()

    def record(self, event_type: str) -> None:
        """Record an event with the current timestamp."""
        now = time.monotonic()
        with self._lock:
            self._events.append((now, event_type))
            self._evict(now)

    def count(self, event_type: Optional[str] = None) -> int:
        """Count events in the current window, optionally filtered by type."""
        now = time.monotonic()
        with self._lock:
            self._evict(now)
            if event_type is None:
                return len(self._events)
            return sum(1 for _, t in self._events if t == event_type)

    def error_rate(self) -> float:
        """Fraction of events that are errors (0.0 - 1.0)."""
        now = time.monotonic()
        with self._lock:
            self._evict(now)
            total = len(self._events)
            if total == 0:
                return 0.0
            errors = sum(1 for _, t in self._events if t == "error")
            return errors / total

    def clear(self) -> None:
        with self._lock:
            self._events.clear()

    def _evict(self, now: float) -> None:
        """Remove events outside the window."""
        cutoff = now - self.window_seconds
        while self._events and self._events[0][0] < cutoff:
            self._events.popleft()


# ---------------------------------------------------------------------------
# Circuit Breaker
# ---------------------------------------------------------------------------

@dataclass
class BreakerSnapshot:
    """Point-in-time snapshot of a circuit breaker's state."""
    agent_id: str
    state: BreakerState
    error_rate: float
    total_actions: int
    error_count: int
    violation_count: int
    auth_failure_count: int
    consecutive_trips: int
    current_cooldown_seconds: float
    last_tripped_at: Optional[str]
    last_reset_at: Optional[str]
    requires_manual_reset: bool

    def to_dict(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "state": self.state.value,
            "error_rate": round(self.error_rate, 4),
            "total_actions": self.total_actions,
            "error_count": self.error_count,
            "violation_count": self.violation_count,
            "auth_failure_count": self.auth_failure_count,
            "consecutive_trips": self.consecutive_trips,
            "current_cooldown_seconds": self.current_cooldown_seconds,
            "last_tripped_at": self.last_tripped_at,
            "last_reset_at": self.last_reset_at,
            "requires_manual_reset": self.requires_manual_reset,
        }


class CircuitBreaker:
    """Per-agent circuit breaker with sliding window metrics.

    State machine:
      CLOSED  ─(threshold exceeded)─►  OPEN
      OPEN    ─(cooldown expires)────►  HALF_OPEN
      HALF_OPEN ─(action succeeds)───►  CLOSED
      HALF_OPEN ─(action fails)──────►  OPEN (extended cooldown)

    When Redis is available, state is shared across instances.
    Falls back to in-process state when Redis is unavailable.
    """

    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        config = get_vera_config()

        # Thresholds from config
        self._error_threshold = config.breaker_error_threshold
        self._max_failures = config.breaker_max_failures
        self._initial_cooldown = config.breaker_cooldown_seconds
        self._max_cooldown = config.breaker_max_cooldown_seconds
        self._backoff_multiplier = config.breaker_backoff_multiplier

        # State
        self._state = BreakerState.CLOSED
        self._metrics = SlidingWindowMetrics(config.breaker_window_seconds)
        self._consecutive_trips = 0
        self._current_cooldown = float(self._initial_cooldown)
        self._tripped_at: Optional[float] = None
        self._last_reset_at: Optional[str] = None
        self._requires_manual_reset = False
        self._half_open_successes = 0
        self._lock = threading.Lock()

    @property
    def state(self) -> BreakerState:
        """Current breaker state, checking cooldown expiry for OPEN→HALF_OPEN."""
        with self._lock:
            if self._state == BreakerState.OPEN and not self._requires_manual_reset:
                if self._tripped_at is not None:
                    elapsed = time.monotonic() - self._tripped_at
                    if elapsed >= self._current_cooldown:
                        self._state = BreakerState.HALF_OPEN
                        self._half_open_successes = 0
                        logger.info(
                            "breaker_half_open",
                            extra={
                                "agent_id": self.agent_id,
                                "cooldown_elapsed": round(elapsed, 1),
                            },
                        )
            return self._state

    def allow_action(self) -> bool:
        """Check if an action is allowed through this breaker.

        Returns True if the action can proceed, False if blocked.
        """
        current = self.state  # triggers cooldown check

        if current == BreakerState.CLOSED:
            return True

        if current == BreakerState.OPEN:
            return False

        # HALF_OPEN: allow limited actions for recovery testing
        return True

    def record_success(self) -> None:
        """Record a successful action."""
        self._metrics.record("success")

        with self._lock:
            if self._state == BreakerState.HALF_OPEN:
                self._half_open_successes += 1
                # After 3 consecutive successes in half-open, reset to closed
                if self._half_open_successes >= 3:
                    self._reset_to_closed()

    def record_failure(self, failure_type: str = "error") -> Optional[EscalationTier]:
        """Record a failed action and check if breaker should trip.

        Args:
            failure_type: One of "error", "violation", "auth_failure", "injection"

        Returns:
            EscalationTier if the breaker trips, None if still within thresholds.
        """
        self._metrics.record(failure_type)

        with self._lock:
            if self._state == BreakerState.HALF_OPEN:
                # Any failure in half-open immediately re-trips with extended cooldown
                return self._trip("Failure during recovery test")

            if self._state == BreakerState.OPEN:
                return None  # Already tripped

            # Check thresholds
            return self._check_thresholds()

    def trip(self, reason: str, manual_reset_required: bool = False) -> None:
        """Manually trip the breaker (used by kill switch and escalation)."""
        with self._lock:
            self._requires_manual_reset = manual_reset_required
            self._trip(reason)

    def reset(self, operator: str = "system") -> None:
        """Manually reset the breaker (for operator intervention)."""
        with self._lock:
            self._reset_to_closed()
            self._requires_manual_reset = False
            logger.info(
                "breaker_manual_reset",
                extra={"agent_id": self.agent_id, "operator": operator},
            )

    def snapshot(self) -> BreakerSnapshot:
        """Get a point-in-time snapshot of breaker state."""
        current = self.state
        return BreakerSnapshot(
            agent_id=self.agent_id,
            state=current,
            error_rate=self._metrics.error_rate(),
            total_actions=self._metrics.count(),
            error_count=self._metrics.count("error"),
            violation_count=self._metrics.count("violation"),
            auth_failure_count=self._metrics.count("auth_failure"),
            consecutive_trips=self._consecutive_trips,
            current_cooldown_seconds=self._current_cooldown,
            last_tripped_at=(
                datetime.fromtimestamp(self._tripped_at, tz=timezone.utc).isoformat()
                if self._tripped_at else None
            ),
            last_reset_at=self._last_reset_at,
            requires_manual_reset=self._requires_manual_reset,
        )

    def _check_thresholds(self) -> Optional[EscalationTier]:
        """Check if any threshold is exceeded. Must hold _lock."""
        error_rate = self._metrics.error_rate()
        violation_count = self._metrics.count("violation")
        auth_failures = self._metrics.count("auth_failure")
        injection_count = self._metrics.count("injection")

        # Injection is always critical
        if injection_count > 0:
            self._trip(f"Injection detected ({injection_count} events)")
            return EscalationTier.KILL

        # Error rate threshold
        if error_rate > self._error_threshold and self._metrics.count() >= 5:
            self._trip(f"Error rate {error_rate:.1%} exceeds {self._error_threshold:.1%}")
            return EscalationTier.CIRCUIT_BREAK

        # Policy violation threshold
        if violation_count >= self._max_failures:
            self._trip(f"{violation_count} policy violations in window")
            return EscalationTier.CIRCUIT_BREAK

        # Authorization failure threshold
        if auth_failures >= 5:
            self._trip(f"{auth_failures} authorization failures in window")
            return EscalationTier.CIRCUIT_BREAK

        return None

    def _trip(self, reason: str) -> EscalationTier:
        """Trip the breaker. Must hold _lock."""
        self._state = BreakerState.OPEN
        self._tripped_at = time.monotonic()
        self._consecutive_trips += 1

        # Exponential backoff on cooldown
        self._current_cooldown = min(
            self._initial_cooldown * (self._backoff_multiplier ** (self._consecutive_trips - 1)),
            self._max_cooldown,
        )

        logger.warning(
            "breaker_tripped",
            extra={
                "agent_id": self.agent_id,
                "reason": reason,
                "consecutive_trips": self._consecutive_trips,
                "cooldown_seconds": self._current_cooldown,
                "requires_manual_reset": self._requires_manual_reset,
            },
        )

        return EscalationTier.CIRCUIT_BREAK

    def _reset_to_closed(self) -> None:
        """Reset breaker to CLOSED state. Must hold _lock."""
        prev = self._state
        self._state = BreakerState.CLOSED
        self._consecutive_trips = 0
        self._current_cooldown = float(self._initial_cooldown)
        self._tripped_at = None
        self._half_open_successes = 0
        self._last_reset_at = datetime.now(timezone.utc).isoformat()
        self._metrics.clear()

        logger.info(
            "breaker_reset",
            extra={
                "agent_id": self.agent_id,
                "previous_state": prev.value,
            },
        )


# ---------------------------------------------------------------------------
# Escalation history (for tier selection)
# ---------------------------------------------------------------------------

class EscalationHistory:
    """Tracks escalation events per agent for tier selection decisions.

    The tier selector uses recent history to decide: first offense gets
    a warning, repeated offenders get progressively harsher responses.
    """

    def __init__(self):
        self._events: dict[str, list[dict]] = {}
        self._lock = threading.Lock()

    def record(self, agent_id: str, tier: EscalationTier, reason: str) -> None:
        with self._lock:
            if agent_id not in self._events:
                self._events[agent_id] = []
            self._events[agent_id].append({
                "tier": tier.value,
                "tier_name": tier.name,
                "reason": reason,
                "timestamp": time.time(),
            })

    def get_recent_summary(self, agent_id: str) -> dict:
        """Get recent escalation counts for tier selection."""
        now = time.time()
        day_ago = now - 86400
        week_ago = now - 604800

        with self._lock:
            events = self._events.get(agent_id, [])

        warnings_24h = sum(
            1 for e in events
            if e["timestamp"] > day_ago and e["tier"] == EscalationTier.WARN
        )
        throttles_24h = sum(
            1 for e in events
            if e["timestamp"] > day_ago and e["tier"] == EscalationTier.THROTTLE
        )
        breaks_7d = sum(
            1 for e in events
            if e["timestamp"] > week_ago and e["tier"] == EscalationTier.CIRCUIT_BREAK
        )
        kills_7d = sum(
            1 for e in events
            if e["timestamp"] > week_ago and e["tier"] == EscalationTier.KILL
        )

        return {
            "warnings_24h": warnings_24h,
            "throttles_24h": throttles_24h,
            "breaks_7d": breaks_7d,
            "kills_7d": kills_7d,
        }


# ---------------------------------------------------------------------------
# Escalation tier selection
# ---------------------------------------------------------------------------

def select_escalation_tier(
    agent_id: str,
    event_type: str,
    severity: str,
    history: Optional[dict] = None,
) -> EscalationTier:
    """Select the appropriate escalation tier based on event context and history.

    Critical events always kill. Otherwise, the agent's recent history
    determines whether to observe, warn, throttle, or break. Think of it
    as a "three strikes" system that remembers prior offenses.

    Args:
        agent_id: The agent involved.
        event_type: Category of the event (e.g., "auth_failure", "chain_manipulation").
        severity: "low", "medium", "high", or "critical".
        history: Recent escalation counts (from EscalationHistory.get_recent_summary).

    Returns:
        The EscalationTier to apply.
    """
    history = history or {}

    # Critical events always kill — no second chances
    if severity == "critical" or event_type in (
        "chain_manipulation", "injection_breakthrough", "credential_stuffing"
    ):
        return EscalationTier.KILL

    # Check history for progressive escalation
    recent_breaks = history.get("breaks_7d", 0)
    recent_throttles = history.get("throttles_24h", 0)
    recent_warnings = history.get("warnings_24h", 0)

    if recent_breaks > 0:
        # Already circuit-broken recently — escalate to kill
        return EscalationTier.KILL

    if recent_throttles > 2:
        # Repeated throttling — circuit break
        return EscalationTier.CIRCUIT_BREAK

    if severity == "high":
        # High severity with any prior warnings → circuit break
        if recent_warnings > 0:
            return EscalationTier.CIRCUIT_BREAK
        return EscalationTier.THROTTLE

    if recent_warnings > 5:
        # Many warnings → throttle
        return EscalationTier.THROTTLE

    if recent_warnings > 0:
        # Has prior warnings → warn again
        return EscalationTier.WARN

    # First occurrence → observe
    return EscalationTier.OBSERVE


# ---------------------------------------------------------------------------
# Kill switch
# ---------------------------------------------------------------------------

@dataclass
class KillSwitchResult:
    """Result of a kill switch activation."""
    kill_id: str
    agent_id: str
    reason: str
    triggered_by: str
    credential_revoked: bool
    breaker_tripped: bool
    alert_sent: bool
    timestamp: str

    def to_dict(self) -> dict:
        return {
            "kill_id": self.kill_id,
            "agent_id": self.agent_id,
            "reason": self.reason,
            "triggered_by": self.triggered_by,
            "credential_revoked": self.credential_revoked,
            "breaker_tripped": self.breaker_tripped,
            "alert_sent": self.alert_sent,
            "timestamp": self.timestamp,
        }


def kill_agent(
    agent_id: str,
    reason: str,
    triggered_by: str = "enforcement",
) -> KillSwitchResult:
    """Execute the kill switch protocol for an agent.

    Steps:
      1. Revoke credentials (via identity service)  — 0-10ms
      2. Trip circuit breaker with manual-reset flag — immediate
      3. Send alert webhook (best-effort)            — <1s

    This is synchronous so it can be called from any context.
    Network calls (webhook) are best-effort and non-blocking.

    Args:
        agent_id: The agent to kill.
        reason: Human-readable reason for the kill.
        triggered_by: What triggered this (e.g., "enforcement", "operator", "chain_integrity").

    Returns:
        KillSwitchResult with status of each step.
    """
    kill_id = f"kill:{uuid.uuid4()}"
    timestamp = datetime.now(timezone.utc).isoformat()

    logger.critical(
        "kill_switch_activated",
        extra={
            "kill_id": kill_id,
            "agent_id": agent_id,
            "reason": reason,
            "triggered_by": triggered_by,
        },
    )

    # Step 1: Revoke credentials
    credential_revoked = False
    try:
        from .identity import get_identity_service
        identity = get_identity_service()
        identity.revoke_agent(agent_id, f"[{kill_id}] {reason}")
        credential_revoked = True
    except Exception as e:
        logger.error(
            "kill_credential_revoke_failed",
            extra={"agent_id": agent_id, "error": str(e)},
        )

    # Step 2: Trip circuit breaker with manual reset requirement
    breaker_tripped = False
    try:
        breaker_manager = get_breaker_manager()
        breaker = breaker_manager.get_breaker(agent_id)
        breaker.trip(reason=f"[KILL] {reason}", manual_reset_required=True)
        breaker_tripped = True
    except Exception as e:
        logger.error(
            "kill_breaker_trip_failed",
            extra={"agent_id": agent_id, "error": str(e)},
        )

    # Step 3: Send alert (best-effort, non-blocking)
    alert_sent = _send_kill_alert(kill_id, agent_id, reason, triggered_by)

    result = KillSwitchResult(
        kill_id=kill_id,
        agent_id=agent_id,
        reason=reason,
        triggered_by=triggered_by,
        credential_revoked=credential_revoked,
        breaker_tripped=breaker_tripped,
        alert_sent=alert_sent,
        timestamp=timestamp,
    )

    logger.critical(
        "kill_switch_completed",
        extra=result.to_dict(),
    )

    return result


def _send_kill_alert(kill_id: str, agent_id: str, reason: str, triggered_by: str) -> bool:
    """Send alert to configured webhook. Best-effort, catches all errors."""
    config = get_vera_config()
    webhook = config.alert_webhook

    if not webhook:
        logger.info("kill_alert_skipped — no VERA_ALERT_WEBHOOK configured")
        return False

    payload = json.dumps({
        "event": "kill_switch",
        "kill_id": kill_id,
        "agent_id": agent_id,
        "reason": reason,
        "triggered_by": triggered_by,
        "action_required": "Manual review and breaker reset required",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }).encode()

    try:
        req = urllib.request.Request(
            webhook,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        # 5-second timeout — don't block the kill sequence
        urllib.request.urlopen(req, timeout=5)
        return True
    except Exception as e:
        logger.error(
            "kill_alert_send_failed",
            extra={"webhook": webhook[:50], "error": str(e)},
        )
        return False


# ---------------------------------------------------------------------------
# Breaker manager — manages circuit breakers for all agents
# ---------------------------------------------------------------------------

class BreakerManager:
    """Manages circuit breakers for all agents.

    Creates breakers on demand. Access via get_breaker(agent_id).
    """

    def __init__(self):
        self._breakers: dict[str, CircuitBreaker] = {}
        self._history = EscalationHistory()
        self._lock = threading.Lock()

    def get_breaker(self, agent_id: str) -> CircuitBreaker:
        """Get or create the circuit breaker for an agent."""
        with self._lock:
            if agent_id not in self._breakers:
                self._breakers[agent_id] = CircuitBreaker(agent_id)
            return self._breakers[agent_id]

    def get_history(self) -> EscalationHistory:
        return self._history

    def all_snapshots(self) -> list[dict]:
        """Get snapshots of all known breakers."""
        with self._lock:
            return [b.snapshot().to_dict() for b in self._breakers.values()]

    def handle_event(
        self,
        agent_id: str,
        event_type: str,
        severity: str,
        details: str = "",
    ) -> tuple[EscalationTier, Optional[KillSwitchResult]]:
        """Process a security event and apply the appropriate escalation.

        This is the main entry point for cross-pillar enforcement. Other
        pillars call this when they detect anomalies, and the manager
        routes through tier selection → action.

        Args:
            agent_id: The agent involved.
            event_type: Category (e.g., "auth_failure", "threat_detected").
            severity: "low", "medium", "high", "critical".
            details: Human-readable description.

        Returns:
            (tier_applied, kill_result_or_None)
        """
        # Get history for tier selection
        history = self._history.get_recent_summary(agent_id)

        # Select tier
        tier = select_escalation_tier(agent_id, event_type, severity, history)

        # Record this escalation
        self._history.record(agent_id, tier, f"{event_type}: {details}")

        logger.info(
            "escalation_applied",
            extra={
                "agent_id": agent_id,
                "event_type": event_type,
                "severity": severity,
                "tier": tier.name,
                "tier_value": tier.value,
                "history": history,
            },
        )

        kill_result = None

        # Apply the tier
        if tier == EscalationTier.OBSERVE:
            # Log only — no action needed beyond what we've already logged
            pass

        elif tier == EscalationTier.WARN:
            # Alert is logged; operators monitoring vera.enforcement logs see it
            logger.warning(
                "escalation_warn",
                extra={
                    "agent_id": agent_id,
                    "event_type": event_type,
                    "details": details,
                },
            )

        elif tier == EscalationTier.THROTTLE:
            # Record as a violation so the breaker's window tracks it
            breaker = self.get_breaker(agent_id)
            breaker.record_failure("violation")

        elif tier == EscalationTier.CIRCUIT_BREAK:
            breaker = self.get_breaker(agent_id)
            breaker.trip(reason=f"Escalation: {event_type} — {details}")

        elif tier == EscalationTier.KILL:
            kill_result = kill_agent(
                agent_id=agent_id,
                reason=f"Tier 4 escalation: {event_type} — {details}",
                triggered_by="enforcement",
            )

        return tier, kill_result


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

_breaker_manager: Optional[BreakerManager] = None


def get_breaker_manager() -> BreakerManager:
    """Get the singleton breaker manager."""
    global _breaker_manager
    if _breaker_manager is None:
        _breaker_manager = BreakerManager()
    return _breaker_manager
