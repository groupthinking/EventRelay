"""Live PostgreSQL acceptance tests for the API-cost migration substrate."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from youtube_extension.backend.api_cost_migrate import apply_runtime_grants
from youtube_extension.backend.models.api_cost import WebhookOutbox
from youtube_extension.backend.services.api_cost_monitor import APICostMonitor

RUNTIME_URL = os.getenv("API_COST_TEST_RUNTIME_DATABASE_URL")
ROTATED_RUNTIME_URL = os.getenv("API_COST_TEST_ROTATED_RUNTIME_DATABASE_URL")
UNSAFE_RUNTIME_URL = os.getenv("API_COST_TEST_UNSAFE_RUNTIME_DATABASE_URL")
ADMIN_URL = os.getenv("API_COST_TEST_ADMIN_DATABASE_URL")
DISPOSABLE_DATABASE = os.getenv("API_COST_TEST_DISPOSABLE_DATABASE") == "true"

pytestmark = pytest.mark.skipif(
    not RUNTIME_URL or not DISPOSABLE_DATABASE,
    reason=(
        "live PostgreSQL tests require API_COST_TEST_RUNTIME_DATABASE_URL and "
        "API_COST_TEST_DISPOSABLE_DATABASE=true"
    ),
)


@pytest.fixture
def monitor(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("API_COST_TRACKING", "true")
    monkeypatch.setenv("API_DAILY_BUDGET", "1000000")
    instance = APICostMonitor(
        database_url=RUNTIME_URL,
        initialize_schema=False,
    )
    try:
        yield instance
    finally:
        if instance.engine is not None:
            instance.engine.dispose()


def test_runtime_monitor_is_ready_without_alembic_table_access(
    monitor: APICostMonitor,
) -> None:
    monitor.ensure_database_ready()

    assert monitor.engine is not None
    with monitor.engine.connect() as connection:
        current_user, member = connection.execute(
            text(
                "SELECT current_user, "
                "pg_has_role(current_user, 'api_cost_runtime', 'MEMBER')"
            )
        ).one()
    assert current_user == "api_cost_app"
    assert member is True


def test_old_runtime_remains_ready_with_future_nullable_column(
    monitor: APICostMonitor,
) -> None:
    """An additive migration must remain compatible with the serving revision."""
    ddl = create_engine(os.environ["DATABASE_URL"], future=True)
    column_added = False
    try:
        with ddl.begin() as connection:
            connection.execute(
                text(
                    "ALTER TABLE public.api_usage "
                    "ADD COLUMN future_runtime_metadata text"
                )
            )
            column_added = True

        monitor.ensure_database_ready()
    finally:
        if column_added:
            with ddl.begin() as connection:
                connection.execute(
                    text(
                        "ALTER TABLE public.api_usage "
                        "DROP COLUMN future_runtime_metadata"
                    )
                )
        ddl.dispose()


@pytest.mark.asyncio
async def test_usage_written_by_monitor_is_visible_to_rotated_login(
    monitor: APICostMonitor,
) -> None:
    marker = f"postgres-ci-{uuid4()}"
    record = await monitor.record_usage(
        "openai",
        marker,
        1000,
        model="gpt-4o-mini",
        request_type="migration-acceptance",
    )
    assert record is not None

    rotated = create_engine(ROTATED_RUNTIME_URL, future=True)
    try:
        with rotated.connect() as connection:
            stored = connection.execute(
                text(
                    "SELECT service, endpoint, tokens_used "
                    "FROM api_usage WHERE endpoint = :endpoint"
                ),
                {"endpoint": marker},
            ).one()
        assert stored == ("openai", marker, 1000)
    finally:
        rotated.dispose()


@pytest.mark.asyncio
async def test_postgres_daily_cost_enqueues_a_pending_threshold_alert(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("API_COST_TRACKING", "true")
    monkeypatch.setenv("API_ALERT_THRESHOLD", "0.00001")
    monkeypatch.setenv("API_DAILY_BUDGET", "1000000")
    instance = APICostMonitor(database_url=RUNTIME_URL, initialize_schema=False)
    try:
        marker = f"threshold-{uuid4()}"
        await instance.record_usage(
            "openai",
            marker,
            1000,
            model="gpt-4o-mini",
            request_type="postgres-date-acceptance",
        )

        today = datetime.now(timezone.utc).date().isoformat()
        assert await instance.get_daily_cost(today) > 0
        assert instance.engine is not None
        with Session(instance.engine) as session:
            pending = session.scalar(
                select(WebhookOutbox).where(
                    WebhookOutbox.utc_date == today,
                    WebhookOutbox.alert_type == "threshold",
                )
            )
        assert pending is not None
        assert pending.status == "pending"
        assert pending.retry_count == 0
    finally:
        if instance.engine is not None:
            instance.engine.dispose()


def test_readiness_rejects_a_login_with_direct_unsafe_privileges(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    if not UNSAFE_RUNTIME_URL:
        pytest.skip("API_COST_TEST_UNSAFE_RUNTIME_DATABASE_URL is not configured")

    ddl = create_engine(os.environ["DATABASE_URL"], future=True)
    unsafe = APICostMonitor(database_url=UNSAFE_RUNTIME_URL, initialize_schema=False)
    try:
        with ddl.begin() as connection:
            connection.execute(
                text("GRANT TRUNCATE ON public.api_usage TO api_cost_app_unsafe")
            )

        with pytest.raises(RuntimeError, match="no_unsafe_table_privileges"):
            unsafe.ensure_database_ready()
    finally:
        with ddl.begin() as connection:
            connection.execute(
                text("REVOKE TRUNCATE ON public.api_usage FROM api_cost_app_unsafe")
            )
        ddl.dispose()
        if unsafe.engine is not None:
            unsafe.engine.dispose()


def test_readiness_rejects_access_to_unrelated_shared_database_table() -> None:
    if not UNSAFE_RUNTIME_URL:
        pytest.skip("API_COST_TEST_UNSAFE_RUNTIME_DATABASE_URL is not configured")

    ddl = create_engine(os.environ["DATABASE_URL"], future=True)
    unsafe = APICostMonitor(database_url=UNSAFE_RUNTIME_URL, initialize_schema=False)
    try:
        with ddl.begin() as connection:
            connection.execute(
                text("GRANT SELECT ON public.tenants TO api_cost_app_unsafe")
            )

        with pytest.raises(RuntimeError, match="no_unexpected_table_access"):
            unsafe.ensure_database_ready()
    finally:
        with ddl.begin() as connection:
            connection.execute(
                text("REVOKE SELECT ON public.tenants FROM api_cost_app_unsafe")
            )
        ddl.dispose()
        if unsafe.engine is not None:
            unsafe.engine.dispose()


def test_grant_reconciliation_rejects_unrelated_group_access() -> None:
    ddl = create_engine(os.environ["DATABASE_URL"], future=True)
    try:
        with ddl.begin() as connection:
            connection.execute(
                text("GRANT SELECT ON public.tenants TO api_cost_runtime")
            )
            try:
                with pytest.raises(RuntimeError, match="unrelated table"):
                    apply_runtime_grants(connection, "api_cost_runtime")
            finally:
                connection.execute(
                    text("REVOKE SELECT ON public.tenants FROM api_cost_runtime")
                )
    finally:
        ddl.dispose()


def test_readiness_rejects_a_login_with_database_create(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    if not UNSAFE_RUNTIME_URL:
        pytest.skip("API_COST_TEST_UNSAFE_RUNTIME_DATABASE_URL is not configured")

    ddl = create_engine(os.environ["DATABASE_URL"], future=True)
    unsafe = APICostMonitor(database_url=UNSAFE_RUNTIME_URL, initialize_schema=False)
    try:
        with ddl.begin() as connection:
            connection.execute(
                text("GRANT CREATE ON DATABASE eventrelay TO api_cost_app_unsafe")
            )

        with pytest.raises(RuntimeError, match="no_database_create"):
            unsafe.ensure_database_ready()
    finally:
        with ddl.begin() as connection:
            connection.execute(
                text("REVOKE CREATE ON DATABASE eventrelay FROM api_cost_app_unsafe")
            )
        ddl.dispose()
        if unsafe.engine is not None:
            unsafe.engine.dispose()


def test_readiness_rejects_elevated_runtime_group(
    monitor: APICostMonitor,
) -> None:
    if not ADMIN_URL:
        pytest.skip("API_COST_TEST_ADMIN_DATABASE_URL is not configured")

    admin = create_engine(ADMIN_URL, future=True)
    try:
        with admin.begin() as connection:
            connection.execute(text("ALTER ROLE api_cost_runtime BYPASSRLS"))

        with pytest.raises(RuntimeError, match="group_non_elevated"):
            monitor.ensure_database_ready()
    finally:
        with admin.begin() as connection:
            connection.execute(text("ALTER ROLE api_cost_runtime NOBYPASSRLS"))
        admin.dispose()


def test_readiness_rejects_nested_runtime_group(
    monitor: APICostMonitor,
) -> None:
    if not ADMIN_URL:
        pytest.skip("API_COST_TEST_ADMIN_DATABASE_URL is not configured")

    admin = create_engine(ADMIN_URL, future=True)
    parent_role = f"api_cost_parent_{uuid4().hex[:8]}"
    parent_created = False
    membership_granted = False
    try:
        with admin.begin() as connection:
            connection.execute(text(f'CREATE ROLE "{parent_role}" NOLOGIN'))
            parent_created = True
            connection.execute(text(f'GRANT "{parent_role}" TO api_cost_runtime'))
            membership_granted = True

        with pytest.raises(RuntimeError, match="group_no_parent_roles"):
            monitor.ensure_database_ready()
    finally:
        if parent_created:
            with admin.begin() as connection:
                if membership_granted:
                    connection.execute(
                        text(f'REVOKE "{parent_role}" FROM api_cost_runtime')
                    )
                connection.execute(text(f'DROP ROLE "{parent_role}"'))
        admin.dispose()


def test_readiness_rejects_missing_worker_index(
    monitor: APICostMonitor,
) -> None:
    ddl = create_engine(os.environ["DATABASE_URL"], future=True)
    index_dropped = False
    try:
        with ddl.begin() as connection:
            connection.execute(text("DROP INDEX public.ix_webhook_outbox_due"))
            index_dropped = True

        with pytest.raises(RuntimeError, match="outbox_due_index"):
            monitor.ensure_database_ready()
    finally:
        if index_dropped:
            with ddl.begin() as connection:
                connection.execute(
                    text(
                        "CREATE INDEX ix_webhook_outbox_due ON public.webhook_outbox "
                        "(status, next_attempt_at, retry_count, id)"
                    )
                )
        ddl.dispose()


def test_readiness_rejects_and_recovers_from_malformed_serial_default(
    monitor: APICostMonitor,
) -> None:
    ddl = create_engine(os.environ["DATABASE_URL"], future=True)
    default_changed = False
    try:
        with ddl.begin() as connection:
            connection.execute(
                text(
                    "ALTER TABLE public.api_usage ALTER COLUMN id SET DEFAULT "
                    "(nextval('public.api_usage_id_seq'::regclass) * 0)"
                )
            )
            default_changed = True

        with pytest.raises(RuntimeError, match="column_contract"):
            monitor.ensure_database_ready()
    finally:
        if default_changed:
            with ddl.begin() as connection:
                connection.execute(
                    text(
                        "ALTER TABLE public.api_usage ALTER COLUMN id SET DEFAULT "
                        "nextval('public.api_usage_id_seq'::regclass)"
                    )
                )
        ddl.dispose()

    monitor.ensure_database_ready()


def test_readiness_rejects_and_recovers_from_weakened_check_definition(
    monitor: APICostMonitor,
) -> None:
    ddl = create_engine(os.environ["DATABASE_URL"], future=True)
    check_weakened = False
    try:
        with ddl.begin() as connection:
            connection.execute(
                text(
                    "ALTER TABLE public.webhook_outbox "
                    "DROP CONSTRAINT ck_webhook_outbox_status, "
                    "ADD CONSTRAINT ck_webhook_outbox_status CHECK (true)"
                )
            )
            check_weakened = True

        with pytest.raises(RuntimeError, match="check_definitions"):
            monitor.ensure_database_ready()
    finally:
        if check_weakened:
            with ddl.begin() as connection:
                connection.execute(
                    text(
                        "ALTER TABLE public.webhook_outbox "
                        "DROP CONSTRAINT ck_webhook_outbox_status, "
                        "ADD CONSTRAINT ck_webhook_outbox_status "
                        "CHECK (status IN "
                        "('pending', 'processing', 'sent', 'failed'))"
                    )
                )
        ddl.dispose()

    monitor.ensure_database_ready()


def test_runtime_role_can_mutate_outbox_but_cannot_execute_ddl(
    monitor: APICostMonitor,
) -> None:
    assert monitor.engine is not None
    unique_date = f"ci-{uuid4().hex[:7]}"
    with Session(monitor.engine) as session:
        item = WebhookOutbox(
            utc_date=unique_date,
            alert_type="budget_threshold",
            status="pending",
            retry_count=0,
            next_attempt_at=datetime.now(timezone.utc),
            current_cost=1.25,
            payload='{"acceptance": true}',
        )
        session.add(item)
        session.commit()
        item_id = item.id

        item.status = "processing"
        item.next_attempt_at = None
        session.commit()

        persisted = session.scalar(
            select(WebhookOutbox).where(WebhookOutbox.id == item_id)
        )
        assert persisted is not None
        assert persisted.status == "processing"
        assert persisted.next_attempt_at is None

        session.delete(persisted)
        session.commit()

    with monitor.engine.connect() as connection:
        transaction = connection.begin()
        with pytest.raises(DBAPIError):
            connection.execute(text("CREATE TABLE api_cost_runtime_must_fail(id int)"))
        transaction.rollback()


def test_runtime_role_cannot_read_migration_ownership_state(
    monitor: APICostMonitor,
) -> None:
    assert monitor.engine is not None
    with monitor.engine.connect() as connection:
        transaction = connection.begin()
        with pytest.raises(DBAPIError):
            connection.execute(text("SELECT version_num FROM alembic_version"))
        transaction.rollback()


def test_pending_outbox_survives_writer_exit_and_reader_process() -> None:
    """Committed work remains visible after the writer process has exited."""
    unique_date = f"rv-{uuid4().hex[:7]}"
    writer_environment = os.environ.copy()
    writer_environment["API_COST_SUBPROCESS_DATABASE_URL"] = str(RUNTIME_URL)
    writer_environment["API_COST_SUBPROCESS_UTC_DATE"] = unique_date
    writer = subprocess.run(
        [
            sys.executable,
            "-c",
            """
import json
import os
from sqlalchemy import create_engine, text

engine = create_engine(os.environ["API_COST_SUBPROCESS_DATABASE_URL"], future=True)
try:
    with engine.begin() as connection:
        item_id = connection.execute(
            text(
                "INSERT INTO webhook_outbox "
                "(utc_date, alert_type, status, retry_count, current_cost, payload) "
                "VALUES (:utc_date, 'revision_replacement', 'pending', 0, 2.5, "
                ":payload) RETURNING id"
            ),
            {
                "utc_date": os.environ["API_COST_SUBPROCESS_UTC_DATE"],
                "payload": '{"delivery_enabled": false}',
            },
        ).scalar_one()
    print("OUTBOX_WRITER=" + json.dumps({"id": item_id, "pid": os.getpid()}))
finally:
    engine.dispose()
""",
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
        env=writer_environment,
    )
    writer_payload = json.loads(
        next(
            line.removeprefix("OUTBOX_WRITER=")
            for line in writer.stdout.splitlines()
            if line.startswith("OUTBOX_WRITER=")
        )
    )

    reader_environment = os.environ.copy()
    reader_environment["API_COST_SUBPROCESS_DATABASE_URL"] = str(ROTATED_RUNTIME_URL)
    reader_environment["API_COST_SUBPROCESS_ITEM_ID"] = str(writer_payload["id"])
    reader = subprocess.run(
        [
            sys.executable,
            "-c",
            """
import json
import os
from sqlalchemy import create_engine, text

engine = create_engine(os.environ["API_COST_SUBPROCESS_DATABASE_URL"], future=True)
try:
    with engine.begin() as connection:
        item = connection.execute(
            text(
                "SELECT status, retry_count, current_cost, payload "
                "FROM webhook_outbox WHERE id = :item_id"
            ),
            {"item_id": int(os.environ["API_COST_SUBPROCESS_ITEM_ID"])},
        ).mappings().one()
        connection.execute(
            text("DELETE FROM webhook_outbox WHERE id = :item_id"),
            {"item_id": int(os.environ["API_COST_SUBPROCESS_ITEM_ID"])},
        )
    print(
        "OUTBOX_READER="
        + json.dumps(
            {
                "pid": os.getpid(),
                "status": item["status"],
                "retry_count": item["retry_count"],
                "current_cost": item["current_cost"],
                "payload": item["payload"],
            },
            sort_keys=True,
        )
    )
finally:
    engine.dispose()
""",
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
        env=reader_environment,
    )
    reader_payload = json.loads(
        next(
            line.removeprefix("OUTBOX_READER=")
            for line in reader.stdout.splitlines()
            if line.startswith("OUTBOX_READER=")
        )
    )

    assert writer_payload["pid"] != os.getpid()
    assert reader_payload["pid"] not in {os.getpid(), writer_payload["pid"]}
    assert reader_payload == {
        "pid": reader_payload["pid"],
        "status": "pending",
        "retry_count": 0,
        "current_cost": 2.5,
        "payload": '{"delivery_enabled": false}',
    }


def test_pending_outbox_is_visible_to_two_concurrent_runtime_processes() -> None:
    """Both runtime logins observe the same durable row at overlapping times."""
    unique_date = f"cc-{uuid4().hex[:7]}"
    seed_engine = create_engine(RUNTIME_URL, future=True)
    try:
        with seed_engine.begin() as connection:
            item_id = connection.execute(
                text(
                    "INSERT INTO webhook_outbox "
                    "(utc_date, alert_type, status, retry_count, current_cost, payload) "
                    "VALUES (:utc_date, 'concurrent_visibility', 'pending', 0, "
                    "3.5, :payload) RETURNING id"
                ),
                {
                    "utc_date": unique_date,
                    "payload": '{"delivery_enabled": false}',
                },
            ).scalar_one()

        reader_script = """
import json
import os
import time
from sqlalchemy import create_engine, text

engine = create_engine(os.environ["API_COST_SUBPROCESS_DATABASE_URL"], future=True)
try:
    with engine.connect() as connection:
        start_at = float(os.environ["API_COST_SUBPROCESS_START_AT"])
        while time.time() < start_at:
            time.sleep(0.005)
        interval_start = time.time()
        item = connection.execute(
            text(
                "SELECT status, retry_count, current_cost FROM webhook_outbox "
                "WHERE id = :item_id"
            ),
            {"item_id": int(os.environ["API_COST_SUBPROCESS_ITEM_ID"])},
        ).mappings().one()
        connection.execute(text("SELECT pg_sleep(0.25)"))
        interval_end = time.time()
    print(
        "OUTBOX_CONCURRENT_READER="
        + json.dumps(
            {
                "pid": os.getpid(),
                "interval_start": interval_start,
                "interval_end": interval_end,
                "status": item["status"],
                "retry_count": item["retry_count"],
                "current_cost": item["current_cost"],
            },
            sort_keys=True,
        )
    )
finally:
    engine.dispose()
"""
        start_at = time.time() + 2
        readers: list[subprocess.Popen[str]] = []
        for database_url in (RUNTIME_URL, ROTATED_RUNTIME_URL):
            environment = os.environ.copy()
            environment.update(
                {
                    "API_COST_SUBPROCESS_DATABASE_URL": str(database_url),
                    "API_COST_SUBPROCESS_ITEM_ID": str(item_id),
                    "API_COST_SUBPROCESS_START_AT": str(start_at),
                }
            )
            readers.append(
                subprocess.Popen(
                    [sys.executable, "-c", reader_script],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    env=environment,
                )
            )

        payloads = []
        for reader in readers:
            stdout, stderr = reader.communicate(timeout=30)
            assert reader.returncode == 0, stderr
            payloads.append(
                json.loads(
                    next(
                        line.removeprefix("OUTBOX_CONCURRENT_READER=")
                        for line in stdout.splitlines()
                        if line.startswith("OUTBOX_CONCURRENT_READER=")
                    )
                )
            )

        assert payloads[0]["pid"] != payloads[1]["pid"]
        assert all(payload["status"] == "pending" for payload in payloads)
        assert all(payload["retry_count"] == 0 for payload in payloads)
        assert all(payload["current_cost"] == 3.5 for payload in payloads)
        assert max(payload["interval_start"] for payload in payloads) < min(
            payload["interval_end"] for payload in payloads
        )
    finally:
        with seed_engine.begin() as connection:
            connection.execute(
                text("DELETE FROM webhook_outbox WHERE utc_date = :utc_date"),
                {"utc_date": unique_date},
            )
        seed_engine.dispose()
