"""Focused durability and lifecycle tests for the API-cost webhook outbox."""

from __future__ import annotations

import asyncio
import sqlite3
import sys
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from sqlalchemy import text

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from youtube_extension.backend.services import api_cost_monitor as monitor_module
from youtube_extension.backend.services.api_cost_monitor import (
    APICostMonitor,
    WebhookOutbox,
)


def _get_item(monitor: APICostMonitor, utc_date: str) -> WebhookOutbox:
    session = monitor.Session()
    try:
        item = (
            session.query(WebhookOutbox)
            .filter_by(utc_date=utc_date, alert_type="threshold")
            .one()
        )
        session.expunge(item)
        return item
    finally:
        session.close()


async def _wait_until(predicate, timeout: float = 1.0) -> None:
    deadline = asyncio.get_running_loop().time() + timeout
    while not predicate():
        if asyncio.get_running_loop().time() >= deadline:
            raise AssertionError("condition was not reached before timeout")
        await asyncio.sleep(0.005)


def test_additive_schema_upgrade_preserves_rows_and_adds_due_index(tmp_path):
    db_path = tmp_path / "legacy.db"
    connection = sqlite3.connect(db_path)
    try:
        connection.executescript("""
            CREATE TABLE webhook_outbox (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                utc_date VARCHAR NOT NULL,
                alert_type VARCHAR NOT NULL,
                status VARCHAR NOT NULL,
                retry_count INTEGER NOT NULL,
                last_attempt DATETIME,
                error_message VARCHAR,
                current_cost FLOAT NOT NULL,
                payload VARCHAR,
                CONSTRAINT uq_utc_date_alert_type UNIQUE (utc_date, alert_type)
            );
            INSERT INTO webhook_outbox (
                utc_date, alert_type, status, retry_count, current_cost, payload
            ) VALUES (
                '2026-07-17', 'threshold', 'pending', 0, 8.5, 'keep me'
            );
            """)
        connection.commit()
    finally:
        connection.close()

    monitor = APICostMonitor(db_path=str(db_path))

    with monitor.engine.connect() as connection:
        columns = {
            row[1]
            for row in connection.execute(text("PRAGMA table_info(webhook_outbox)"))
        }
        indexes = {
            row[1]
            for row in connection.execute(text("PRAGMA index_list(webhook_outbox)"))
        }
        due_index_columns = [
            row[2]
            for row in connection.execute(
                text("PRAGMA index_info(ix_webhook_outbox_due)")
            )
        ]

    assert "next_attempt_at" in columns
    assert "ix_webhook_outbox_due" in indexes
    assert due_index_columns == ["status", "next_attempt_at", "retry_count"]
    assert _get_item(monitor, "2026-07-17").payload == "keep me"


def test_schema_initialization_failure_is_not_suppressed(tmp_path, monkeypatch):
    def fail_upgrade(self):
        raise sqlite3.OperationalError("migration failed")

    monkeypatch.setattr(APICostMonitor, "_upgrade_sqlite_outbox_schema", fail_upgrade)

    with pytest.raises(sqlite3.OperationalError, match="migration failed"):
        APICostMonitor(db_path=str(tmp_path / "broken.db"))


async def test_constructor_and_alert_do_not_spawn_background_work(
    tmp_path, monkeypatch
):
    recovery_started = asyncio.Event()

    async def blocking_recovery(self, stale_timeout_seconds=None):
        recovery_started.set()
        await asyncio.Event().wait()

    monkeypatch.setattr(APICostMonitor, "recover_stale_deliveries", blocking_recovery)
    existing_tasks = asyncio.all_tasks()
    monitor = APICostMonitor(db_path=str(tmp_path / "no_implicit_tasks.db"))
    await asyncio.sleep(0)
    spawned_tasks = asyncio.all_tasks() - existing_tasks

    try:
        assert spawned_tasks == set()
        assert not recovery_started.is_set()

        loop = asyncio.get_running_loop()
        created = []
        original_create_task = loop.create_task

        def record_create_task(coro, *args, **kwargs):
            created.append(coro)
            coro.close()
            return None

        with monkeypatch.context() as context:
            context.setattr(loop, "create_task", record_create_task)
            await monitor._send_budget_alert(8.5, "threshold")

        assert created == []
        assert loop.create_task == original_create_task
    finally:
        for task in spawned_tasks:
            task.cancel()
        if spawned_tasks:
            await asyncio.gather(*spawned_tasks, return_exceptions=True)


async def test_start_is_idempotent_and_close_stops_the_single_worker(tmp_path):
    monitor = APICostMonitor(db_path=str(tmp_path / "lifecycle.db"))
    monitor.webhook_poll_interval_seconds = 60

    first = await monitor.start()
    second = await monitor.start()

    assert first is second
    assert first is monitor._worker_task
    assert not first.done()

    await monitor.close()

    assert first.done()
    assert monitor._worker_task is None
    await monitor.close()


async def test_missing_webhook_url_leaves_item_unattempted(tmp_path):
    monitor = APICostMonitor(db_path=str(tmp_path / "missing_url.db"))
    monitor.webhook_url = None
    assert monitor._claim_alert("2026-07-18", "threshold", 8.5)

    await monitor.process_outbox()

    item = _get_item(monitor, "2026-07-18")
    assert item.status == "pending"
    assert item.retry_count == 0
    assert item.last_attempt is None
    assert item.next_attempt_at is None


async def test_claim_is_compare_and_swap_across_monitor_instances(tmp_path):
    db_path = str(tmp_path / "shared.db")
    first = APICostMonitor(db_path=db_path)
    second = APICostMonitor(db_path=db_path)
    assert first._claim_alert("2026-07-19", "threshold", 8.5)
    item_id = _get_item(first, "2026-07-19").id
    claim_time = datetime.now(timezone.utc)

    claims = await asyncio.gather(
        asyncio.to_thread(first._try_claim_outbox_item, item_id, claim_time, True),
        asyncio.to_thread(second._try_claim_outbox_item, item_id, claim_time, True),
    )

    assert sum(claim is not None for claim in claims) == 1
    item = _get_item(first, "2026-07-19")
    assert item.status == "processing"
    assert item.retry_count == 1


async def test_completion_is_conditional_on_the_original_claim(tmp_path):
    db_path = str(tmp_path / "conditional-completion.db")
    first = APICostMonitor(db_path=db_path)
    second = APICostMonitor(db_path=db_path)
    assert first._claim_alert("2026-07-25", "threshold", 8.5)
    item_id = _get_item(first, "2026-07-25").id

    old_claim = first._try_claim_outbox_item(item_id, datetime.now(timezone.utc), False)
    assert old_claim is not None

    session = second.Session()
    try:
        item = session.query(WebhookOutbox).filter_by(id=item_id).one()
        item.status = "failed"
        session.commit()
    finally:
        session.close()

    new_claim = second._try_claim_outbox_item(
        item_id, datetime.now(timezone.utc) + timedelta(seconds=1), False
    )
    assert new_claim is not None

    assert first._complete_outbox_claim(old_claim, success=True) is False
    item = _get_item(first, "2026-07-25")
    assert item.status == "processing"
    assert item.retry_count == 2

    assert second._complete_outbox_claim(new_claim, success=True) is True
    assert _get_item(first, "2026-07-25").status == "sent"


async def test_failure_persists_equal_jitter_backoff_and_respects_due_time(
    tmp_path, monkeypatch
):
    monitor = APICostMonitor(db_path=str(tmp_path / "backoff.db"))
    monitor.webhook_url = "https://example.test/hook"
    monitor.webhook_retry_base_seconds = 10
    monitor.webhook_retry_max_seconds = 25
    monkeypatch.setattr(monitor_module.random, "uniform", lambda low, high: high)

    attempts = 0

    async def fail(message):
        nonlocal attempts
        attempts += 1
        return False

    monkeypatch.setattr(monitor, "_send_webhook_notification", fail)
    assert monitor._claim_alert("2026-07-20", "threshold", 8.5)

    expected_delays = [10, 20, 25, 25]
    for expected_attempt, expected_delay in enumerate(expected_delays, start=1):
        before = datetime.now(timezone.utc).replace(tzinfo=None)
        await monitor.process_outbox(force=True)
        item = _get_item(monitor, "2026-07-20")
        assert item.retry_count == expected_attempt
        assert item.status == "failed"
        assert item.next_attempt_at is not None
        actual_delay = (item.next_attempt_at - before).total_seconds()
        assert expected_delay - 0.5 <= actual_delay <= expected_delay + 0.5

        await monitor.process_outbox()
        assert _get_item(monitor, "2026-07-20").retry_count == expected_attempt

    await monitor.process_outbox(force=True)
    item = _get_item(monitor, "2026-07-20")
    assert item.retry_count == 5
    assert item.next_attempt_at is None
    assert item.error_message.startswith("Retry exhausted")

    await monitor.process_outbox(force=True)
    assert _get_item(monitor, "2026-07-20").retry_count == 5
    assert attempts == 5


async def test_worker_automatically_retries_due_delivery(tmp_path, monkeypatch):
    monitor = APICostMonitor(db_path=str(tmp_path / "automatic.db"))
    monitor.webhook_url = "https://example.test/hook"
    monitor.webhook_retry_base_seconds = 0.01
    monitor.webhook_retry_max_seconds = 0.01
    monitor.webhook_poll_interval_seconds = 0.005
    monkeypatch.setattr(monitor_module.random, "uniform", lambda low, high: high)
    attempts = 0

    async def fail_once(message):
        nonlocal attempts
        attempts += 1
        return attempts > 1

    monkeypatch.setattr(monitor, "_send_webhook_notification", fail_once)
    assert monitor._claim_alert("2026-07-21", "threshold", 8.5)

    try:
        await monitor.start()
        await _wait_until(lambda: _get_item(monitor, "2026-07-21").status == "sent")
    finally:
        await monitor.close()

    assert attempts == 2
    assert _get_item(monitor, "2026-07-21").retry_count == 2


@pytest.mark.parametrize("last_attempt", [None, datetime(2020, 1, 1)])
async def test_stale_processing_recovery_handles_null_and_old_timestamps(
    tmp_path, last_attempt
):
    suffix = "null" if last_attempt is None else "old"
    monitor = APICostMonitor(db_path=str(tmp_path / f"stale-{suffix}.db"))
    assert monitor._claim_alert("2026-07-22", "threshold", 8.5)
    session = monitor.Session()
    try:
        item = session.query(WebhookOutbox).one()
        item.status = "processing"
        item.retry_count = 1
        item.last_attempt = last_attempt
        session.commit()
    finally:
        session.close()

    await monitor.recover_stale_deliveries(stale_timeout_seconds=30)

    item = _get_item(monitor, "2026-07-22")
    assert item.status == "failed"
    assert item.next_attempt_at is not None
    assert "Recovery:" in item.error_message


async def test_stale_processing_at_max_attempts_is_terminal(tmp_path):
    monitor = APICostMonitor(db_path=str(tmp_path / "stale-exhausted.db"))
    assert monitor._claim_alert("2026-07-26", "threshold", 8.5)
    session = monitor.Session()
    try:
        item = session.query(WebhookOutbox).one()
        item.status = "processing"
        item.retry_count = 5
        item.last_attempt = datetime(2020, 1, 1)
        session.commit()
    finally:
        session.close()

    await monitor.recover_stale_deliveries(stale_timeout_seconds=30)

    item = _get_item(monitor, "2026-07-26")
    assert item.status == "failed"
    assert item.next_attempt_at is None
    assert item.error_message.startswith("Retry exhausted")


async def test_cancellation_releases_claim_and_schedules_retry(tmp_path, monkeypatch):
    monitor = APICostMonitor(db_path=str(tmp_path / "cancel.db"))
    monitor.webhook_url = "https://example.test/hook"
    monitor.webhook_retry_base_seconds = 0.01
    monitor.webhook_poll_interval_seconds = 60
    delivery_started = asyncio.Event()

    async def block(message):
        delivery_started.set()
        await asyncio.Event().wait()

    monkeypatch.setattr(monitor, "_send_webhook_notification", block)
    assert monitor._claim_alert("2026-07-23", "threshold", 8.5)

    await monitor.start()
    await asyncio.wait_for(delivery_started.wait(), timeout=1)
    await monitor.close()

    item = _get_item(monitor, "2026-07-23")
    assert item.status == "failed"
    assert item.retry_count == 1
    assert item.next_attempt_at is not None
    assert "cancel" in item.error_message.lower()


async def test_every_attempt_uses_stable_idempotency_headers_and_sent_is_terminal(
    tmp_path, monkeypatch
):
    monitor = APICostMonitor(db_path=str(tmp_path / "headers.db"))
    monitor.webhook_url = "https://example.test/hook"
    responses = iter([500, 204])
    captured_headers: list[dict[str, str]] = []

    class FakeResponse:
        def __init__(self, status):
            self.status = status

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

    class FakeSession:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        def post(self, url, json=None, timeout=None, headers=None):
            captured_headers.append(headers)
            return FakeResponse(next(responses))

    monkeypatch.setattr(monitor_module.aiohttp, "ClientSession", FakeSession)
    assert monitor._claim_alert("2026-07-24", "threshold", 8.5)

    await monitor.process_outbox(force=True)
    await monitor.process_outbox(force=True)
    await monitor.process_outbox()

    expected_event_id = "api-cost:2026-07-24:threshold"
    assert captured_headers == [
        {"Idempotency-Key": expected_event_id, "X-Event-ID": expected_event_id},
        {"Idempotency-Key": expected_event_id, "X-Event-ID": expected_event_id},
    ]
    item = _get_item(monitor, "2026-07-24")
    assert item.status == "sent"
    assert item.retry_count == 2


async def test_worker_database_transactions_run_off_event_loop(tmp_path, monkeypatch):
    monitor = APICostMonitor(db_path=str(tmp_path / "off-loop.db"))
    monitor.webhook_url = "https://example.test/hook"
    assert monitor._claim_alert("2026-07-27", "threshold", 8.5)

    event_loop_thread = threading.get_ident()
    observed_threads: list[tuple[str, int]] = []
    helper_names = (
        "_recover_stale_deliveries_sync",
        "_select_outbox_item_ids",
        "_try_claim_outbox_item",
        "_complete_outbox_claim",
    )

    for helper_name in helper_names:
        original = getattr(monitor, helper_name)

        def record_thread(*args, _name=helper_name, _original=original, **kwargs):
            observed_threads.append((_name, threading.get_ident()))
            return _original(*args, **kwargs)

        monkeypatch.setattr(monitor, helper_name, record_thread)

    async def succeed(message):
        return True

    monkeypatch.setattr(monitor, "_send_webhook_notification", succeed)

    assert await monitor.process_outbox(force=True) == 1
    assert _get_item(monitor, "2026-07-27").status == "sent"
    assert {name for name, _ in observed_threads} == set(helper_names)
    assert all(thread_id != event_loop_thread for _, thread_id in observed_threads)
