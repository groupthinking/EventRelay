-- Training dataset storage.
--
-- Replaces `data/training/video-analysis.jsonl` + `metadata.json`, which were
-- written under `process.cwd()`. On Vercel that path is a read-only bundle, so
-- every write threw EROFS (audit finding F4). Worse, `getMetadata()` called
-- `ensureDir()` before reading, so even the *read* path threw — meaning the
-- training status endpoint failed rather than reporting an empty dataset.
--
-- Dedup moves from an application-level `videosProcessed.includes(url)` array
-- scan to a UNIQUE constraint. The array check was also a race: two concurrent
-- pipeline runs for the same video could both observe "not present" and both
-- append, silently corrupting the fine-tuning dataset with duplicates. A UNIQUE
-- index makes that outcome impossible regardless of concurrency.

CREATE TABLE IF NOT EXISTS training_examples (
  id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  video_url    text NOT NULL,
  video_title  text NOT NULL DEFAULT 'Unknown',
  -- Vertex AI SFT-formatted example, ready to serialise as JSONL.
  example      jsonb NOT NULL,
  -- Raw analysis output retained so the example can be regenerated if the
  -- prompt format changes, without re-running the (paid) analysis.
  analysis     jsonb NOT NULL,
  exported_at  timestamptz,
  created_at   timestamptz NOT NULL DEFAULT now()
);

-- The dedup guarantee.
CREATE UNIQUE INDEX IF NOT EXISTS training_examples_video_url_idx
  ON training_examples (video_url);

-- Ordering for JSONL export.
CREATE INDEX IF NOT EXISTS training_examples_created_idx
  ON training_examples (created_at);

-- Singleton row tracking fine-tuning job state. `id` is pinned to a constant so
-- a second row cannot be created.
CREATE TABLE IF NOT EXISTS training_runs (
  id                  integer PRIMARY KEY DEFAULT 1,
  tuning_triggered_at timestamptz,
  tuning_job_id       text,
  CONSTRAINT training_runs_singleton CHECK (id = 1)
);

INSERT INTO training_runs (id) VALUES (1) ON CONFLICT (id) DO NOTHING;
