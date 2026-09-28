"""AUDIT-011: yt-dlp circuit breaker behavior."""

from youtube_extension.backend.services.youtube.adapters.ytdlp_circuit import (
    YtdlpCircuitBreaker,
    get_ytdlp_circuit,
    reset_ytdlp_circuit_for_tests,
)


def test_circuit_opens_after_threshold_failures() -> None:
    breaker = YtdlpCircuitBreaker(failure_threshold=2, cooldown_seconds=60.0)
    assert breaker.allow() is True
    breaker.record_failure()
    assert breaker.allow() is True
    breaker.record_failure()
    assert breaker.allow() is False


def test_success_closes_circuit() -> None:
    breaker = YtdlpCircuitBreaker(failure_threshold=1, cooldown_seconds=60.0)
    breaker.record_failure()
    assert breaker.allow() is False
    breaker.record_success()
    assert breaker.allow() is True


def test_global_reset_for_tests() -> None:
    reset_ytdlp_circuit_for_tests()
    breaker = get_ytdlp_circuit()
    breaker.record_failure()
    breaker.record_failure()
    breaker.record_failure()
    assert breaker.allow() is False
    reset_ytdlp_circuit_for_tests()
    assert get_ytdlp_circuit().allow() is True
