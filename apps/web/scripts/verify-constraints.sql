-- Behavioural proof of the delivery constraints.
--
-- `apply-migrations.mjs --check` proves the constraints *exist*. Existence is
-- not the guarantee: a CHECK whose predicate is subtly wrong is present in
-- `pg_constraint` and still accepts the row it was written to reject. That is
-- exactly how `delivery_runs_deployment_url_is_https` passed every existence
-- check while accepting `https://localhost` (fixed in 0002). This file proves
-- behaviour by attempting each forbidden write and failing if it succeeds.
--
-- Run against a database that has had `drizzle/*.sql` applied:
--   npm run db:verify-constraints
--
-- Plain SQL with no psql meta-commands, so `scripts/verify-constraints.mjs`
-- can execute it through the same driver the app uses. Everything happens
-- inside one transaction that is rolled back at the end, so the script leaves
-- no rows behind and is safe to run against a shared development database.

BEGIN;

-- Assert that `stmt` is rejected. Fails loudly if the database accepts it.
CREATE OR REPLACE FUNCTION pg_temp.must_reject(label text, stmt text)
RETURNS void LANGUAGE plpgsql AS $fn$
BEGIN
  BEGIN
    EXECUTE stmt;
  EXCEPTION
    WHEN check_violation OR not_null_violation OR foreign_key_violation
      OR unique_violation OR invalid_text_representation THEN
      RAISE NOTICE 'ok: rejected %', label;
      RETURN;
  END;
  RAISE EXCEPTION 'CONSTRAINT GAP: the database accepted "%" — the guarantee is not enforced', label;
END;
$fn$;

-- Assert that `stmt` is accepted. Guards against a constraint tightened so far
-- that the legitimate path no longer works — a green "nothing bad is storable"
-- suite is worthless if nothing good is storable either.
CREATE OR REPLACE FUNCTION pg_temp.must_accept(label text, stmt text)
RETURNS void LANGUAGE plpgsql AS $fn$
BEGIN
  EXECUTE stmt;
  RAISE NOTICE 'ok: accepted %', label;
END;
$fn$;

-- ── delivered requires evidence ──

SELECT pg_temp.must_reject(
  'delivered run with no repository, tests, or deployment',
  $$INSERT INTO delivery_runs (user_id, title, status, source_kind)
    VALUES ('u1', 'phantom', 'delivered', 'idea')$$
);

SELECT pg_temp.must_reject(
  'delivered run with a repo but no passing tests',
  $$INSERT INTO delivery_runs (user_id, title, status, source_kind, repo_url, deployment_url, delivered_at)
    VALUES ('u1', 'untested', 'delivered', 'idea',
            'https://github.com/acme/x', 'https://x.vercel.app', now())$$
);

SELECT pg_temp.must_reject(
  'delivered run with no delivered_at timestamp',
  $$INSERT INTO delivery_runs (user_id, title, status, source_kind, repo_url, tests_passed_at, deployment_url)
    VALUES ('u1', 'timeless', 'delivered', 'idea',
            'https://github.com/acme/x', now(), 'https://x.vercel.app')$$
);

-- ── deployment_url must be a real live host ──

SELECT pg_temp.must_reject(
  'localhost deployment URL',
  $$INSERT INTO delivery_runs (user_id, title, status, source_kind, deployment_url)
    VALUES ('u1', 'local', 'deploying', 'idea', 'https://localhost:3000')$$
);

SELECT pg_temp.must_reject(
  'documentation-domain deployment URL',
  $$INSERT INTO delivery_runs (user_id, title, status, source_kind, deployment_url)
    VALUES ('u1', 'docs', 'deploying', 'idea', 'https://app.example.com')$$
);

SELECT pg_temp.must_reject(
  'plain http deployment URL',
  $$INSERT INTO delivery_runs (user_id, title, status, source_kind, deployment_url)
    VALUES ('u1', 'insecure', 'deploying', 'idea', 'http://real-host.dev')$$
);

-- ── blocked must be diagnosable ──

SELECT pg_temp.must_reject(
  'blocked run with no reason',
  $$INSERT INTO delivery_runs (user_id, title, status, source_kind, blocked_from)
    VALUES ('u1', 'silent', 'blocked', 'idea', 'building')$$
);

-- ── source shape ──

SELECT pg_temp.must_reject(
  'video run with no source URL',
  $$INSERT INTO delivery_runs (user_id, title, status, source_kind)
    VALUES ('u1', 'sourceless', 'sourcing', 'video')$$
);

SELECT pg_temp.must_reject(
  'idea run carrying a source URL',
  $$INSERT INTO delivery_runs (user_id, title, status, source_kind, source_url)
    VALUES ('u1', 'confused', 'sourcing', 'idea', 'https://youtu.be/auJzb1D-fag')$$
);

-- ── the legitimate paths still work ──

SELECT pg_temp.must_accept(
  'an idea run in sourcing',
  $$INSERT INTO delivery_runs (id, user_id, title, status, source_kind)
    VALUES ('11111111-1111-1111-1111-111111111111', 'u1', 'good idea', 'sourcing', 'idea')$$
);

SELECT pg_temp.must_accept(
  'a fully evidenced delivered run',
  $$INSERT INTO delivery_runs (user_id, title, status, source_kind, repo_url, tests_passed_at, deployment_url, delivered_at)
    VALUES ('u1', 'shipped', 'delivered', 'idea',
            'https://github.com/acme/x', now(), 'https://x.vercel.app', now())$$
);

-- ── gates carry proof ──

SELECT pg_temp.must_reject(
  'passing gate with empty evidence',
  $$INSERT INTO run_gates (run_id, kind, result, evidence)
    VALUES ('11111111-1111-1111-1111-111111111111', 'tests_passed', 'pass', '{}'::jsonb)$$
);

SELECT pg_temp.must_accept(
  'passing gate with real evidence',
  $$INSERT INTO run_gates (run_id, kind, result, evidence)
    VALUES ('11111111-1111-1111-1111-111111111111', 'tests_passed', 'pass',
            '{"exitCode": 0, "passed": 42}'::jsonb)$$
);

SELECT pg_temp.must_reject(
  'a second evaluation of the same gate on the same run',
  $$INSERT INTO run_gates (run_id, kind, result, evidence)
    VALUES ('11111111-1111-1111-1111-111111111111', 'tests_passed', 'fail',
            '{"exitCode": 1}'::jsonb)$$
);

-- ── approvals reference a spec ──

SELECT pg_temp.must_reject(
  'approval with no spec version attached',
  $$INSERT INTO run_approvals (run_id, decision, decided_by)
    VALUES ('11111111-1111-1111-1111-111111111111', 'approved', 'founder@acme.test')$$
);

SELECT pg_temp.must_reject(
  'approval carrying an unrecognised decision',
  $$WITH s AS (
      INSERT INTO run_specs (run_id, requirements, plan)
      VALUES ('11111111-1111-1111-1111-111111111111', '{}'::jsonb, '{}'::jsonb)
      RETURNING id
    )
    INSERT INTO run_approvals (run_id, spec_id, decision, decided_by)
    SELECT '11111111-1111-1111-1111-111111111111', s.id, 'probably', 'founder@acme.test'
      FROM s$$
);

-- ── embeddings are never stored empty ──

SELECT pg_temp.must_reject(
  'embedding row with zero chunks',
  $$INSERT INTO video_embeddings (video_id, chunks, chunk_count)
    VALUES ('auJzb1D-fag', '[]'::jsonb, 0)$$
);

SELECT pg_temp.must_reject(
  'embedding row whose count disagrees with its chunks',
  $$INSERT INTO video_embeddings (video_id, chunks, chunk_count)
    VALUES ('auJzb1D-fag', '[{"start":0}]'::jsonb, 7)$$
);

-- ── training dedup ──

SELECT pg_temp.must_accept(
  'a training example',
  $$INSERT INTO training_examples (video_url, example, analysis)
    VALUES ('https://youtu.be/auJzb1D-fag', '{}'::jsonb, '{}'::jsonb)$$
);

SELECT pg_temp.must_reject(
  'a duplicate training example for the same video',
  $$INSERT INTO training_examples (video_url, example, analysis)
    VALUES ('https://youtu.be/auJzb1D-fag', '{}'::jsonb, '{}'::jsonb)$$
);

ROLLBACK;
