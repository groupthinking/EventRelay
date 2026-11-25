from __future__ import annotations

import ast
import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DOC_PATH = REPO_ROOT / "docs" / "MIGRATION_TRUTH.md"
MIGRATIONS_DIR = REPO_ROOT / "apps" / "web" / "supabase" / "migrations"
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


def _strip_sql_comments(sql: str) -> str:
    without_block = re.sub(r"/\*.*?\*/", " ", sql, flags=re.DOTALL)
    return re.sub(r"--[^\n]*", "", without_block)


def _split_sql_statements(sql: str) -> list[str]:
    clean = _strip_sql_comments(sql)
    return [stmt.strip() for stmt in clean.split(";") if stmt.strip()]


def _extract_parenthesized_block(text: str, open_idx: int) -> tuple[str, int]:
    depth = 0
    for idx in range(open_idx, len(text)):
        ch = text[idx]
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                return text[open_idx + 1 : idx], idx
    raise AssertionError("Unclosed parenthesized SQL block.")


def _split_top_level_commas(body: str) -> list[str]:
    parts: list[str] = []
    current: list[str] = []
    depth = 0
    for ch in body:
        if ch == "(":
            depth += 1
        elif ch == ")" and depth > 0:
            depth -= 1
        if ch == "," and depth == 0:
            item = "".join(current).strip()
            if item:
                parts.append(item)
            current = []
            continue
        current.append(ch)
    tail = "".join(current).strip()
    if tail:
        parts.append(tail)
    return parts


def _normalize_ident(raw: str) -> str:
    return raw.strip().strip('"').lower()


def _reconstruct_ordered_supabase_schema(
    migration_files: list[Path],
) -> tuple[dict[str, set[str]], list[str]]:
    """Replay ordered CREATE TABLE and ALTER TABLE migrations into final column sets."""
    assert migration_files, "Expected at least one Supabase SQL migration file."
    tables: dict[str, set[str]] = {}
    statements: list[str] = []

    for migration_file in migration_files:
        for stmt in _split_sql_statements(migration_file.read_text(encoding="utf-8")):
            statements.append(stmt)
            create_match = re.match(
                r"create\s+table\s+(?:if\s+not\s+exists\s+)?(?:public\.)?([a-z_][a-z0-9_]*)\s*\(",
                stmt,
                flags=re.IGNORECASE,
            )
            if create_match:
                table_name = _normalize_ident(create_match.group(1))
                open_paren = stmt.index("(", create_match.start())
                block, _ = _extract_parenthesized_block(stmt, open_paren)
                cols = tables.setdefault(table_name, set())
                for entry in _split_top_level_commas(block):
                    lowered = entry.lstrip().lower()
                    if lowered.startswith(
                        ("constraint ", "primary key ", "foreign key ", "unique ", "check ")
                    ):
                        continue
                    col_match = re.match(r'"?([a-z_][a-z0-9_]*)"?\s+', entry, flags=re.IGNORECASE)
                    if col_match:
                        cols.add(_normalize_ident(col_match.group(1)))
                continue

            drop_table_match = re.match(
                r"drop\s+table\s+(?:if\s+exists\s+)?(?:public\.)?([a-z_][a-z0-9_]*)",
                stmt,
                flags=re.IGNORECASE,
            )
            if drop_table_match:
                tables.pop(_normalize_ident(drop_table_match.group(1)), None)
                continue

            alter_match = re.match(
                r"alter\s+table\s+(?:if\s+exists\s+)?(?:only\s+)?(?:public\.)?([a-z_][a-z0-9_]*)\s+(.+)$",
                stmt,
                flags=re.IGNORECASE | re.DOTALL,
            )
            if alter_match:
                table_name = _normalize_ident(alter_match.group(1))
                cols = tables.setdefault(table_name, set())
                for action in _split_top_level_commas(alter_match.group(2)):
                    add_col = re.match(
                        r"add\s+(?:column\s+)?(?:if\s+not\s+exists\s+)?\"?([a-z_][a-z0-9_]*)\"?\s+",
                        action,
                        flags=re.IGNORECASE,
                    )
                    if add_col:
                        col_name = _normalize_ident(add_col.group(1))
                        if col_name not in {"constraint", "primary", "unique", "check", "foreign"}:
                            cols.add(col_name)
                        continue
                    drop_col = re.match(
                        r"drop\s+(?:column\s+)?(?:if\s+exists\s+)?\"?([a-z_][a-z0-9_]*)\"?",
                        action,
                        flags=re.IGNORECASE,
                    )
                    if drop_col:
                        col_name = _normalize_ident(drop_col.group(1))
                        if col_name != "constraint":
                            cols.discard(col_name)
                        continue
                    rename_col = re.match(
                        r"rename\s+(?:column\s+)?\"?([a-z_][a-z0-9_]*)\"?\s+to\s+\"?([a-z_][a-z0-9_]*)\"?",
                        action,
                        flags=re.IGNORECASE,
                    )
                    if rename_col:
                        cols.discard(_normalize_ident(rename_col.group(1)))
                        cols.add(_normalize_ident(rename_col.group(2)))

    return tables, statements


def _extract_studio_columns_from_projection(chat_store: str) -> set[str]:
    match = re.search(r"const columns = '([^']+)';", chat_store)
    assert match, "Expected `const columns = '...';` in chat-store.ts"
    return {value.strip() for value in match.group(1).split(",") if value.strip()}


def _extract_studio_columns_from_row_schema(chat_store: str) -> set[str]:
    match = re.search(r"const\s+rowSchema\s*=\s*z\.object\s*\(\s*\{", chat_store)
    assert match, "Expected `const rowSchema = z.object({ ... })` in chat-store.ts"
    start_brace = match.end() - 1
    depth = 0
    end_brace = -1
    for idx in range(start_brace, len(chat_store)):
        ch = chat_store[idx]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                end_brace = idx
                break
    assert end_brace > start_brace, "Expected closing brace for rowSchema."

    object_body = chat_store[start_brace + 1 : end_brace]
    keys: set[str] = set()
    nested_depth = 0
    for line in object_body.splitlines():
        if nested_depth == 0:
            key_match = re.match(r"^\s*([a-z_][a-z0-9_]*)\s*:", line, flags=re.IGNORECASE)
            if key_match:
                keys.add(key_match.group(1))
        for ch in line:
            if ch in "{[(":
                nested_depth += 1
            elif ch in "}])" and nested_depth > 0:
                nested_depth -= 1
    assert keys, "Expected rowSchema properties in chat-store.ts"
    return keys


def _extract_shared_sql_tables_from_ast(source_path: Path) -> tuple[dict[str, set[str]], bool]:
    """Parse Table(...) declarations and verify create_all() via Python AST."""
    tree = ast.parse(source_path.read_text(encoding="utf-8"), filename=str(source_path))
    discovered: dict[str, set[str]] = {}
    has_create_all = False

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Attribute) and func.attr == "create_all":
                has_create_all = True
            is_table_call = (isinstance(func, ast.Name) and func.id == "Table") or (
                isinstance(func, ast.Attribute) and func.attr == "Table"
            )
            if is_table_call and node.args and isinstance(node.args[0], ast.Constant):
                table_name = str(node.args[0].value)
                col_names: set[str] = set()
                for arg in node.args[2:]:
                    if isinstance(arg, ast.Call):
                        col_func = arg.func
                        is_col = (isinstance(col_func, ast.Name) and col_func.id == "Column") or (
                            isinstance(col_func, ast.Attribute) and col_func.attr == "Column"
                        )
                        if is_col and arg.args and isinstance(arg.args[0], ast.Constant):
                            col_names.add(str(arg.args[0].value))
                discovered[table_name] = col_names

    return discovered, has_create_all


def test_migration_truth_matrix_reconciles_active_sql_surfaces() -> None:
    doc_text = DOC_PATH.read_text(encoding="utf-8")
    matrix = _extract_matrix(doc_text)

    assert "production_domains" in matrix
    assert "runtime_managed_domains" in matrix
    assert (
        "non_production_domains" not in matrix
    ), "SharedSQLStateStore tables are production-reachable via DATABASE_URL and must not be marked non-production."

    migration_files = sorted(MIGRATIONS_DIR.glob("*.sql"))
    discovered_tables, sql_statements = _reconstruct_ordered_supabase_schema(migration_files)

    production_by_table = {
        entry["table"]: entry for entry in matrix["production_domains"] if "table" in entry
    }
    assert set(production_by_table.keys()) == set(
        discovered_tables.keys()
    ), "Production matrix tables must match every table discovered across apps/web/supabase/migrations/*.sql."

    studio_entry = production_by_table["studio_chats"]
    expected_bootstrap = (
        MIGRATIONS_DIR / "20260912214530_create_private_studio_chat_ownership.sql"
    ).relative_to(REPO_ROOT).as_posix()
    assert studio_entry["migration_file"] == expected_bootstrap
    assert studio_entry.get("rls") == "enabled+forced"
    assert studio_entry.get("tenant_boundary") == "owner_subject + service_role access"

    chat_store_text = CHAT_STORE_PATH.read_text(encoding="utf-8")
    projection_columns = _extract_studio_columns_from_projection(chat_store_text)
    row_schema_columns = _extract_studio_columns_from_row_schema(chat_store_text)
    migration_columns = discovered_tables["studio_chats"]
    mapped_columns = set(studio_entry.get("columns", []))

    assert row_schema_columns == projection_columns
    assert projection_columns == migration_columns
    assert mapped_columns == migration_columns

    # Validate SQL-side RLS hardening, role revocations/grants, and tenant uniqueness across ordered chain.
    normalized_stmts = [" ".join(stmt.lower().split()) for stmt in sql_statements]
    rls_enabled = False
    rls_forced = False
    revoked_roles: set[str] = set()
    service_role_privileges: set[str] = set()

    for norm in normalized_stmts:
        if "alter table public.studio_chats enable row level security" in norm:
            rls_enabled = True
        elif "alter table public.studio_chats disable row level security" in norm:
            rls_enabled = False
        if "alter table public.studio_chats force row level security" in norm:
            rls_forced = True
        elif "alter table public.studio_chats no force row level security" in norm:
            rls_forced = False

        revoke_match = re.match(
            r"revoke\s+all\s+(?:privileges\s+)?on\s+(?:table\s+)?public\.studio_chats\s+from\s+(.+)$",
            norm,
        )
        if revoke_match:
            for role in revoke_match.group(1).split(","):
                revoked_roles.add(role.strip())

        grant_match = re.match(
            r"grant\s+(.+?)\s+on\s+(?:table\s+)?public\.studio_chats\s+to\s+(.+)$",
            norm,
        )
        if grant_match:
            target_roles = [r.strip() for r in grant_match.group(2).split(",")]
            for role in target_roles:
                if role in {"public", "anon", "authenticated"}:
                    revoked_roles.discard(role)
            if "service_role" in target_roles:
                for priv in grant_match.group(1).split(","):
                    service_role_privileges.add(priv.strip())

    assert rls_enabled, "public.studio_chats must enable row level security in migrations."
    assert rls_forced, "public.studio_chats must force row level security in migrations."
    assert {"public", "anon", "authenticated"}.issubset(
        revoked_roles
    ), "public.studio_chats must revoke access from public, anon, and authenticated."
    assert {"select", "insert", "update", "delete"}.issubset(
        service_role_privileges
    ), "public.studio_chats must grant CRUD privileges to service_role."
    assert any(
        "unique (owner_subject, request_id)" in norm for norm in normalized_stmts
    ), "public.studio_chats must enforce UNIQUE (owner_subject, request_id)."
    assert "eq('owner_subject'" in chat_store_text, "chat-store.ts must scope queries by owner_subject."

    # Validate runtime-managed SharedSQLStateStore tables independently via AST inspection.
    discovered_runtime_tables, has_create_all = _extract_shared_sql_tables_from_ast(
        SHARED_SQL_STATE_PATH
    )
    assert has_create_all, "SharedSQLStateStore must invoke MetaData.create_all."
    assert discovered_runtime_tables, "Expected SQLAlchemy Table(...) declarations in shared_sql_state.py."

    runtime_by_table = {
        entry["table"]: entry
        for entry in matrix["runtime_managed_domains"]
        if "table" in entry
    }
    assert set(runtime_by_table.keys()) == set(
        discovered_runtime_tables.keys()
    ), "runtime_managed_domains must match every Table(...) declared in shared_sql_state.py."

    expected_owner_rel = SHARED_SQL_STATE_PATH.relative_to(REPO_ROOT).as_posix()
    for table_name, expected_cols in discovered_runtime_tables.items():
        entry = runtime_by_table[table_name]
        assert entry["owner_file"] == expected_owner_rel
        assert entry["migration_strategy"] == "runtime_create_all"
        assert (
            entry["production_applicability"]
            == "production_reachable_via_database_url_unresolved_migration"
        )
        assert entry["status"] == "runtime_create_all_unmigrated"
        assert set(entry.get("columns", [])) == expected_cols

    assert "alembic_status" in matrix
    assert matrix["alembic_status"]["state"] in {"retired", "absent"}


def test_ordered_migration_chain_replay_and_drift_detectors(tmp_path: Path) -> None:
    m1 = tmp_path / "001_init.sql"
    m2 = tmp_path / "002_alter.sql"
    m1.write_text(
        """
        create table public.studio_chats (
          id uuid primary key,
          owner_subject text not null,
          legacy_col text
        );
        create table public.extra_prod_table (
          id uuid primary key
        );
        """,
        encoding="utf-8",
    )
    m2.write_text(
        """
        alter table public.studio_chats
          add column new_col text not null,
          drop column legacy_col;
        alter table only public.studio_chats
          rename column owner_subject to owner_id;
        """,
        encoding="utf-8",
    )
    tables, _ = _reconstruct_ordered_supabase_schema([m1, m2])
    assert set(tables.keys()) == {"studio_chats", "extra_prod_table"}
    assert tables["studio_chats"] == {"id", "owner_id", "new_col"}

    ts_sample = """
    const rowSchema = z.object({
      id: z.uuid(),
      required_added_field: z.string(),
    }).refine((r) => Boolean(r));
    const columns = 'id';
    """
    assert _extract_studio_columns_from_row_schema(ts_sample) == {"id", "required_added_field"}
    assert _extract_studio_columns_from_projection(ts_sample) == {"id"}

