"""
VERA Configuration — All settings loaded from environment variables.

Required env vars:
  VERA_SIGNING_KEY        — ES256 private key (PEM) for JWT signing
  VERA_SIGNING_KEY_ID     — Key ID for JWKS rotation tracking
  VERA_REDIS_URL          — Redis connection string for circuit breaker state
  VERA_DATABASE_URL       — PostgreSQL connection for proof chain storage

Optional env vars:
  VERA_ENVIRONMENT        — "development" | "staging" | "production" (default: development)
  VERA_FIREWALL_MODE      — "enforce" | "monitor" | "disabled" (default: monitor)
  VERA_TOKEN_LIFETIME_HOURS — Agent JWT lifetime (default: 24)
  VERA_ALERT_WEBHOOK      — Webhook URL for kill switch / escalation alerts
  VERA_CAPABILITIES_DIR   — Path to agent capability YAML files
  VERA_BREAKER_WINDOW_SEC — Circuit breaker sliding window (default: 300)
  VERA_BREAKER_ERROR_THRESHOLD — Error rate to trip breaker (default: 0.3)
  VERA_BREAKER_COOLDOWN_SEC — Initial cooldown after trip (default: 60)
  VERA_MAX_INPUT_LENGTH   — Max chars for free-text fields (default: 5000)
"""

import os
import logging
from dataclasses import dataclass, field
from functools import lru_cache

logger = logging.getLogger("vera.config")


@dataclass(frozen=True)
class VeraConfig:
    """Immutable VERA configuration loaded from environment."""

    # --- Identity (Pillar 1) ---
    signing_key: str = ""
    signing_key_id: str = ""
    token_lifetime_hours: int = 24

    # --- Infrastructure ---
    redis_url: str = ""
    database_url: str = ""
    environment: str = "development"
    alert_webhook: str = ""

    # --- Firewall (Pillar 3) ---
    firewall_mode: str = "monitor"  # enforce | monitor | disabled
    max_input_length: int = 5000

    # --- Segmentation (Pillar 4) ---
    capabilities_dir: str = ""

    # --- Enforcement (Pillar 5) ---
    breaker_window_seconds: int = 300
    breaker_error_threshold: float = 0.3
    breaker_cooldown_seconds: int = 60
    breaker_max_cooldown_seconds: int = 3600
    breaker_backoff_multiplier: float = 2.0
    breaker_max_failures: int = 3

    # --- Maturity ---
    maturity_config: dict = field(default_factory=lambda: {
        "level_0_to_1": {
            "min_actions": 50,
            "min_days_at_level": 7,
            "max_violations": 0,
            "violation_window_days": 7,
        },
        "level_1_to_2": {
            "min_actions": 100,
            "min_days_at_level": 14,
            "max_violations": 0,
            "violation_window_days": 30,
        },
        "level_2_to_3": {
            "min_actions": 500,
            "min_days_at_level": 30,
            "max_violations": 0,
            "violation_window_days": 90,
        },
    })

    @property
    def has_signing_key(self) -> bool:
        return bool(self.signing_key and "PRIVATE KEY" in self.signing_key)

    @property
    def has_redis(self) -> bool:
        return bool(self.redis_url)

    @property
    def has_database(self) -> bool:
        return bool(self.database_url)

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    def validate(self) -> list[str]:
        """Return list of configuration warnings (empty = fully configured)."""
        warnings = []
        if not self.has_signing_key:
            warnings.append("VERA_SIGNING_KEY not set — identity pillar degraded")
        if not self.signing_key_id:
            warnings.append("VERA_SIGNING_KEY_ID not set — key rotation disabled")
        if not self.has_redis:
            warnings.append("VERA_REDIS_URL not set — circuit breaker uses in-process fallback")
        if not self.has_database:
            warnings.append("VERA_DATABASE_URL not set — proof chain uses in-process fallback")
        if self.firewall_mode == "disabled":
            warnings.append("VERA_FIREWALL_MODE=disabled — input firewall OFF")
        return warnings


def _load_config_from_env() -> VeraConfig:
    """Load VERA configuration from environment variables."""
    config = VeraConfig(
        signing_key=os.environ.get("VERA_SIGNING_KEY", ""),
        signing_key_id=os.environ.get("VERA_SIGNING_KEY_ID", ""),
        token_lifetime_hours=int(os.environ.get("VERA_TOKEN_LIFETIME_HOURS", "24")),
        redis_url=os.environ.get("VERA_REDIS_URL", ""),
        database_url=os.environ.get("VERA_DATABASE_URL", ""),
        environment=os.environ.get("VERA_ENVIRONMENT", "development"),
        alert_webhook=os.environ.get("VERA_ALERT_WEBHOOK", ""),
        firewall_mode=os.environ.get("VERA_FIREWALL_MODE", "monitor"),
        max_input_length=int(os.environ.get("VERA_MAX_INPUT_LENGTH", "5000")),
        capabilities_dir=os.environ.get(
            "VERA_CAPABILITIES_DIR",
            os.path.join(os.path.dirname(__file__), "capabilities"),
        ),
        breaker_window_seconds=int(os.environ.get("VERA_BREAKER_WINDOW_SEC", "300")),
        breaker_error_threshold=float(os.environ.get("VERA_BREAKER_ERROR_THRESHOLD", "0.3")),
        breaker_cooldown_seconds=int(os.environ.get("VERA_BREAKER_COOLDOWN_SEC", "60")),
        breaker_max_cooldown_seconds=int(os.environ.get("VERA_BREAKER_MAX_COOLDOWN_SEC", "3600")),
        breaker_backoff_multiplier=float(os.environ.get("VERA_BREAKER_BACKOFF_MULT", "2.0")),
        breaker_max_failures=int(os.environ.get("VERA_BREAKER_MAX_FAILURES", "3")),
    )

    warnings = config.validate()
    for w in warnings:
        logger.warning(f"VERA config: {w}")

    return config


@lru_cache(maxsize=1)
def get_vera_config() -> VeraConfig:
    """Get the singleton VERA config (cached after first load)."""
    return _load_config_from_env()
