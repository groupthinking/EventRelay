# Cloud Run deployment

EventRelay backend releases run only through
`.github/workflows/deploy-cloud-run.yml` from protected `staging` and
`production` environments. The workflow targets `uvai-backend`, matching the
`api.uvai.io` domain mapping.

The release is fail-closed: it verifies the exact SHA and PostgreSQL check,
authenticates through Workload Identity Federation, pins numeric secret
versions, builds one immutable image in staging, reuses that exact digest in
production, runs migrations and privilege reconciliation, deploys the disabled
dedicated worker, validates an API candidate, removes its temporary tag,
explicitly promotes traffic, and restores the previous serving revision if
post-promotion smoke checks fail. The API candidate preserves the existing
service account and appends its Cloud SQL attachment instead of replacing
existing database connections.

Only the migration job receives the PostgreSQL DDL secret as `DATABASE_URL`.
The API and worker receive their DML secret as `API_COST_DATABASE_URL`, avoiding
any collision with the backend's separate asynchronous database configuration.

Do not use direct `gcloud run deploy`, Cloud Build, a local deploy script, or a
checked-in service manifest. Those paths cannot prove migration ordering,
credential separation, immutable secrets, readiness or rollback evidence.

See [API_COST_POSTGRESQL_RUNBOOK.md](./API_COST_POSTGRESQL_RUNBOOK.md) for
provisioning, release, acceptance evidence and incident recovery.
