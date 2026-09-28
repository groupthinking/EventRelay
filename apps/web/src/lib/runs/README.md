# Durable specification approval storage

This internal service stores run state, versioned specification approvals, and
ordered events in Postgres. Every operation checks tenant membership. Writes
require an owner or author, and use revision comparisons inside transactions.
Scope changes invalidate the current approval while retaining its history.

`getRunStore()` requires `RUN_DATABASE_URL`; it has no filesystem fallback.
Use a dedicated Neon development branch and set `RUN_DATABASE_URL_UNPOOLED`
for `npm --workspace=apps/web run db:runs:migrate`. Migrations are explicit;
request handling never changes the schema. Never expose either URL to clients.

The caller must derive `userId` from authenticated server identity. Provision
`uvai_run_members` only through a trusted administrative path. Request JSON must
never grant membership or set the authenticated user. Tenant isolation currently
uses service-level checks; database RLS remains an integration prerequisite.

Verification: from apps/web, run
`../../node_modules/.bin/vitest run src/lib/runs/store.test.ts`.
These tests apply the generated SQL to real embedded Postgres (PGlite), including
a file-backed restart, stale approvals, tenant checks, and transaction rollback.
They do not verify hosted Neon, multi-connection contention, or deployment.

Remaining integration steps:

- Provision the development database and restricted runtime role; add RLS.
- Connect authenticated Studio routes and trusted membership provisioning.
- Bind approval to durable workflow pause/resume and idempotent job dispatch.
- Add isolated build execution, durable artifact storage, and delivery evidence.
- Verify a real approved run through repository commit, tests, READY deployment,
  and live smoke checks before calling the product delivered.

`beginPlanning` changes database state only; it does not launch an agent.
No public API or Studio UI is wired to this module yet. Existing G.A.T.E. and
Upstash Video Pack storage remain independent and authoritative for their roles.
