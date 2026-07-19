# Cloud Run release entrypoint

Direct Cloud Run deployment is retired. EventRelay backend releases run only
through the protected `.github/workflows/deploy-cloud-run.yml` workflow, which
pins an exact tested commit and secret versions, migrates shared PostgreSQL,
deploys the disabled worker, verifies a no-traffic API candidate, and rolls
traffic back automatically if the promoted revision fails its smoke tests.

Before the first release, complete the database, service-account, Secret
Manager, Workload Identity Federation, and protected-environment prerequisites
in [the API-cost PostgreSQL runbook](deployment/API_COST_POSTGRESQL_RUNBOOK.md).

For a release:

1. Confirm all three `PostgreSQL migration matrix` checks succeeded for the
   exact commit.
2. Run **Deploy Cloud Run PostgreSQL substrate** against `staging` and supply
   the same full 40-character commit SHA.
3. Retain the workflow evidence and smoke results.
4. Run the same SHA against `production`; the workflow requires the latest
   staging deployment to have succeeded, reuses that run's exact image digest
   without rebuilding, and requires the current `main` head.

Do not restore `infrastructure/cloudrun/setup.sh`,
`infrastructure/cloudrun/deploy.sh`, or
`scripts/deployment/deploy-cloud-run.sh`. They are fail-closed tombstones.
