-- Delivery pipeline schema.
--
-- Idempotent: safe to re-run. Every statement guards on existence so this can
-- be applied to a database that is already partially migrated.
--
-- The CHECK constraints at the bottom are the point of this file. They encode
-- "delivered means proven" in the database itself, so no application bug,
-- rewrite, or manual UPDATE can record a delivery that never happened.

-- ── Enums ──

DO $$ BEGIN
  CREATE TYPE run_status AS ENUM (
    'sourcing', 'requirements', 'planning', 'awaiting_approval',
    'building', 'verifying', 'deploying',
    'delivered', 'blocked', 'failed', 'cancelled'
  );
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE gate_kind AS ENUM (
    'source_evidence', 'requirements_complete', 'plan_executable',
    'human_approved', 'build_succeeded', 'tests_passed', 'deployment_live'
  );
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE gate_result AS ENUM ('pass', 'fail', 'skipped');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE artifact_kind AS ENUM (
    'repository', 'deployment', 'test_report', 'build_log', 'transcript'
  );
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- ── Tables ──

CREATE TABLE IF NOT EXISTS delivery_runs (
  id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id          text NOT NULL,
  title            text NOT NULL,
  status           run_status NOT NULL DEFAULT 'sourcing',
  source_kind      text NOT NULL,
  source_url       text,
  workflow_run_id  text,
  repo_url         text,
  tests_passed_at  timestamptz,
  deployment_url   text,
  delivered_at     timestamptz,
  blocked_reason   text,
  created_at       timestamptz NOT NULL DEFAULT now(),
  updated_at       timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS delivery_runs_user_created_idx
  ON delivery_runs (user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS delivery_runs_status_idx ON delivery_runs (status);

CREATE TABLE IF NOT EXISTS run_specs (
  id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  run_id       uuid NOT NULL REFERENCES delivery_runs (id) ON DELETE CASCADE,
  version      integer NOT NULL DEFAULT 1,
  requirements jsonb NOT NULL,
  plan         jsonb NOT NULL,
  created_at   timestamptz NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS run_specs_run_version_idx
  ON run_specs (run_id, version);

CREATE TABLE IF NOT EXISTS run_steps (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  run_id      uuid NOT NULL REFERENCES delivery_runs (id) ON DELETE CASCADE,
  seq         integer NOT NULL,
  phase       run_status NOT NULL,
  name        text NOT NULL,
  status      text NOT NULL DEFAULT 'running',
  detail      jsonb,
  started_at  timestamptz NOT NULL DEFAULT now(),
  finished_at timestamptz
);

-- Doubles as the idempotency guard for retried durable steps.
CREATE UNIQUE INDEX IF NOT EXISTS run_steps_run_seq_idx ON run_steps (run_id, seq);

CREATE TABLE IF NOT EXISTS run_gates (
  id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  run_id       uuid NOT NULL REFERENCES delivery_runs (id) ON DELETE CASCADE,
  kind         gate_kind NOT NULL,
  result       gate_result NOT NULL,
  evidence     jsonb NOT NULL,
  evaluated_at timestamptz NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS run_gates_run_kind_idx ON run_gates (run_id, kind);

CREATE TABLE IF NOT EXISTS run_artifacts (
  id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  run_id     uuid NOT NULL REFERENCES delivery_runs (id) ON DELETE CASCADE,
  kind       artifact_kind NOT NULL,
  uri        text NOT NULL,
  meta       jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS run_artifacts_run_idx ON run_artifacts (run_id);

CREATE TABLE IF NOT EXISTS run_approvals (
  id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  run_id     uuid NOT NULL REFERENCES delivery_runs (id) ON DELETE CASCADE,
  spec_id    uuid NOT NULL REFERENCES run_specs (id) ON DELETE CASCADE,
  decision   text NOT NULL,
  decided_by text NOT NULL,
  note       text,
  decided_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS run_approvals_run_idx ON run_approvals (run_id);

-- ── Preventative constraints ──
--
-- Added with a guarded DO block rather than plain ALTER so re-running is safe.

-- A run may only be 'delivered' with all three pieces of delivery evidence
-- present. This is the structural answer to "the system reported success it
-- could not prove": there is no code path, including a manual UPDATE, that can
-- store a delivered run without a repository, a passing test run, and a live
-- deployment URL.
DO $$ BEGIN
  ALTER TABLE delivery_runs ADD CONSTRAINT delivery_runs_delivered_requires_evidence
    CHECK (
      status <> 'delivered'
      OR (
        repo_url IS NOT NULL
        AND tests_passed_at IS NOT NULL
        AND deployment_url IS NOT NULL
        AND delivered_at IS NOT NULL
      )
    );
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- 'blocked' must always say which gate refused. A blocked run with no reason is
-- indistinguishable from a crash, which defeats the purpose of separating the
-- two states.
DO $$ BEGIN
  ALTER TABLE delivery_runs ADD CONSTRAINT delivery_runs_blocked_requires_reason
    CHECK (status <> 'blocked' OR blocked_reason IS NOT NULL);
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- A deployment URL must be a real https origin. Guards against storing a
-- placeholder like 'pending' or 'localhost' and treating it as a live delivery.
DO $$ BEGIN
  ALTER TABLE delivery_runs ADD CONSTRAINT delivery_runs_deployment_url_is_https
    CHECK (deployment_url IS NULL OR deployment_url ~ '^https://[^/]+');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- A video run needs a source URL; an idea run must not carry one.
DO $$ BEGIN
  ALTER TABLE delivery_runs ADD CONSTRAINT delivery_runs_source_shape
    CHECK (
      (source_kind = 'video' AND source_url IS NOT NULL)
      OR (source_kind = 'idea' AND source_url IS NULL)
    );
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- A passing gate must carry non-empty evidence. A pass with `{}` is the same
-- unfalsifiable claim this schema exists to prevent.
DO $$ BEGIN
  ALTER TABLE run_gates ADD CONSTRAINT run_gates_pass_requires_evidence
    CHECK (result <> 'pass' OR (evidence IS NOT NULL AND evidence <> '{}'::jsonb));
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  ALTER TABLE run_approvals ADD CONSTRAINT run_approvals_decision_valid
    CHECK (decision IN ('approved', 'rejected', 'changes_requested'));
EXCEPTION WHEN duplicate_object THEN NULL; END $$;
