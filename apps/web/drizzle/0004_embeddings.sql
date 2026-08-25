-- Transcript embedding storage.
--
-- Replaces `data/embeddings/<videoId>.json` under `process.cwd()` — the last
-- remaining instance of audit finding F4. On Vercel that path is a read-only
-- bundle, so `saveEmbeddings()` threw EROFS on every pipeline run, and
-- `loadEmbeddings()` caught the resulting ENOENT and returned `null`. The
-- semantic search endpoint then reported "no embeddings for this video"
-- instead of "embeddings could never be stored": a silent, permanent
-- degradation that looked like an empty index.
--
-- One row per video rather than one per chunk. Chunks are always read and
-- written as a complete set for a single video (the search endpoint scores all
-- of them in process), so per-chunk rows would add join cost and a partial-write
-- failure mode for no gain. If similarity search moves into the database with
-- pgvector, that is a per-chunk table and a deliberate migration, not a
-- silent reshaping of this one.

CREATE TABLE IF NOT EXISTS video_embeddings (
  video_id     text PRIMARY KEY,
  -- ChunkEmbedding[]: { start, duration, text, embedding[] }
  chunks       jsonb NOT NULL,
  chunk_count  integer NOT NULL,
  updated_at   timestamptz NOT NULL DEFAULT now()
);

-- An empty chunk set is not a saved index. Storing one would recreate the
-- exact ambiguity this table exists to remove: a present-but-useless row
-- reading as a successful save.
DO $$ BEGIN
  ALTER TABLE video_embeddings ADD CONSTRAINT video_embeddings_non_empty
    CHECK (chunk_count > 0 AND jsonb_array_length(chunks) = chunk_count);
EXCEPTION WHEN duplicate_object THEN NULL; END $$;
