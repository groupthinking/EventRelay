"""Schema drift guard for AUDIT-007 (#2169).

Checks that docs/schema_inventory.json points at real files, that the shared-state
Supabase migration matches the SQLAlchemy models in shared_sql_state.py column for
column, and that every migrated table forces row-level security with no anon or
authenticated access.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from sqlalchemy.dialects import postgresql

from youtube_extension.services.shared_sql_state import (
    SHARED_STATE_MIGRATION,
    SharedSQLStateStore,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
INVENTORY_PATH = REPO_ROOT / "docs" / "schema_inventory.json"
MIGRATIONS_DIR = REPO_ROOT / "apps" / "web" / "supabase" / "migrations"
SHARED_TABLES = ("shared_sessions", "shared_timeline_events", "shared_a2a_messages")

_TYPE_ALIASES = {
    "TIMESTAMP WITH TIME ZONE": "TIMESTAMPTZ",
    "CHARACTER VARYING": "VARCHAR",
}


def _strip_comments(sql: str) -> str:
    return re.sub(r"--[^\n]*", "", sql)


def _load_inventory() -> dict:
    return json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))


def _normalize_type(raw: str) -> str:
    value = re.sub(r"\s+", " ", raw.strip().upper())
    for alias, canonical in _TYPE_ALIASES.items():
        value = value.replace(alias, canonical)
    return value.replace(" (", "(")


def _parse_create_tables(sql: str) -> dict[str, dict]:
    """Parse `create table` blocks into columns, primary keys and foreign keys."""

    tables: dict[str, dict] = {}
    pattern = re.compile(
        r"create\s+table\s+(?:if\s+not\s+exists\s+)?(?:public\.)?(\w+)\s*\((.*?)\);",
        re.IGNORECASE | re.DOTALL,
    )
    for name, body in pattern.findall(sql):
        columns: dict[str, dict] = {}
        primary_key: list[str] = []
        foreign_keys: list[str] = []
        for raw_line in body.split(",\n"):
            line = raw_line.strip().rstrip(",")
            if not line:
                continue
            lowered = line.lower()
            pk_match = re.search(r"primary\s+key\s*\(([^)]*)\)", lowered)
            if lowered.startswith("constraint") or lowered.startswith("primary key"):
                if pk_match:
                    primary_key.extend(c.strip().strip('"') for c in pk_match.group(1).split(","))
                if "foreign key" in lowered or "references" in lowered:
                    foreign_keys.append(line)
                continue
            col_match = re.match(r'"?(\w+)"?\s+(.*)$', line, re.DOTALL)
            assert col_match, f"unparsed column line in {name}: {line!r}"
            col_name, rest = col_match.groups()
            type_match = re.match(
                r"((?:timestamp with time zone|timestamptz|character varying|varchar|"
                r"serial|integer|text)(?:\s*\(\d+\))?)",
                rest,
                re.IGNORECASE,
            )
            assert type_match, f"unknown type for {name}.{col_name}: {rest!r}"
            remainder = rest[type_match.end():].lower()
            if "primary key" in remainder:
                primary_key.append(col_name)
            if "references" in remainder:
                foreign_keys.append(line)
            columns[col_name] = {
                "type": _normalize_type(type_match.group(1)),
                "not_null": "not null" in remainder or "primary key" in remainder,
                "default": "default" in remainder,
            }
        tables[name.lower()] = {
            "columns": columns,
            "primary_key": primary_key,
            "foreign_keys": foreign_keys,
        }
    return tables


def _parse_indexes(sql: str) -> dict[str, tuple[str, tuple[str, ...], bool]]:
    pattern = re.compile(
        r"create\s+(unique\s+)?index\s+(?:if\s+not\s+exists\s+)?(\w+)\s+on\s+"
        r"(?:public\.)?(\w+)\s*\(([^)]*)\)",
        re.IGNORECASE,
    )
    return {
        name: (table, tuple(c.strip().strip('"') for c in cols.split(",")), bool(unique))
        for unique, name, table, cols in pattern.findall(sql)
    }


def _model_tables() -> dict:
    store = SharedSQLStateStore("sqlite://")
    dialect = postgresql.dialect()
    expected: dict[str, dict] = {}
    for table in store.metadata.sorted_tables:
        columns = {}
        for column in table.columns:
            if column.primary_key and column.autoincrement is True:
                col_type = "SERIAL"
            else:
                col_type = _normalize_type(column.type.compile(dialect=dialect))
            columns[column.name] = {
                "type": col_type,
                "not_null": not column.nullable,
                "default": column.server_default is not None,
            }
        indexes = {
            index.name: (table.name, tuple(c.name for c in index.columns), bool(index.unique))
            for index in table.indexes
        }
        expected[table.name] = {
            "columns": columns,
            "primary_key": [c.name for c in table.primary_key.columns],
            "foreign_keys": [fk.target_fullname for fk in table.foreign_keys],
            "indexes": indexes,
        }
    store.engine.dispose()
    return expected


@pytest.fixture(scope="module")
def shared_migration_sql() -> str:
    path = REPO_ROOT / SHARED_STATE_MIGRATION
    assert path.is_file(), f"missing migration {SHARED_STATE_MIGRATION}"
    return _strip_comments(path.read_text(encoding="utf-8"))


def test_inventory_paths_exist_and_migrations_are_checked_in() -> None:
    inventory = _load_inventory()
    assert (REPO_ROOT / inventory["migrations_dir"]).is_dir()
    for entry in inventory["tables"]:
        assert (REPO_ROOT / entry["model_source"]).is_file(), entry["name"]
        if entry["status"] == "migrated":
            migration = REPO_ROOT / entry["migration"]
            assert migration.is_file(), entry["name"]
            assert migration.parent == MIGRATIONS_DIR
            assert re.fullmatch(r"\d{14}_[a-z0-9_]+\.sql", migration.name), migration.name


def test_shared_state_tables_are_inventoried_as_migrated_with_forced_rls() -> None:
    entries = {entry["name"]: entry for entry in _load_inventory()["tables"]}
    for table in SHARED_TABLES:
        entry = entries[table]
        assert entry["status"] == "migrated"
        assert entry["rls"] == "forced"
        assert entry["migration"] == SHARED_STATE_MIGRATION
        assert entry["model_source"] == "src/youtube_extension/services/shared_sql_state.py"


def test_shared_state_migration_matches_sqlalchemy_models(shared_migration_sql: str) -> None:
    parsed = _parse_create_tables(shared_migration_sql)
    parsed_indexes = _parse_indexes(shared_migration_sql)
    expected = _model_tables()

    assert set(parsed) == set(expected) == set(SHARED_TABLES)
    for name, model in expected.items():
        table = parsed[name]
        assert table["columns"] == model["columns"], name
        assert list(table["columns"]) == list(model["columns"]), f"{name} column order"
        assert table["primary_key"] == model["primary_key"], name
        assert table["foreign_keys"] == [] and model["foreign_keys"] == [], name
    migration_indexes = {k: v for k, v in parsed_indexes.items() if v[0] in expected}
    model_indexes = {k: v for m in expected.values() for k, v in m["indexes"].items()}
    assert migration_indexes == model_indexes


def test_shared_state_migration_is_idempotent(shared_migration_sql: str) -> None:
    lowered = shared_migration_sql.lower()
    assert len(re.findall(r"create\s+table\s+(?!if\s+not\s+exists)", lowered)) == 0
    assert len(re.findall(r"create\s+(?:unique\s+)?index\s+(?!if\s+not\s+exists)", lowered)) == 0
    assert "drop " not in lowered


@pytest.mark.parametrize(
    "migration_name",
    sorted(
        {
            entry["migration"]
            for entry in json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))["tables"]
            if entry["rls"] == "forced"
        }
    ),
)
def test_migrated_tables_force_rls_without_client_access(migration_name: str) -> None:
    sql = _strip_comments((REPO_ROOT / migration_name).read_text(encoding="utf-8")).lower()
    tables = [
        entry["name"]
        for entry in _load_inventory()["tables"]
        if entry["migration"] == migration_name and entry["rls"] == "forced"
    ]
    assert tables
    assert "create policy" not in sql
    assert not re.search(r"grant[^;]*\bto\s+[^;]*\b(anon|authenticated|public)\b", sql)
    for table in tables:
        qualified = rf"public\.{table}"
        assert re.search(rf"alter table {qualified} enable row level security;", sql), table
        assert re.search(rf"alter table {qualified} force row level security;", sql), table
        assert re.search(
            rf"revoke all on table {qualified} from public, anon, authenticated;", sql
        ), table
        assert re.search(
            rf"grant select, insert, update, delete on table {qualified} to service_role;", sql
        ), table


def test_shared_state_sequences_are_service_role_only(shared_migration_sql: str) -> None:
    sql = shared_migration_sql.lower()
    for sequence in ("shared_timeline_events_id_seq", "shared_a2a_messages_id_seq"):
        assert f"revoke all on sequence public.{sequence} from public, anon, authenticated;" in sql
        assert f"grant usage, select on sequence public.{sequence} to service_role;" in sql
