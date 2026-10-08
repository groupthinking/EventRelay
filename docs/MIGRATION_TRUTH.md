# SQL model and migration truth (AUDIT-007 / #2169)

## Current repository evidence — 2026-10-08

The previous inventory in this file named backend model modules and three Alembic revisions. That inventory is obsolete: the current recursive repository tree does not contain `src/youtube_extension/backend/models/`, `src/youtube_extension/backend/migrations/`, or `tests/unit/test_migration_truth.py`. `alembic.ini` still points to the missing migration directory. Do not treat the old count guard or directory list as verified current coverage.

One SQL migration is present at `apps/web/supabase/migrations/20260912214530_create_private_studio_chat_ownership.sql`. Its presence alone does not prove that all live tables, tenant policies, deployed revisions, or Python persistence models are reconciled.

## Acceptance and blocking requirements

Issue #2169 remains open. Before creating migrations, identify the actual active database and owning service, inventory current persistence models and deployed revision/RLS state using approved read-only access, and map each model to its authoritative migration history. The missing legacy directory needs an explicit retirement or restoration decision; do not silently manufacture a replacement migration chain.

No live schema comparison, database access, migration generation, or migration application was performed in this correction. A destructive migration requires separate approval. New tables/columns must accompany the matching migration and fixture validation in the same PR.

Historical claim retained for audit: the previous file asserted three committed revisions (`001`–`003`) and a `test_migration_truth.py` guard. That claim is not valid for the inspected current tree.
