# Backend deployment

The only supported backend deployment path is the protected GitHub Actions
workflow `.github/workflows/deploy-cloud-run.yml`.

It deploys the canonical `uvai-backend` service behind `api.uvai.io`, the
dedicated `eventrelay-api-cost-worker`, and the migration/grant job using one
immutable SHA image. Staging builds it once; production consumes that exact
tested digest without rebuilding. PostgreSQL migrations complete before either
runtime is changed. Workload Identity Federation, three distinct runtime/job
identities, distinct DDL/DML credentials, numeric Secret Manager versions,
database-aware readiness, candidate smoke testing and explicit traffic
promotion are mandatory.

The PostgreSQL DML credential is scoped to the API-cost subsystem as
`API_COST_DATABASE_URL`. The workflow intentionally leaves the backend's global
`DATABASE_URL` unchanged so unrelated async database consumers keep their own
driver contract.

Direct Cloud Build, shell-script and service-manifest entrypoints are retired
because they bypass those gates and intentionally fail closed.

Provisioning, exact release order, evidence, credential rotation and rollback
are documented in
[`docs/deployment/API_COST_POSTGRESQL_RUNBOOK.md`](docs/deployment/API_COST_POSTGRESQL_RUNBOOK.md).
