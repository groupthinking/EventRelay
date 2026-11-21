# SQL model and migration truth (AUDIT-007 / #2169)

## Current repository evidence

The legacy Alembic inventory from earlier audit notes is not the active schema source in this tree. Current SQL ownership is split into:

- Supabase SQL migrations under `apps/web/supabase/migrations/` for `apps/web` tables.
- Runtime SQLAlchemy `MetaData.create_all` tables declared in `src/youtube_extension/services/shared_sql_state.py`, which `AgentOrchestrator` initializes when `DATABASE_URL` or `EVENTRELAY_SHARED_STATE_DATABASE_URL` is configured (including production Terraform environments supplying `DATABASE_URL`).

There is no `alembic.ini` file in the current repository root, and there is no `src/youtube_extension/backend/migrations/` directory in this tree.

## Active model to migration matrix

<!-- MIGRATION_TRUTH_MATRIX_START -->
```json
{
  "production_domains": [
    {
      "service": "apps/web studio ownership",
      "table": "studio_chats",
      "model_contract_file": "apps/web/src/lib/studio/chat-store.ts",
      "migration_file": "apps/web/supabase/migrations/20260912214530_create_private_studio_chat_ownership.sql",
      "columns": [
        "id",
        "owner_subject",
        "request_id",
        "request_hash",
        "v0_chat_id",
        "title",
        "pack_source_hash",
        "creation_state",
        "created_at",
        "updated_at"
      ],
      "rls": "enabled+forced",
      "tenant_boundary": "owner_subject + service_role access",
      "status": "reconciled"
    }
  ],
  "runtime_managed_domains": [
    {
      "service": "internal runtime shared SQL state",
      "table": "shared_sessions",
      "owner_file": "src/youtube_extension/services/shared_sql_state.py",
      "columns": [
        "session_id",
        "payload",
        "version",
        "created_at",
        "updated_at"
      ],
      "migration_strategy": "runtime_create_all",
      "production_applicability": "production_reachable_via_database_url_unresolved_migration",
      "status": "runtime_create_all_unmigrated"
    },
    {
      "service": "internal runtime shared SQL state",
      "table": "shared_timeline_events",
      "owner_file": "src/youtube_extension/services/shared_sql_state.py",
      "columns": [
        "id",
        "session_id",
        "timestamp",
        "summary",
        "content"
      ],
      "migration_strategy": "runtime_create_all",
      "production_applicability": "production_reachable_via_database_url_unresolved_migration",
      "status": "runtime_create_all_unmigrated"
    },
    {
      "service": "internal runtime shared SQL state",
      "table": "shared_a2a_messages",
      "owner_file": "src/youtube_extension/services/shared_sql_state.py",
      "columns": [
        "id",
        "sender",
        "recipient",
        "conversation_id",
        "timestamp",
        "content"
      ],
      "migration_strategy": "runtime_create_all",
      "production_applicability": "production_reachable_via_database_url_unresolved_migration",
      "status": "runtime_create_all_unmigrated"
    }
  ],
  "alembic_status": {
    "state": "absent",
    "note": "No alembic.ini or active alembic version directory exists in this tree."
  }
}
```
<!-- MIGRATION_TRUTH_MATRIX_END -->

## RLS and tenant strategy

`studio_chats` uses explicit SQL-side hardening in the migration chain:

- `ALTER TABLE ... ENABLE ROW LEVEL SECURITY`
- `ALTER TABLE ... FORCE ROW LEVEL SECURITY`
- `REVOKE ALL ... FROM public, anon, authenticated`
- `GRANT SELECT, INSERT, UPDATE, DELETE ... TO service_role`

Tenant boundary is application-owned `owner_subject` filtering plus uniqueness on `(owner_subject, request_id)`. All read/write paths in `apps/web/src/lib/studio/chat-store.ts` scope queries by `owner_subject`.

## Production applicability of `SharedSQLStateStore`

`infrastructure/terraform/environments/production/main.tf` injects `DATABASE_URL` without an environment exclusion on `AgentOrchestrator`, so `shared_sessions`, `shared_timeline_events`, and `shared_a2a_messages` are production-reachable runtime `create_all` tables rather than strictly non-production tables. Until either versioned SQL migrations or an explicit non-production boundary is implemented, these tables remain tracked under `runtime_managed_domains` with status `runtime_create_all_unmigrated`.

## Drift guard

`tests/unit/test_migration_truth_matrix.py` enforces parity across code, ordered migrations, and this matrix:

- Discovers all production `CREATE TABLE` / `ALTER TABLE` statements across ordered `apps/web/supabase/migrations/*.sql` files independently of the matrix.
- Verifies `studio_chats` parity across the ordered migration chain, `rowSchema` in `chat-store.ts`, SELECT `columns` projection, and `MIGRATION_TRUTH.md`.
- Validates live SQL-level RLS (`ENABLE` + `FORCE`), `REVOKE ALL` from `public`/`anon`/`authenticated`, `GRANT SELECT, INSERT, UPDATE, DELETE` to `service_role`, `(owner_subject, request_id)` uniqueness, and `owner_subject` filtering.
- Parses `src/youtube_extension/services/shared_sql_state.py` via AST to verify every `Table(...)`, column list, and `.create_all(...)` invocation matches `runtime_managed_domains` accurately.
