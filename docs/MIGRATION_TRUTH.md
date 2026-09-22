# SQL model vs migration truth (AUDIT-007 / #2169)

## Current state

| Area | Location | Notes |
| --- | --- | --- |
| Model mixins | `src/youtube_extension/backend/models/base.py` | Timestamps, tenant, UUID, soft-delete |
| Model modules | `src/youtube_extension/backend/models/*.py` | Multiple domain modules |
| Alembic revisions | `src/youtube_extension/backend/migrations/versions/` | **3** committed revisions (`001`–`003`) |

## Policy

1. Any model used in production request paths must have a matching migration revision or an explicit “non-prod / optional store” doc entry here.
2. New tables/columns require Alembic revision in the same PR as model changes.
3. CI guard: `tests/unit/test_migration_truth.py` fails if revision count drops or model package disappears.

## Follow-up (tracked)

Generate incremental migrations for unmigrated model domains after inventory sign-off. Do not auto-generate destructive migrations in CI.
