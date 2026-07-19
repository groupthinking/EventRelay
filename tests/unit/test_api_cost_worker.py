"""Operational contract tests for the dedicated API-cost worker."""

from __future__ import annotations

import asyncio

import pytest

from youtube_extension.backend.api_cost_worker import (
    APICostWorker,
    WorkerConfig,
    WorkerState,
    validate_cloud_sql_socket,
)


class MutableClock:
    def __init__(self, value: float = 100.0) -> None:
        self.value = value

    def __call__(self) -> float:
        return self.value


def test_production_cloud_sql_url_must_use_attached_unix_socket() -> None:
    with pytest.raises(ValueError, match="Cloud SQL Unix socket"):
        validate_cloud_sql_socket(
            "postgresql+psycopg://runtime:secret@10.0.0.2/eventrelay",
            "uvai:us-central1:eventrelay",
        )

    validate_cloud_sql_socket(
        "postgresql+psycopg://runtime:secret@/eventrelay"
        "?host=/cloudsql/uvai:us-central1:eventrelay",
        "uvai:us-central1:eventrelay",
    )


def test_production_config_fails_closed_without_shared_postgres(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.delenv("API_COST_DATABASE_URL", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv(
        "CLOUD_SQL_INSTANCE_CONNECTION_NAME", "uvai:us-central1:eventrelay"
    )

    with pytest.raises(ValueError, match="DATABASE_URL"):
        WorkerConfig.from_env()


def test_worker_prefers_scoped_api_cost_database_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv(
        "API_COST_DATABASE_URL", "postgresql+psycopg://runtime:secret@db/api_cost"
    )
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://backend:secret@db/backend")

    config = WorkerConfig.from_env()

    assert config.database_url == ("postgresql+psycopg://runtime:secret@db/api_cost")


def test_worker_uses_global_database_url_only_as_legacy_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.delenv("API_COST_DATABASE_URL", raising=False)
    monkeypatch.setenv(
        "DATABASE_URL", "postgresql+psycopg://runtime:secret@db/api_cost"
    )

    assert WorkerConfig.from_env().database_url == (
        "postgresql+psycopg://runtime:secret@db/api_cost"
    )


def test_delivery_requires_webhook_when_explicitly_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("API_COST_DELIVERY_ENABLED", "true")
    monkeypatch.delenv("API_COST_WEBHOOK_URL", raising=False)

    with pytest.raises(ValueError, match="API_COST_WEBHOOK_URL"):
        WorkerConfig.from_env()


def test_health_staleness_must_exceed_poll_interval(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("API_COST_POLL_INTERVAL_SECONDS", "61")
    monkeypatch.setenv("API_COST_HEALTH_MAX_STALENESS_SECONDS", "60")

    with pytest.raises(ValueError, match="poll interval"):
        WorkerConfig.from_env()


@pytest.mark.parametrize(
    ("name", "value"),
    (
        ("API_COST_POLL_INTERVAL_SECONDS", "nan"),
        ("API_COST_OPERATION_TIMEOUT_SECONDS", "inf"),
        ("API_COST_HEALTH_MAX_STALENESS_SECONDS", "-inf"),
    ),
)
def test_worker_timing_values_must_be_finite(
    monkeypatch: pytest.MonkeyPatch,
    name: str,
    value: str,
) -> None:
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv(name, value)

    with pytest.raises(ValueError, match="finite"):
        WorkerConfig.from_env()


@pytest.mark.asyncio
async def test_disabled_worker_checks_database_but_never_delivers() -> None:
    calls = {"database": 0, "delivery": 0}

    async def check_database() -> None:
        calls["database"] += 1

    async def process_outbox(_batch_size: int) -> None:
        calls["delivery"] += 1

    clock = MutableClock()
    state = WorkerState(clock=clock)
    worker = APICostWorker(
        config=WorkerConfig(delivery_enabled=False),
        state=state,
        database_check=check_database,
        outbox_processor=process_outbox,
    )

    await worker.poll_once()

    assert calls == {"database": 1, "delivery": 0}
    assert state.is_ready(max_staleness_seconds=30)
    assert state.is_live(max_staleness_seconds=30)


@pytest.mark.asyncio
async def test_enabled_worker_processes_only_after_database_check() -> None:
    order: list[str] = []

    async def check_database() -> None:
        order.append("database")

    async def process_outbox(batch_size: int) -> None:
        order.append(f"outbox:{batch_size}")

    worker = APICostWorker(
        config=WorkerConfig(delivery_enabled=True, batch_size=7),
        state=WorkerState(),
        database_check=check_database,
        outbox_processor=process_outbox,
    )

    await worker.poll_once()

    assert order == ["database", "outbox:7"]


def test_health_expires_when_polling_stops_progressing() -> None:
    clock = MutableClock()
    state = WorkerState(clock=clock)
    state.record_poll_started()
    state.record_database_success()
    state.record_poll_completed()
    assert state.is_live(max_staleness_seconds=20)
    assert state.is_ready(max_staleness_seconds=20)

    clock.value += 21

    assert not state.is_live(max_staleness_seconds=20)
    assert not state.is_ready(max_staleness_seconds=20)


def test_readiness_fails_immediately_after_database_error() -> None:
    state = WorkerState()
    state.record_poll_started()
    state.record_database_error(RuntimeError("database unavailable"))
    state.record_poll_completed()

    assert state.is_live(max_staleness_seconds=30)
    assert not state.is_ready(max_staleness_seconds=30)
    assert "database unavailable" in state.snapshot()["last_error"]


def test_liveness_fails_when_active_poll_exceeds_timeout() -> None:
    clock = MutableClock()
    state = WorkerState(clock=clock)
    state.record_poll_started()
    clock.value += 11

    assert not state.is_live(max_staleness_seconds=10)


@pytest.mark.asyncio
async def test_timed_out_database_check_marks_worker_unhealthy() -> None:
    never_finishes = asyncio.Event()

    async def hung_database_check() -> None:
        await never_finishes.wait()

    worker = APICostWorker(
        config=WorkerConfig(
            operation_timeout_seconds=0.01,
            health_max_staleness_seconds=1,
        ),
        state=WorkerState(),
        database_check=hung_database_check,
    )

    with pytest.raises(TimeoutError):
        await worker.poll_once()

    assert not worker.state.is_live(max_staleness_seconds=1)
    assert not worker.state.is_ready(max_staleness_seconds=1)
