# SQL model and migration truth (AUDIT-007 / #2169)

## Current state — 2026-11-09

Machine-readable inventory: [`docs/schema_inventory.json`](schema_inventory.json). It is
guarded by `tests/unit/test_schema_inventory.py`, which fails if a listed source or
migration file is missing, if the shared-state migration drifts from the SQLAlchemy
models (columns, types, nullability, primary keys, indexes, foreign keys), or if a
migrated table stops forcing row-level security.

Migrations live in `apps/web/supabase/migrations/` and are named
`<UTC yyyymmddhhmmss>_<snake_case_description>.sql`.

| Table | Model / owner | Migration | RLS | Access |
| --- | --- | --- | --- | --- |
| `studio_chats` | `apps/web/src/lib/studio/chat-store.ts` | `20260912214530_create_private_studio_chat_ownership.sql` | enabled + forced | `service_role` only |
| `shared_sessions` | `src/youtube_extension/services/shared_sql_state.py` | `20261109062000_create_service_role_shared_state_tables.sql` | enabled + forced | `service_role` only |
| `shared_timeline_events` | same | same | enabled + forced | `service_role` only |
| `shared_a2a_messages` | same | same | enabled + forced | `service_role` only |

### Schema ownership for the shared-state tables

- **PostgreSQL / Supabase:** the migration is the only schema source.
  `SharedSQLStateStore` no longer runs `metadata.create_all()` there; it inspects the
  database and raises `SharedStateSchemaError` (naming the migration) if a table or
  column is missing, or PostgreSQL tables lack forced RLS, deny-all client ACLs,
  required service-role grants or their secured serial sequences. Existing tables
  from `create_all()` therefore cannot pass by having the right columns alone.
  `AgentOrchestrator` already catches this and falls back to its
  in-memory A2A log with a warning; `scripts/maintenance/session_orchestration_manager.py`
  fails loudly.
- **SQLite (local default, tests):** `create_all()` still creates the tables, so local
  runs need no setup.
- The migration is idempotent (`create table if not exists`, `create index if not
  exists`), so it can be applied to a database where an older build already created
  these tables with `create_all()`. That path was checked against PostgreSQL 17: the
  resulting schema is identical to a fresh apply.

### Tenancy and RLS strategy

Tables written only by trusted server code are service-role only: RLS enabled and
forced, no policies, all privileges revoked from `public`, `anon` and `authenticated`,
and `select, insert, update, delete` granted to `service_role` (sequences: `usage,
select`). The connecting role must be `service_role` or another role with `BYPASSRLS`
(on Supabase, `postgres` has it). A role without `BYPASSRLS` — including a table owner,
because RLS is forced — reads zero rows and cannot write.

## Not yet reconciled

- `supabase/supabase_setup.sql` (projects, chats, files, media, mcp_logs, nods_page,
  nods_page_section): a Docker init script, not a migration; RLS enabled but not forced,
  with owner/authenticated policies. Needs its own migrate-or-retire decision.
- `infrastructure/database/query_optimization.sql` (video_processing_results,
  api_usage_optimized, performance_metrics_optimized): unmanaged script, no application
  model, no migration. `index_analysis.py` inspects video_processing_results and
  performance_metrics_optimized.
- `supabase/setup_mcp_db.js` attempts to create `mcp_contexts`; bootstrap script,
  no checked-in migration or RLS.
- `src/integration/supabase_db.py` `generate_schema_sql()` emits template tables
  (profiles, subscriptions) for generated apps; out of scope for EventRelay's own schema.
- The Supabase CLI config is `supabase/config.toml` (project `nsfrhirwsjqwhagtuaxx`),
  while migrations are in `apps/web/supabase/migrations/`. Applying them is a manual
  step until the two are aligned.

## Deployment

Applying migrations to the live Supabase project is a human step; nothing in this
repository applies them automatically. Before applying
`20261109062000_create_service_role_shared_state_tables.sql`, check whether any
deployed service's `DATABASE_URL` / `EVENTRELAY_SHARED_STATE_DATABASE_URL` already
created these tables via `create_all()` — if so they currently have no RLS and default
grants, and the migration will lock them down in place.

### Plain PostgreSQL prerequisites

Supabase supplies `anon`, `authenticated`, and `service_role`. A plain PostgreSQL
administrator must provision these roles **before applying the migration**. Run the
following only for roles confirmed absent (existing roles must be inspected, not replaced):

```sql
CREATE ROLE anon NOLOGIN;
CREATE ROLE authenticated NOLOGIN;
CREATE ROLE service_role NOLOGIN BYPASSRLS;
GRANT USAGE ON SCHEMA public TO service_role;
```

Then apply the checked-in migration as the database owner or administrator. Connect
the server with a dedicated login role that has `BYPASSRLS` and inherits the
`service_role` object grants, or use an appropriately configured `service_role`
login. `BYPASSRLS` itself is not inherited through role membership. Provision login
authentication through the database's secret-management process; never commit it.
Client-facing roles must have neither `BYPASSRLS` nor membership in privileged
server roles. No application start-up path creates roles or applies migrations.

## History

The October 2026 version of this file noted that the backend model modules and the three
Alembic revisions (`001`–`003`) named in the original audit, and
`tests/unit/test_migration_truth.py`, are absent from the tree. That remains true; the
legacy Alembic chain is treated as retired, not restored.

## Disposable PostgreSQL acceptance

`scripts/testing/verify_shared_state_postgres.py` starts its own temporary PostgreSQL
cluster (optional `pgserver` and `psycopg` packages), refuses IP listeners, and tests
legacy tables, effective client privileges, role attributes, sequence access,
server-role writes, fresh-store readback and a hostile `search_path`. Run from the
repository root with `PYTHONPATH=src python scripts/testing/verify_shared_state_postgres.py`.
It never reads deployment database environment variables.

The November 12, 2026 attempt was blocked before server startup by
`PermissionError: [Errno 1] Operation not permitted` when creating the private
Unix socket. These PostgreSQL acceptance cases are **NOT RUN**; the passing unit
suite uses SQLite and mocked PostgreSQL catalogs. SQL parsing is a syntax check,
not PostgreSQL runtime acceptance. Keep migration/production acceptance on hold
until this script and the opt-in real-PostgreSQL test pass on an allowed runner.
