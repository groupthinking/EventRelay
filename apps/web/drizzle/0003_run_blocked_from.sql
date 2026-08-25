-- Resumption metadata for blocked and failed runs.
--
-- `delivery_runs` recorded *that* a run blocked (`blocked_reason`) but not
-- *where* it stopped, so a blocked run could not be resumed from the failing
-- phase — the operator had to guess, or restart the whole pipeline and redo
-- work that had already succeeded. The lifecycle model in
-- `src/lib/delivery-lifecycle.ts` has always carried `blockedFrom` and `error`;
-- this migration makes the table match the contract the code already assumes.
--
-- Both columns are nullable with no default: they are meaningful only for
-- blocked/failed runs, and back-filling a value for historical rows would
-- invent a phase that was never observed.

ALTER TABLE delivery_runs
  ADD COLUMN IF NOT EXISTS blocked_from text;

ALTER TABLE delivery_runs
  ADD COLUMN IF NOT EXISTS error text;

-- A blocked run must say where it stopped, mirroring the existing
-- `delivery_runs_blocked_requires_reason` constraint. Together they guarantee a
-- blocked run is always fully diagnosable: it has both a reason and an origin.
--
-- Scoped to rows created from here on: pre-existing blocked rows predate the
-- column and cannot retroactively know their origin phase, so validating them
-- would fail on data the application never had the chance to populate.
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'delivery_runs_blocked_requires_origin'
  ) THEN
    ALTER TABLE delivery_runs ADD CONSTRAINT delivery_runs_blocked_requires_origin
      CHECK (status <> 'blocked' OR blocked_from IS NOT NULL) NOT VALID;
  END IF;
END $$;

-- `blocked_from` must name a real phase; a typo would silently break resumption.
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'delivery_runs_blocked_from_valid'
  ) THEN
    ALTER TABLE delivery_runs ADD CONSTRAINT delivery_runs_blocked_from_valid
      CHECK (
        blocked_from IS NULL
        OR blocked_from IN (
          'sourcing', 'requirements', 'planning', 'awaiting_approval',
          'building', 'verifying', 'deploying'
        )
      ) NOT VALID;
  END IF;
END $$;
