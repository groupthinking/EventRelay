"""Disposable local PostgreSQL acceptance; uses only a private Unix socket."""
import json
import logging
import signal
import tempfile
from pathlib import Path
from unittest.mock import patch

import pgserver
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from youtube_extension.services.shared_sql_state import (
    SHARED_STATE_MIGRATION,
    SharedSQLStateStore,
    SharedStateSchemaError,
)

logging.disable(logging.CRITICAL)
signal.signal(signal.SIGTERM, lambda *_: (_ for _ in ()).throw(SystemExit(124)))
receipt = []
engines = []
server = None


def expect_hold(label, uri):
    try:
        store = SharedSQLStateStore(uri)
    except SharedStateSchemaError as exc:
        assert "security" in str(exc), str(exc)
        receipt.append({"case": label, "result": "PASS: rejected"})
    else:
        store.engine.dispose()
        raise AssertionError(label + " unexpectedly passed")


try:
    server = pgserver.get_server(tempfile.mkdtemp(prefix="eventrelay-pg-"), cleanup_mode="delete")
    base_url = make_url(server.get_uri()).set(drivername="postgresql+psycopg")
    assert base_url.host is None or base_url.host.startswith("/"), "Unix-socket-only server required"
    admin = create_engine(base_url)
    engines.append(admin)
    with admin.begin() as conn:
        version = conn.scalar(text("SELECT version()"))
        assert conn.scalar(text("SHOW listen_addresses")) == "", "IP listeners must be disabled"
        conn.exec_driver_sql("CREATE ROLE anon NOLOGIN")
        conn.exec_driver_sql("CREATE ROLE authenticated NOLOGIN")
        conn.exec_driver_sql("CREATE ROLE service_role NOLOGIN BYPASSRLS")
        conn.exec_driver_sql("CREATE ROLE review_server LOGIN BYPASSRLS")
        conn.exec_driver_sql("CREATE ROLE review_no_bypass LOGIN")
        conn.exec_driver_sql("GRANT service_role TO review_server, review_no_bypass")
        conn.exec_driver_sql("GRANT USAGE ON SCHEMA public TO service_role")
    admin_uri = base_url.render_as_string(hide_password=False)
    with patch.object(SharedSQLStateStore, "_ensure_schema", return_value=None):
        legacy = SharedSQLStateStore(admin_uri)
        legacy.metadata.create_all(legacy.engine)
        legacy.engine.dispose()
    expect_hold("legacy create_all without security", admin_uri)

    migration = Path(SHARED_STATE_MIGRATION).read_text()
    with admin.begin() as conn:
        conn.exec_driver_sql(migration)
        conn.exec_driver_sql(migration)
    receipt.append({"case": "migration applied twice", "result": "PASS"})

    service_url = base_url.set(username="review_server")
    service_uri = service_url.render_as_string(hide_password=False)
    store = SharedSQLStateStore(service_uri)
    engines.append(store.engine)
    assert store.metadata.schema == "public"
    store.save_session({"id": "pg-acceptance", "title": "original"})
    store.append_timeline_event("pg-acceptance", {"timestamp": "00:04", "summary": "source event", "content": "evidence"})
    store.append_a2a_message({"sender": "a", "recipient": "b", "conversation_id": "local-review", "timestamp": "00:04", "content": {"verified": True}})
    reopened = SharedSQLStateStore(service_uri)
    engines.append(reopened.engine)
    assert reopened.get_session("pg-acceptance")["title"] == "original"
    assert len(reopened.get_session("pg-acceptance")["timeline"]) == 1
    assert reopened.get_a2a_messages(conversation_id="local-review")[0]["content"] == {"verified": True}
    receipt.append({"case": "dedicated server-role table/sequence writes and fresh-store readback", "result": "PASS"})

    mutations = [
        ("RLS disabled", "ALTER TABLE public.shared_sessions DISABLE ROW LEVEL SECURITY", "ALTER TABLE public.shared_sessions ENABLE ROW LEVEL SECURITY"),
        ("RLS not forced", "ALTER TABLE public.shared_sessions NO FORCE ROW LEVEL SECURITY", "ALTER TABLE public.shared_sessions FORCE ROW LEVEL SECURITY"),
        ("direct client table grant", "GRANT SELECT ON public.shared_sessions TO anon", "REVOKE ALL ON public.shared_sessions FROM anon"),
        ("client BYPASSRLS", "ALTER ROLE anon BYPASSRLS", "ALTER ROLE anon NOBYPASSRLS"),
        ("client superuser", "ALTER ROLE anon SUPERUSER", "ALTER ROLE anon NOSUPERUSER"),
        ("missing service grant", "REVOKE UPDATE ON public.shared_sessions FROM service_role", "GRANT UPDATE ON public.shared_sessions TO service_role"),
        ("client sequence grant", "GRANT USAGE ON SEQUENCE public.shared_timeline_events_id_seq TO authenticated", "REVOKE ALL ON SEQUENCE public.shared_timeline_events_id_seq FROM authenticated"),
    ]
    for label, weaken, restore in mutations:
        with admin.begin() as conn:
            conn.exec_driver_sql(weaken)
        try:
            expect_hold(label, service_uri)
        finally:
            with admin.begin() as conn:
                conn.exec_driver_sql(restore)

    with admin.begin() as conn:
        conn.exec_driver_sql("CREATE ROLE review_client_group NOLOGIN")
        conn.exec_driver_sql("GRANT SELECT ON public.shared_sessions TO review_client_group")
        conn.exec_driver_sql("GRANT review_client_group TO authenticated")
    expect_hold("inherited client table privilege", service_uri)
    with admin.begin() as conn:
        conn.exec_driver_sql("REVOKE review_client_group FROM authenticated")
        conn.exec_driver_sql("REVOKE ALL ON public.shared_sessions FROM review_client_group")

    expect_hold("server role without BYPASSRLS", base_url.set(username="review_no_bypass").render_as_string(hide_password=False))

    with admin.begin() as conn:
        conn.exec_driver_sql("CREATE SCHEMA review_shadow")
        conn.exec_driver_sql("GRANT USAGE ON SCHEMA review_shadow TO service_role")
        conn.exec_driver_sql("CREATE TABLE review_shadow.shared_sessions (LIKE public.shared_sessions INCLUDING ALL)")
        conn.exec_driver_sql("GRANT ALL ON review_shadow.shared_sessions TO service_role")
    shadow_uri = service_url.update_query_dict({"options": "-csearch_path=review_shadow,public"}).render_as_string(hide_password=False)
    shadow_store = SharedSQLStateStore(shadow_uri)
    engines.append(shadow_store.engine)
    shadow_store.save_session({"id": "shadow-test", "title": "must stay public"})
    with admin.connect() as conn:
        assert conn.scalar(text("SELECT count(*) FROM public.shared_sessions WHERE session_id='shadow-test'")) == 1
        assert conn.scalar(text("SELECT count(*) FROM review_shadow.shared_sessions")) == 0
    receipt.append({"case": "hostile search_path still writes to validated public schema", "result": "PASS"})
    print(json.dumps({"postgres": version, "cases": receipt, "passed": len(receipt), "network": "private Unix socket; no IP listener"}, indent=2))
finally:
    for engine in engines:
        engine.dispose()
    if server is not None:
        server.cleanup()
        print("DISPOSABLE_POSTGRES_STOPPED_AND_DELETED")
