# SQL model and migration truth (AUDIT-007 / #2169)

## Current repository evidence — 2026-11-16

The legacy Alembic inventory from earlier audit notes is not the active schema source in this tree. Current SQL ownership is split into:

- Supabase SQL migration(s) for production `apps/web` tables.
- Runtime SQLAlchemy `create_all` tables for internal shared orchestration state.

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
  "non_production_domains": [
    {
      "service": "internal runtime shared SQL state",
      "table": "shared_sessions",
      "owner_file": "src/youtube_extension/services/shared_sql_state.py",
      "migration_strategy": "runtime_create_all",
      "status": "allowed_non_migrated"
    },
    {
      "service": "internal runtime shared SQL state",
      "table": "shared_timeline_events",
      "owner_file": "src/youtube_extension/services/shared_sql_state.py",
      "migration_strategy": "runtime_create_all",
      "status": "allowed_non_migrated"
    },
    {
      "service": "internal runtime shared SQL state",
      "table": "shared_a2a_messages",
      "owner_file": "src/youtube_extension/services/shared_sql_state.py",
      "migration_strategy": "runtime_create_all",
      "status": "allowed_non_migrated"
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

`studio_chats` uses explicit SQL-side hardening in the migration file:

- `ALTER TABLE ... ENABLE ROW LEVEL SECURITY`
- `ALTER TABLE ... FORCE ROW LEVEL SECURITY`
- `REVOKE ALL ... FROM public, anon, authenticated`
- `GRANT ... TO service_role`

Tenant boundary is application-owned `owner_subject` filtering plus uniqueness on `(owner_subject, request_id)`. All read/write paths in `apps/web/src/lib/studio/chat-store.ts` scope queries by `owner_subject`.

## Drift guard

`tests/unit/test_migration_truth_matrix.py` is the schema-drift guard for this issue. It fails when any of the following occurs:

- `MIGRATION_TRUTH.md` lacks the required matrix block.
- `studio_chats` is not mapped to a migration file.
- `studio_chats` column set drifts between migration SQL, app model contract, and documented mapping.
- Shared runtime SQL tables are not explicitly classified as non-production runtime `create_all`.

Historical claim retained for audit: a previous file revision asserted three committed revisions (`001`–`003`) and a `test_migration_truth.py` count guard. That claim is not valid for the inspected current tree.
