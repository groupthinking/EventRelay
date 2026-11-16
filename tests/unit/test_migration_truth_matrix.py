from __future__ import annotations

import json
import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
DOC_PATH = REPO_ROOT / "docs" / "MIGRATION_TRUTH.md"
MIGRATION_PATH = (
    REPO_ROOT
    / "apps"
    / "web"
    / "supabase"
    / "migrations"
    / "20260912214530_create_private_studio_chat_ownership.sql"
)
CHAT_STORE_PATH = REPO_ROOT / "apps" / "web" / "src" / "lib" / "studio" / "chat-store.ts"
SHARED_SQL_STATE_PATH = (
    REPO_ROOT / "src" / "youtube_extension" / "services" / "shared_sql_state.py"
)


def _extract_matrix(doc_text: str) -> dict:
    match = re.search(
        r"<!-- MIGRATION_TRUTH_MATRIX_START -->\s*```json\s*(\{.*?\})\s*```\s*<!-- MIGRATION_TRUTH_MATRIX_END -->",
        doc_text,
        flags=re.DOTALL,
    )
    assert match, "MIGRATION_TRUTH.md must include matrix markers with JSON content."
    return json.loads(match.group(1))


def _extract_studio_columns_from_migration(sql: str) -> set[str]:
    table_match = re.search(
        r"create table\s+public\.studio_chats\s*\((.*?)\);\s*",
        sql,
        flags=re.IGNORECASE | re.DOTALL,
    )
    assert table_match, "Expected CREATE TABLE public.studio_chats block in migration."
    columns: set[str] = set()
    for raw_line in table_match.group(1).splitlines():
        line = raw_line.strip().rstrip(",")
        if not line:
            continue
        if line.lower().startswith(("constraint ", "primary key ", "foreign key ", "unique ")):
            continue
        match = re.match(r"([a-z_][a-z0-9_]*)\s+", line, flags=re.IGNORECASE)
        if match:
            columns.add(match.group(1))
    return columns


def _extract_studio_columns_from_chat_store(chat_store: str) -> set[str]:
    match = re.search(r"const columns = '([^']+)';", chat_store)
    assert match, "Expected `const columns = '...';` in chat-store.ts"
    return {value.strip() for value in match.group(1).split(",")}


def test_migration_truth_matrix_reconciles_active_sql_surfaces() -> None:
    doc_text = DOC_PATH.read_text(encoding="utf-8")
    matrix = _extract_matrix(doc_text)

    assert "production_domains" in matrix
    assert "non_production_domains" in matrix

    production_by_table = {
        entry["table"]: entry for entry in matrix["production_domains"] if "table" in entry
    }
    assert "studio_chats" in production_by_table

    studio_entry = production_by_table["studio_chats"]
    assert studio_entry["migration_file"] == str(
        MIGRATION_PATH.relative_to(REPO_ROOT).as_posix()
    )
    assert studio_entry.get("rls") == "enabled+forced"
    assert studio_entry.get("tenant_boundary") == "owner_subject + service_role access"

    migration_sql = MIGRATION_PATH.read_text(encoding="utf-8")
    chat_store_text = CHAT_STORE_PATH.read_text(encoding="utf-8")

    migration_columns = _extract_studio_columns_from_migration(migration_sql)
    chat_store_columns = _extract_studio_columns_from_chat_store(chat_store_text)
    mapped_columns = set(studio_entry.get("columns", []))

    assert migration_columns == chat_store_columns
    assert mapped_columns == migration_columns

    non_prod_by_table = {
        entry["table"]: entry
        for entry in matrix["non_production_domains"]
        if "table" in entry
    }
    for table_name in ("shared_sessions", "shared_timeline_events", "shared_a2a_messages"):
        assert table_name in non_prod_by_table
        assert non_prod_by_table[table_name]["migration_strategy"] == "runtime_create_all"
        assert non_prod_by_table[table_name]["owner_file"] == str(
            SHARED_SQL_STATE_PATH.relative_to(REPO_ROOT).as_posix()
        )

    assert "alembic_status" in matrix
    assert matrix["alembic_status"]["state"] in {"retired", "absent"}
