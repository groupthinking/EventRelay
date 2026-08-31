# API-cost PostgreSQL and worker runbook

This is the production operating contract for MYX-81 / GitHub #868. The only
deployment entrypoint is `.github/workflows/deploy-cloud-run.yml`. It deploys
the existing `uvai-backend` service mapped to `api.uvai.io`, plus the dedicated
`eventrelay-api-cost-worker` service and `eventrelay-api-cost-migrate` job.

The substrate release keeps `API_COST_DELIVERY_ENABLED=false` in both runtime
services. PR #869 must remain draft until its delivery state machine passes the
PostgreSQL and staging gates; that later change owns activation.

The smallest production-safe substrate is deliberately narrow: three canonical
tables in the existing Alembic chain, one DDL-only migration job, one stable
NOLOGIN DML group with rotating logins, one disabled dedicated worker, and the
existing API service. The rollout preserves the API's current identity and all
existing Cloud SQL attachments. It does not provision a second ORM, run DDL in
a runtime process, send webhook traffic, or replace the backend's unrelated
global `DATABASE_URL`.

## Required Google Cloud resources

Reuse a supported shared Cloud SQL for PostgreSQL instance in `us-central1` if
one already satisfies backup, capacity and isolation requirements. Otherwise
provision PostgreSQL 16 with automated backups, point-in-time recovery, deletion
protection, encrypted storage and a maintenance window. Record its full
connection name as the protected GitHub environment variable
`CLOUD_SQL_INSTANCE_CONNECTION_NAME`.

Create these PostgreSQL principals:

- `api_cost_migrator`: LOGIN role used only by the migration Cloud Run job.
- `api_cost_runtime`: stable NOLOGIN group role that receives table and sequence
  DML privileges from the idempotent grant reconciler. It must not itself be a
  member of any parent role; inherited ownership or elevated grants make the
  migration job fail closed.
- `api_cost_runtime_login`: LOGIN role inherited from `api_cost_runtime`; API and
  worker use this login. Rotate this login without changing the stable grantee.

For a new database, connect with the Cloud SQL administrative account and run
this with `psql`. The prompts keep passwords out of shell history:

```sql
\set ON_ERROR_STOP on
\prompt 'Migration-role password: ' migrator_password
\prompt 'Runtime-login password: ' runtime_password

CREATE ROLE api_cost_migrator LOGIN INHERIT
  NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION
  PASSWORD :'migrator_password';
CREATE ROLE api_cost_runtime NOLOGIN INHERIT
  NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION;
CREATE ROLE api_cost_runtime_login LOGIN INHERIT
  NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION
  PASSWORD :'runtime_password'
  IN ROLE api_cost_runtime;
CREATE DATABASE eventrelay OWNER api_cost_migrator;
\connect eventrelay
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
REVOKE ALL ON DATABASE eventrelay FROM api_cost_runtime;
GRANT CONNECT ON DATABASE eventrelay TO api_cost_runtime;
```

For an existing shared database, do not recreate it or transfer broad schema
ownership merely to rename the migrator. Use the established migration owner in
the DDL URL, create only the NOLOGIN group and rotating login above, revoke
`PUBLIC` schema creation, and run the migration/grant job. The established DDL
role must own or be authorized to alter the existing Alembic-managed objects
and create the allow-listed extensions used by revision 001. Never grant that
DDL role to either runtime identity.

The DML role must not own the database or schema and must not receive CREATE,
ALTER or DROP. It and its login must be dedicated to this subsystem: effective
access to any unrelated non-system schema, table, view or sequence is rejected
by grant reconciliation and readiness. Revoke schema creation from `PUBLIC`,
not merely from the login. The migration runner applies the precise
table/sequence grants after every `alembic upgrade head`, including when the
schema was already at head.

Create two URL secrets with distinct credentials:

```text
EVENTRELAY_DATABASE_URL_DDL=postgresql+psycopg://api_cost_migrator:${URL_ENCODED_PASSWORD}@/eventrelay?host=/cloudsql/${CLOUD_SQL_INSTANCE_CONNECTION_NAME}
EVENTRELAY_DATABASE_URL_DML=postgresql+psycopg://api_cost_runtime_login:${URL_ENCODED_PASSWORD}@/eventrelay?host=/cloudsql/${CLOUD_SQL_INSTANCE_CONNECTION_NAME}
```

The values above describe the required shape; store only the URLs in Secret
Manager. Both must use the mounted `/cloudsql/...` Unix socket. Never put either
URL in GitHub logs, source control or an unprotected repository secret.
The migration runner validates the DDL URL against the job's exact
`CLOUD_SQL_INSTANCE_CONNECTION_NAME` before Alembic can execute, and both
migration and runtime connections pin `search_path=public`; a TCP, ambiguous-
host, or wrong-instance URL fails closed.
The migration job receives the DDL URL as `DATABASE_URL`. The API and worker
receive the DML URL only as `API_COST_DATABASE_URL`; the deployment does not
replace the API's global `DATABASE_URL`, which may use a different driver and
serve unrelated backend storage.

The workflow also expects Secret Manager secrets `GEMINI_API_KEY`,
`OPENAI_API_KEY`, `YOUTUBE_API_KEY` and
`EVENTRELAY_API_KEY`. It resolves one enabled numeric version of every secret
before building, pins those versions into each revision, and records only the
version numbers in the job summary.

## Identities and least privilege

Create separate service accounts and store their emails in protected GitHub
environment variables:

| Variable | Required access |
| --- | --- |
| `MIGRATION_SERVICE_ACCOUNT` | Cloud SQL Client; accessor for DDL URL only |
| `WORKER_RUNTIME_SERVICE_ACCOUNT` | Cloud SQL Client; accessor for DML URL only |
| `API_RUNTIME_SERVICE_ACCOUNT` | Cloud SQL Client; accessor for DML URL and API provider secrets |

These three accounts must be pairwise distinct. The workflow verifies both
sides of the partition: required per-secret bindings must exist, and forbidden
cross-bindings must not. Migration must not access the DML or provider secrets;
worker must not access the DDL or provider secrets; API must not access the DDL
secret. A project-wide Secret Manager accessor grant to any of the three is
also a hard failure.

Create or select one release Artifact Registry project containing the
`eventrelay-repo` repository. Set protected variable `ARTIFACT_PROJECT_ID` to
that same project in both GitHub environments; `GCP_PROJECT_ID` remains the
environment-specific Cloud Run/Cloud SQL project. The staging deploy identity
needs Artifact Registry Writer there, the production deploy identity needs
Reader, and each runtime project's Cloud Run service agent needs Reader so it
can pull the cross-project digest. This shared registry is the promotion
boundary: staging writes the image once and production references that exact
immutable digest.

Configure GitHub Workload Identity Federation and store
`GCP_WORKLOAD_IDENTITY_PROVIDER` and `GCP_DEPLOY_SERVICE_ACCOUNT` as protected
environment secrets. The deploy identity needs Artifact Registry Writer, Cloud
Run Admin, Cloud Run Developer for jobs, Secret Manager Viewer for version
metadata and IAM-policy inspection, Project IAM-policy viewer, and Service
Account User on the three runtime identities. Do not create or store a JSON
service-account key.

`API_RUNTIME_SERVICE_ACCOUNT` is an assertion, not a replacement instruction:
set it to the service account already used by `uvai-backend`. The workflow
fails if they differ and omits the API `--service-account` flag, preserving the
existing Firestore, Cloud Tasks and Vertex AI identity. Grant Secret Manager
Accessor directly on each required secret: DDL URL only to the migration
identity, DML URL only to the worker identity, and DML plus the four provider
secrets to the existing API identity. Audit project IAM and revoke any
project-wide `roles/secretmanager.secretAccessor` binding from all three
identities; the workflow refuses to deploy while one remains. In particular,
remove any legacy binding created for `uvai-backend-sa` by the retired setup
script.

Also set protected variables `API_COST_RUNTIME_DB_ROLE=api_cost_runtime`,
`ARTIFACT_PROJECT_ID` to the common release-registry project, and
`CLOUD_SQL_INSTANCE_CONNECTION_NAME` to the exact environment-specific Cloud
SQL connection name.
Both `staging` and `production` GitHub environments must require reviewers;
production must restrict deployment branches to `main`. Disable administrator
reviewer bypass. Restrict the Workload Identity Provider attribute condition to
this repository, this workflow, the selected protected environment, and the
permitted ref (`main` for production).

Before the first substrate run, reconcile `uvai-backend` into one unambiguous
baseline revision: exactly one explicitly named revision serves 100 percent,
that revision is both latest-created and latest-ready, and no traffic entry has
a tag. The serving revision must not mount `API_COST_WEBHOOK_URL`. If any of
these are false, use a separately reviewed one-time cleanup deployment and
remove stale tags/secrets before retrying; do not weaken the workflow gate.
This prevents an older tagged or webhook-capable revision from remaining
directly reachable during the substrate rollout.

## Release order

1. Merge only after all three `PostgreSQL migration matrix` checks (`fresh`,
   `from-002`, and `round-trip`) succeed for the exact commit. The fresh check
   also runs the focused unit/readiness/deployment gates and builds and imports
   the production container.
2. In Actions, select **Deploy Cloud Run PostgreSQL substrate** and its exact
   commit ref. Enter the same full 40-character SHA in `commit_sha`.
3. Choose `staging`. The workflow verifies the checked-out SHA and check runs,
   authenticates through WIF, requires three distinct service accounts,
   inventories the exact 100-percent serving API revision and Cloud SQL
   attachments, and fails on stale traffic tags, a mounted legacy webhook,
   broad secret IAM, or any cross-secret binding. Before any mutation, it also
   re-verifies that revision still serves 100 percent and proves its
   backward-compatible `/api/v1/health` endpoint is healthy as the rollback
   target.
4. It resolves numeric secret versions, then builds and pushes one immutable
   SHA image and uploads a SHA-scoped manifest containing its exact digest.
5. It deploys a one-task, one-parallelism migration job and waits for it. In
   staging it executes the job a second time to prove idempotent migration and
   grant reconciliation. Failure stops the rollout before either runtime.
6. It deploys the dedicated worker with service-level min/max 1, concurrency 1,
   CPU always allocated and delivery forcibly disabled, then verifies the
   revision uses the same image digest. Cloud Run may briefly overlap revisions
   during replacement, so these scaling limits are not a database claim lock;
   delivery stays disabled until #869 proves overlap-safe fencing.
7. It adds (rather than replaces) the API-cost Cloud SQL attachment, removes any
   stale webhook environment/secret binding, deploys the API candidate with no
   traffic, and verifies preserved attachments, identity, digest and `/readyz`.
8. It removes the temporary candidate tag before promotion, promotes the exact
   revision to 100 percent, and smokes the service URL. Production additionally
   smokes `https://api.uvai.io`. Any promotion or post-promotion smoke failure
   automatically restores the preflight revision; the database is not
   downgraded.
9. Repeat the same SHA for `production`. The workflow requires the **latest**
   GitHub `staging` deployment for that SHA to be successful, downloads the
   manifest from that exact Actions run, verifies that run's repository,
   workflow path, trigger, conclusion and head SHA, verifies the digest still
   exists in Artifact Registry, and deploys it without rebuilding. It also
   refuses a commit that is not the current `origin/main` head.

The legacy `infrastructure/cloudrun/deploy.sh`, `setup.sh`, `cloudbuild.yaml`,
`service.yaml`, and `scripts/deployment/deploy-cloud-run.sh` files are
intentional fail-closed tombstones. Do not restore or bypass them.

## Acceptance evidence

Retain these artifacts with the issue:

- passing fresh upgrade, revision-002-to-head, downgrade/re-upgrade, already-at-
  head and grant-reconciliation runs against PostgreSQL 16;
- runtime-role INSERT/SELECT/UPDATE/sequence success and DDL/`alembic_version`
  denial;
- API `/readyz` and worker `/readyz` success using the DML login;
- readiness rejection for a wrong runtime group, elevated or nested group,
  database/schema CREATE, unrelated shared-database relation access, malformed
  column type/nullability/default signatures, primary/unique/check definitions,
  and missing or invalid worker indexes;
- one pending row written by a subprocess, followed by writer exit and a read
  from a distinct subprocess using a rotated login;
- worker restart/revision replacement with the pending row preserved;
- a staging worker redeploy with a pending row demonstrably preserved before
  and after revision replacement;
- deployment summary showing the exact SHA/digest, prior and promoted API
  revisions, migration execution IDs, worker revision/configuration and every
  pinned secret version;
- Cloud Run configuration showing service-level worker min 1/max 1,
  concurrency 1, CPU not throttled and `API_COST_DELIVERY_ENABLED=false`;
- production custom-domain response from the promoted `uvai-backend` revision.
- staging artifact evidence showing that production consumed the digest from
  the latest successful staging run without a second image build.

The protected staging workflow runs migration/grant reconciliation twice. A
second successful execution is required evidence of idempotence, not optional
cleanup. Its live tests intentionally mutate and restore schema/grants and only
run when `API_COST_TEST_DISPOSABLE_DATABASE=true`; never set that sentinel for
a persistent environment. The staging worker-redeploy pending-row check remains
required before the substrate PR can leave draft if it is not automated by the
workflow.

## Health and incident response

- API `/health` is process liveness; `/readyz` validates API-cost schema,
  required primary/unique/check constraints and worker indexes, plus effective
  DML privileges. Cloud Run removes a revision from traffic when readiness
  fails.
- Worker `/healthz` expires when its polling loop stops making progress.
  `/readyz` additionally requires a recent successful database check.
- Alert on migration job failure, worker readiness failure, worker restart
  loops, exhausted outbox rows and the age of the oldest due row.

Delivery is disabled in this substrate, so pending rows may accumulate but must
never be sent. MYX-81 does not require or mount a webhook secret.

## Local SQLite compatibility

SQLite remains a local/test compatibility path only. Constructing
`APICostMonitor()` without a database URL or explicit path no longer creates a
database implicitly. Local callers must pass `db_path=...` or set
`API_COST_MONITOR_DB_PATH`; the module self-test explicitly uses
`$RUNTIME_DIR/api_cost_monitoring.db` (defaulting to `/tmp`). Production rejects
SQLite and rejects PostgreSQL TCP URLs when the Cloud SQL Unix socket contract
is required.

The old SQLite outbox layout cannot safely represent claim fencing or due-time
state. Before using an existing local file, stop local writers and make a byte-
for-byte backup, for example:

```bash
cp "$RUNTIME_DIR/api_cost_monitoring.db" \
  "$RUNTIME_DIR/api_cost_monitoring.db.pre-postgres-substrate"
```

Then recreate the disposable local database through an explicit monitor path.
Opening a legacy outbox fails with a backup-and-recreate instruction instead of
silently mutating it. There is no supported SQLite-to-production migration.

## Criteria for PR #869 to leave draft

PR #869 remains draft and both deployed runtimes keep
`API_COST_DELIVERY_ENABLED=false` until all of these are true:

- PostgreSQL claims are atomic and due-aware, using a conditional
  `UPDATE ... RETURNING` or `FOR UPDATE SKIP LOCKED`; two overlapping workers
  cannot own the same event.
- Every claim has a unique token. Completion, failure and stale-claim recovery
  fence on both row ID and token, so an expired worker cannot overwrite a newer
  claim.
- `next_attempt_at` is honored, retry delay is bounded exponential backoff, and
  exhausted rows reach an observable terminal state without hot-looping.
- Batch size, per-webhook timeout and the outer operation timeout are mutually
  consistent. SIGTERM stops new claims, awaits or safely cancels bounded
  in-flight work, and leaves recoverable state.
- The ambiguous case “webhook accepted, completion commit lost” has a reviewed
  duplicate-delivery contract, such as a stable event/idempotency key accepted
  by the receiver; “at most once” is not claimed without proof.
- Live PostgreSQL tests cover concurrent and overlapping worker revisions,
  stale-token completion, cancellation, process crash at each state boundary,
  slow/time-out webhooks, backoff ordering, exhausted rows, and load greater
  than one batch. A staging revision replacement repeats these tests with the
  real Cloud Run settings.
- The final model and migration remain additive and compatible with revision
  003, all required exact-SHA checks pass, review threads are resolved, and
  staging evidence is attached to MYX-81/#868.
- Only then does a separate reviewed activation change create/pin
  `API_COST_WEBHOOK_URL` and flip the delivery flag. A rollback drill must show
  the flag can be frozen before traffic or worker revision rollback.

## Rollback and recovery

Do not downgrade the additive database migration during an application
rollback. It would destroy the compatibility boundary and risks pending data.

The protected workflow records the prior 100-percent revision before creating
the candidate. It removes the temporary candidate tag before promotion and
automatically restores that revision if promotion or a subsequent service or
domain smoke fails. A failed pre-promotion candidate never changes traffic; a
failure cleanup removes its tag so it cannot remain directly addressable.
Rollback validates the backward-compatible `/api/v1/health` route because the
first pre-substrate revision does not yet expose `/readyz`.

If delivery has been enabled by a later release, first freeze it without
scaling the worker to zero:

```bash
gcloud run services update eventrelay-api-cost-worker \
  --region us-central1 \
  --update-env-vars API_COST_DELIVERY_ENABLED=false
```

Then use the protected workflow to redeploy the last known-good main SHA. If
automatic rollback itself cannot complete, use this API-only contingency to
derive and promote the immediately preceding ready revision while retaining the
current database schema:

```bash
PREVIOUS_REVISION="$(gcloud run revisions list \
  --service uvai-backend --region us-central1 \
  --filter='status.conditions.type=Ready AND status.conditions.status=True' \
  --sort-by='~metadata.creationTimestamp' \
  --limit=2 --format='value(metadata.name)' | tail -n 1)"
test -n "${PREVIOUS_REVISION}"
gcloud run services update-traffic uvai-backend \
  --region us-central1 \
  --to-revisions="${PREVIOUS_REVISION}=100"
curl --fail --silent --show-error https://api.uvai.io/api/v1/health
```

Preserve the failed revision, migration execution ID, pinned secret versions and
Cloud SQL logs for incident review. For a substrate revision, restore traffic
only after `/readyz` and a cross-process pending-row read succeed; for a legacy
revision use `/api/v1/health` and retain the database evidence separately.

## Credential rotation

Create a new runtime LOGIN role, grant it membership in the stable
`api_cost_runtime` role, add a numeric version to
`EVENTRELAY_DATABASE_URL_DML`, and run the protected deployment. The migration
job reasserts grants to the stable role on every release. Disable the old login
only after the API and worker revisions using its secret version have drained.
