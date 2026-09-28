"""Circuit breaker for yt-dlp metadata fallback (AUDIT-011 / #2173)."""

from __future__ import annotations

from dataclasses import dataclass
from time import monotonic

_DEFAULT_THRESHOLD = 3
_DEFAULT_COOLDOWN_SECONDS = 300.0


@dataclass
class YtdlpCircuitBreaker:
    failure_threshold: int = _DEFAULT_THRESHOLD
    cooldown_seconds: float = _DEFAULT_COOLDOWN_SECONDS
    consecutive_failures: int = 0
    opened_until: float = 0.0

    def allow(self) -> bool:
        return monotonic() >= self.opened_until

    def record_success(self) -> None:
        self.consecutive_failures = 0
        self.opened_until = 0.0

    def record_failure(self) -> None:
        self.consecutive_failures += 1
        if self.consecutive_failures >= self.failure_threshold:
            self.opened_until = monotonic() + self.cooldown_seconds


_GLOBAL_BREAKER = YtdlpCircuitBreaker()


def get_ytdlp_circuit() -> YtdlpCircuitBreaker:
    return _GLOBAL_BREAKER


def reset_ytdlp_circuit_for_tests() -> None:
    """Test-only reset."""
    global _GLOBAL_BREAKER
    _GLOBAL_BREAKER = YtdlpCircuitBreaker()
