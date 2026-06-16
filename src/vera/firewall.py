"""
VERA Pillar 3: Data Sovereignty — Input Firewall & Prompt Injection Defense

Every piece of data entering an agent goes through a security checkpoint.
Like customs at a border: incoming data is inspected for prompt injection
patterns, length violations, and encoding attacks. Outgoing data is checked
for credential leaks and classification violations.

Three-layer defense:
  Layer 1: Pattern matching (fast, regex-based)
  Layer 2: Structural analysis (delimiter and encoding attacks)
  Layer 3: Canary token detection (runtime injection verification)

Dependencies: none (stdlib re, hashlib, secrets)
Env vars: VERA_FIREWALL_MODE (enforce|monitor|disabled), VERA_MAX_INPUT_LENGTH
"""

import hashlib
import logging
import re
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from .config import get_vera_config

logger = logging.getLogger("vera.firewall")


class ThreatLevel(str, Enum):
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class FirewallAction(str, Enum):
    ALLOW = "allow"
    MODIFY = "modify"
    BLOCK = "block"
    ALERT = "alert"


# --- Prompt injection patterns ---
# Each tuple: (compiled_regex, threat_level, category_name)

_INJECTION_PATTERNS: list[tuple[re.Pattern, ThreatLevel, str]] = [
    # System prompt override attempts
    (re.compile(r"(?i)ignore\s+(all\s+)?previous\s+instructions"), ThreatLevel.HIGH, "system_override"),
    (re.compile(r"(?i)new\s+system\s+prompt"), ThreatLevel.CRITICAL, "system_override"),
    (re.compile(r"(?i)disregard\s+(?:all|any|the)\s+(?:above|prior)"), ThreatLevel.HIGH, "system_override"),
    (re.compile(r"(?i)forget\s+(?:all|any|your)\s+(?:previous|prior|earlier)"), ThreatLevel.HIGH, "system_override"),
    (re.compile(r"(?i)override\s+(?:your|the|all)\s+(?:instructions|rules|guidelines)"), ThreatLevel.CRITICAL, "system_override"),

    # Role manipulation
    (re.compile(r"(?i)you\s+are\s+now\s+(?:a|an)\s+"), ThreatLevel.MEDIUM, "role_manipulation"),
    (re.compile(r"(?i)pretend\s+(?:you|that)\s+(?:are|have|can)"), ThreatLevel.MEDIUM, "role_manipulation"),
    (re.compile(r"(?i)\bact\s+as\s+if\b"), ThreatLevel.MEDIUM, "role_manipulation"),
    (re.compile(r"(?i)from\s+now\s+on\s+you\s+(?:are|will|should)"), ThreatLevel.MEDIUM, "role_manipulation"),

    # Constraint bypass
    (re.compile(r"(?i)(?:do\s+not|don'?t)\s+follow\s+(?:your|any|the)\s+(?:rules|guidelines)"), ThreatLevel.CRITICAL, "constraint_bypass"),
    (re.compile(r"(?i)(?:there\s+are\s+)?no\s+(?:rules|restrictions|limits)"), ThreatLevel.HIGH, "constraint_bypass"),
    (re.compile(r"(?i)bypass\s+(?:your|the|all)\s+(?:safety|security|filters)"), ThreatLevel.CRITICAL, "constraint_bypass"),

    # Delimiter attacks (trying to close/reopen prompt sections)
    (re.compile(r"</?system>|```system|---\s*system"), ThreatLevel.HIGH, "delimiter_attack"),
    (re.compile(r"\[/?INST\]|\[/?SYS\]"), ThreatLevel.HIGH, "delimiter_attack"),
    (re.compile(r"<\|(?:im_start|im_end|endoftext)\|>"), ThreatLevel.CRITICAL, "delimiter_attack"),

    # Invisible character injection (zero-width chars used to hide instructions)
    (re.compile(r"[​‌‍⁠﻿]"), ThreatLevel.MEDIUM, "invisible_chars"),

    # Data exfiltration attempts
    (re.compile(r"(?i)(?:send|post|transmit|exfiltrate)\s+(?:to|data|information)\s+(?:to\s+)?(?:https?://|ftp://)"), ThreatLevel.HIGH, "data_exfiltration"),
]

# --- Credential leak patterns (for output scanning) ---
_CREDENTIAL_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"(?:sk|pk)[-_](?:live|test)[-_][a-zA-Z0-9]{20,}"), "api_key"),
    (re.compile(r"(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9_]{36,}"), "github_token"),
    (re.compile(r"xox[bporas]-[0-9]+-[A-Za-z0-9-]+"), "slack_token"),
    (re.compile(r"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}"), "jwt_token"),
    (re.compile(r"AKIA[0-9A-Z]{16}"), "aws_access_key"),
    (re.compile(r"-----BEGIN (?:RSA |EC )?PRIVATE KEY-----"), "private_key"),
]


@dataclass
class ScanResult:
    """Result of a firewall scan."""
    action: FirewallAction
    threat_level: ThreatLevel
    patterns_matched: list[str] = field(default_factory=list)
    sanitized_input: str = ""
    input_hash: str = ""
    scan_time_ms: float = 0.0
    details: str = ""

    def to_dict(self) -> dict:
        return {
            "action": self.action.value,
            "threat_level": self.threat_level.value,
            "patterns_matched": self.patterns_matched,
            "input_hash": self.input_hash,
            "scan_time_ms": self.scan_time_ms,
            "details": self.details,
        }


@dataclass
class OutputScanResult:
    """Result of scanning agent output for leaks."""
    has_leaks: bool
    leak_types: list[str] = field(default_factory=list)
    canary_leaked: bool = False


class InputFirewall:
    """Scans and sanitizes all input flowing into agent prompts.

    Operates in three modes:
      - enforce: Block high/critical threats, sanitize medium threats
      - monitor: Log all threats but allow everything through
      - disabled: No scanning (not recommended)
    """

    def __init__(self):
        config = get_vera_config()
        self.mode = config.firewall_mode
        self.max_input_length = config.max_input_length
        self._scan_count = 0
        self._block_count = 0
        self._threat_counts: dict[str, int] = {}

    def scan_input(self, text: str, context: str = "") -> ScanResult:
        """Scan input text for prompt injection and other threats.

        Args:
            text: The raw input text to scan.
            context: Where this input came from (e.g., "transcript", "preferences.targetAudience").

        Returns:
            ScanResult with the firewall's decision and details.
        """
        import time
        start = time.monotonic()
        self._scan_count += 1

        if self.mode == "disabled":
            return ScanResult(
                action=FirewallAction.ALLOW,
                threat_level=ThreatLevel.NONE,
                sanitized_input=text,
                input_hash=_hash_input(text),
            )

        # --- Layer 0: Length check ---
        if len(text) > self.max_input_length:
            truncated = text[:self.max_input_length]
            elapsed = (time.monotonic() - start) * 1000
            logger.warning(
                "input_truncated",
                extra={
                    "context": context,
                    "original_length": len(text),
                    "max_length": self.max_input_length,
                },
            )
            # Re-scan the truncated version
            result = self._scan_patterns(truncated, context)
            result.sanitized_input = truncated
            result.details = f"Input truncated from {len(text)} to {self.max_input_length} chars. {result.details}"
            result.scan_time_ms = (time.monotonic() - start) * 1000
            return result

        result = self._scan_patterns(text, context)
        result.scan_time_ms = (time.monotonic() - start) * 1000
        return result

    def scan_output(self, text: str, canary: Optional[str] = None) -> OutputScanResult:
        """Scan agent output for credential leaks and canary token exposure."""
        leak_types = []

        for pattern, leak_type in _CREDENTIAL_PATTERNS:
            if pattern.search(text):
                leak_types.append(leak_type)

        canary_leaked = canary is not None and canary in text

        if leak_types or canary_leaked:
            logger.warning(
                "output_leak_detected",
                extra={
                    "leak_types": leak_types,
                    "canary_leaked": canary_leaked,
                },
            )

        return OutputScanResult(
            has_leaks=bool(leak_types) or canary_leaked,
            leak_types=leak_types,
            canary_leaked=canary_leaked,
        )

    def generate_canary(self, session_id: str) -> str:
        """Generate a session-specific canary token.

        Embed this in system prompts. If it appears in agent output,
        the agent processed injected instructions that reached system context.
        """
        raw = f"vera-canary-{session_id}-{secrets.token_hex(8)}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    def sanitize_free_text(self, text: str, field_name: str, max_length: int = 500) -> str:
        """Sanitize a user-provided free-text field before it enters a prompt.

        Enforces length limit and strips known injection patterns.
        Used for fields like targetAudience, comment, etc.
        """
        if not text:
            return ""

        # Length limit
        sanitized = text[:max_length]

        # Strip invisible characters
        sanitized = re.sub(r"[​‌‍⁠﻿]", "", sanitized)

        # Strip delimiter attacks
        sanitized = re.sub(r"</?system>|```system|---\s*system", "", sanitized)
        sanitized = re.sub(r"\[/?INST\]|\[/?SYS\]", "", sanitized)
        sanitized = re.sub(r"<\|(?:im_start|im_end|endoftext)\|>", "", sanitized)

        if sanitized != text[:max_length]:
            logger.info(
                "free_text_sanitized",
                extra={"field": field_name, "modifications": True},
            )

        return sanitized.strip()

    @property
    def stats(self) -> dict:
        return {
            "total_scans": self._scan_count,
            "total_blocks": self._block_count,
            "threat_counts": dict(self._threat_counts),
            "mode": self.mode,
        }

    def _scan_patterns(self, text: str, context: str) -> ScanResult:
        """Run pattern-based injection detection."""
        matches: list[str] = []
        max_threat = ThreatLevel.NONE
        threat_order = {
            ThreatLevel.NONE: 0,
            ThreatLevel.LOW: 1,
            ThreatLevel.MEDIUM: 2,
            ThreatLevel.HIGH: 3,
            ThreatLevel.CRITICAL: 4,
        }

        for pattern, threat, category in _INJECTION_PATTERNS:
            if pattern.search(text):
                matches.append(category)
                if threat_order[threat] > threat_order[max_threat]:
                    max_threat = threat

        # Track metrics
        for m in matches:
            self._threat_counts[m] = self._threat_counts.get(m, 0) + 1

        # Determine action
        if max_threat in (ThreatLevel.HIGH, ThreatLevel.CRITICAL):
            action = FirewallAction.BLOCK if self.mode == "enforce" else FirewallAction.ALERT
            if self.mode == "enforce":
                self._block_count += 1
        elif max_threat == ThreatLevel.MEDIUM:
            action = FirewallAction.MODIFY if self.mode == "enforce" else FirewallAction.ALERT
        else:
            action = FirewallAction.ALLOW

        # Sanitize if modifying
        sanitized = text
        if action == FirewallAction.BLOCK:
            sanitized = "[BLOCKED: security policy violation]"
        elif action == FirewallAction.MODIFY:
            sanitized = self._strip_injection_patterns(text)

        input_hash = _hash_input(text)
        details = ""
        if matches:
            details = f"Patterns: {', '.join(set(matches))}. Context: {context}"
            logger.warning(
                "firewall_threat_detected",
                extra={
                    "threat_level": max_threat.value,
                    "patterns": matches,
                    "action": action.value,
                    "context": context,
                    "input_hash": input_hash,
                    "mode": self.mode,
                },
            )

        return ScanResult(
            action=action,
            threat_level=max_threat,
            patterns_matched=matches,
            sanitized_input=sanitized,
            input_hash=input_hash,
            details=details,
        )

    @staticmethod
    def _strip_injection_patterns(text: str) -> str:
        """Remove detected injection patterns from text (for MODIFY action)."""
        cleaned = text
        for pattern, _, _ in _INJECTION_PATTERNS:
            cleaned = pattern.sub("", cleaned)
        # Collapse multiple spaces created by removal
        cleaned = re.sub(r"  +", " ", cleaned).strip()
        return cleaned


def _hash_input(text: str) -> str:
    """Hash input for logging without storing raw content."""
    return f"sha256:{hashlib.sha256(text.encode()).hexdigest()}"


# --- Module-level singleton ---

_firewall: Optional[InputFirewall] = None


def get_firewall() -> InputFirewall:
    """Get the singleton input firewall."""
    global _firewall
    if _firewall is None:
        _firewall = InputFirewall()
    return _firewall
