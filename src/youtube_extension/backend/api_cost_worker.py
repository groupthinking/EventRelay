#!/usr/bin/env python3
"""Dedicated Cloud Run worker for durable API-cost outbox delivery.

The worker owns polling and delivery.  The FastAPI process never starts this
loop.  Deployments can keep the process warm while leaving delivery disabled;
this is the fail-closed state used by the PostgreSQL substrate rollout.
"""

from __future__ import annotations

import asyncio
import inspect
import json
import logging
import math
import os
import threading
import time
from collections.abc import Awaitable
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Callable

from youtube_extension.backend.services.api_cost_monitor import (
    ensure_api_cost_database_ready,
    get_cost_monitor,
    is_production_environment,
    validate_cloud_sql_database_url,
)

logger = logging.getLogger(__name__)

AsyncCheck = Callable[[], Awaitable[None]]
AsyncProcessor = Callable[[int], Awaitable[None]]


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    normalized = value.strip().lower()
    if normalized not in {"true", "false"}:
        raise ValueError(f"{name} must be exactly 'true' or 'false'")
    return normalized == "true"


def validate_cloud_sql_socket(database_url: str, instance: str) -> None:
    """Compatibility alias for the centralized runtime URL validator."""
    try:
        validate_cloud_sql_database_url(database_url, instance)
    except RuntimeError as error:
        raise ValueError(str(error)) from error


@dataclass(frozen=True)
class WorkerConfig:
    """Validated worker runtime settings."""

    delivery_enabled: bool = False
    poll_interval_seconds: float = 5.0
    operation_timeout_seconds: float = 20.0
    health_max_staleness_seconds: float = 60.0
    batch_size: int = 10
    port: int = 8080
    database_url: str | None = None
    runtime_db_role: str | None = None
    webhook_url: str | None = None

    @classmethod
    def from_env(cls) -> WorkerConfig:
        config = cls(
            delivery_enabled=_env_bool("API_COST_DELIVERY_ENABLED", False),
            poll_interval_seconds=float(
                os.getenv("API_COST_POLL_INTERVAL_SECONDS", "5")
            ),
            operation_timeout_seconds=float(
                os.getenv("API_COST_OPERATION_TIMEOUT_SECONDS", "20")
            ),
            health_max_staleness_seconds=float(
                os.getenv("API_COST_HEALTH_MAX_STALENESS_SECONDS", "60")
            ),
            batch_size=int(os.getenv("API_COST_WORKER_BATCH_SIZE", "10")),
            port=int(os.getenv("PORT", "8080")),
            database_url=(
                os.getenv("API_COST_DATABASE_URL") or os.getenv("DATABASE_URL")
            ),
            runtime_db_role=os.getenv("API_COST_RUNTIME_DB_ROLE"),
            webhook_url=os.getenv("API_COST_WEBHOOK_URL"),
        )
        config.validate()
        return config

    def validate(self) -> None:
        timing_values = {
            "API_COST_POLL_INTERVAL_SECONDS": self.poll_interval_seconds,
            "API_COST_OPERATION_TIMEOUT_SECONDS": self.operation_timeout_seconds,
            "API_COST_HEALTH_MAX_STALENESS_SECONDS": (
                self.health_max_staleness_seconds
            ),
        }
        for name, value in timing_values.items():
            if not math.isfinite(value):
                raise ValueError(f"{name} must be finite")
        if self.poll_interval_seconds <= 0:
            raise ValueError("API_COST_POLL_INTERVAL_SECONDS must be positive")
        if self.operation_timeout_seconds <= 0:
            raise ValueError("API_COST_OPERATION_TIMEOUT_SECONDS must be positive")
        if self.health_max_staleness_seconds <= self.operation_timeout_seconds:
            raise ValueError(
                "API_COST_HEALTH_MAX_STALENESS_SECONDS must exceed the operation timeout"
            )
        if self.health_max_staleness_seconds <= self.poll_interval_seconds:
            raise ValueError(
                "API_COST_HEALTH_MAX_STALENESS_SECONDS must exceed the poll interval"
            )
        if not 1 <= self.batch_size <= 20:
            raise ValueError("API_COST_WORKER_BATCH_SIZE must be between 1 and 20")
        if not 1 <= self.port <= 65535:
            raise ValueError("PORT must be between 1 and 65535")
        if self.delivery_enabled and not self.webhook_url:
            raise ValueError(
                "API_COST_WEBHOOK_URL is required when API-cost delivery is enabled"
            )

        instance = os.getenv("CLOUD_SQL_INSTANCE_CONNECTION_NAME", "").strip()
        if is_production_environment():
            if not self.database_url:
                raise ValueError(
                    "API_COST_DATABASE_URL or DATABASE_URL is required in production"
                )
            if not instance:
                raise ValueError(
                    "CLOUD_SQL_INSTANCE_CONNECTION_NAME is required in production"
                )
            if not self.runtime_db_role:
                raise ValueError("API_COST_RUNTIME_DB_ROLE is required in production")
        if instance and self.database_url:
            validate_cloud_sql_socket(self.database_url, instance)


@dataclass
class WorkerState:
    """Thread-safe progress state exposed through Cloud Run probes."""

    clock: Callable[[], float] = time.monotonic
    started_at: float = field(init=False)
    poll_started_at: float | None = field(default=None, init=False)
    last_poll_completed_at: float | None = field(default=None, init=False)
    last_database_success_at: float | None = field(default=None, init=False)
    database_ready: bool = field(default=False, init=False)
    last_error: str | None = field(default=None, init=False)
    timed_out: bool = field(default=False, init=False)
    completed_polls: int = field(default=0, init=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False)

    def __post_init__(self) -> None:
        self.started_at = self.clock()

    def record_poll_started(self) -> None:
        with self._lock:
            self.poll_started_at = self.clock()

    def record_database_success(self) -> None:
        with self._lock:
            self.database_ready = True
            self.last_database_success_at = self.clock()
            self.last_error = None
            self.timed_out = False

    def record_database_error(self, error: BaseException) -> None:
        with self._lock:
            self.database_ready = False
            self.last_error = str(error)

    def record_poll_error(self, error: BaseException) -> None:
        with self._lock:
            self.last_error = str(error)

    def record_timeout(self, error: BaseException) -> None:
        with self._lock:
            self.database_ready = False
            self.timed_out = True
            self.last_error = str(error) or "worker operation timed out"

    def record_poll_completed(self) -> None:
        with self._lock:
            self.last_poll_completed_at = self.clock()
            self.poll_started_at = None
            self.completed_polls += 1

    def is_live(self, max_staleness_seconds: float) -> bool:
        now = self.clock()
        with self._lock:
            if self.timed_out:
                return False
            if self.poll_started_at is not None:
                return now - self.poll_started_at <= max_staleness_seconds
            reference = self.last_poll_completed_at or self.started_at
            return now - reference <= max_staleness_seconds

    def is_ready(self, max_staleness_seconds: float) -> bool:
        now = self.clock()
        with self._lock:
            if not self.database_ready or self.last_error is not None:
                return False
            if self.last_database_success_at is None:
                return False
            if now - self.last_database_success_at > max_staleness_seconds:
                return False
            if self.last_poll_completed_at is None:
                return False
            if now - self.last_poll_completed_at > max_staleness_seconds:
                return False
            if self.poll_started_at is not None:
                return now - self.poll_started_at <= max_staleness_seconds
            return True

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return {
                "database_ready": self.database_ready,
                "completed_polls": self.completed_polls,
                "last_error": self.last_error,
                "timed_out": self.timed_out,
                "poll_in_progress": self.poll_started_at is not None,
            }


async def _default_database_check() -> None:
    await ensure_api_cost_database_ready()


async def _default_outbox_processor(batch_size: int) -> None:
    monitor = get_cost_monitor()
    result = monitor.process_outbox(max_items=batch_size)
    if inspect.isawaitable(result):
        await result


class APICostWorker:
    """Bounded polling loop with injectable dependencies for deterministic tests."""

    def __init__(
        self,
        config: WorkerConfig,
        state: WorkerState,
        database_check: AsyncCheck = _default_database_check,
        outbox_processor: AsyncProcessor = _default_outbox_processor,
    ) -> None:
        self.config = config
        self.state = state
        self.database_check = database_check
        self.outbox_processor = outbox_processor

    async def poll_once(self) -> None:
        self.state.record_poll_started()
        database_succeeded = False
        try:
            await asyncio.wait_for(
                self.database_check(), timeout=self.config.operation_timeout_seconds
            )
            database_succeeded = True
            self.state.record_database_success()
            if self.config.delivery_enabled:
                await asyncio.wait_for(
                    self.outbox_processor(self.config.batch_size),
                    timeout=self.config.operation_timeout_seconds,
                )
        except Exception as error:
            if isinstance(error, asyncio.TimeoutError):
                self.state.record_timeout(error)
            elif database_succeeded:
                self.state.record_poll_error(error)
            else:
                self.state.record_database_error(error)
            raise
        finally:
            self.state.record_poll_completed()

    async def run_forever(self, stop: asyncio.Event | None = None) -> None:
        stop_event = stop or asyncio.Event()
        while not stop_event.is_set():
            try:
                await self.poll_once()
            except Exception:
                logger.exception("API-cost worker poll failed")

            try:
                await asyncio.wait_for(
                    stop_event.wait(), timeout=self.config.poll_interval_seconds
                )
            except asyncio.TimeoutError:
                continue


def _health_handler(
    state: WorkerState, max_staleness_seconds: float
) -> type[BaseHTTPRequestHandler]:
    class HealthHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802 - stdlib handler contract
            if self.path == "/healthz":
                healthy = state.is_live(max_staleness_seconds)
                payload = {"status": "healthy" if healthy else "stale"}
            elif self.path == "/readyz":
                healthy = state.is_ready(max_staleness_seconds)
                payload = {"status": "ready" if healthy else "not-ready"}
            else:
                self.send_error(404)
                return

            payload.update(state.snapshot())
            body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
            self.send_response(200 if healthy else 503)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, _format: str, *args: Any) -> None:
            return

    return HealthHandler


async def run_worker(config: WorkerConfig | None = None) -> None:
    active_config = config or WorkerConfig.from_env()
    state = WorkerState()
    worker = APICostWorker(active_config, state)
    server = ThreadingHTTPServer(
        ("0.0.0.0", active_config.port),
        _health_handler(state, active_config.health_max_staleness_seconds),
    )
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    logger.info(
        "API-cost worker started (delivery_enabled=%s)",
        active_config.delivery_enabled,
    )
    try:
        await worker.run_forever()
    finally:
        server.shutdown()
        server.server_close()
        server_thread.join(timeout=5)


def main() -> None:
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    asyncio.run(run_worker())


if __name__ == "__main__":
    main()
