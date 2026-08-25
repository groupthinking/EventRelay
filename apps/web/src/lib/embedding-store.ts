import 'server-only';

/**
 * Transcript embedding storage.
 *
 * Backed by Postgres (`video_embeddings`). The filesystem path survives only as
 * an explicit development fallback for machines with no database configured —
 * never as a silent default.
 *
 * ## Why this was rewritten (audit finding F4)
 *
 * This module wrote `data/embeddings/<videoId>.json` under `process.cwd()`. On
 * Vercel that directory is part of a read-only bundle, so `fs.mkdir` rejected
 * with EROFS and every save threw. The read path then caught its own ENOENT and
 * returned `null`, so `/api/video/search` reported "this video has no
 * embeddings yet" — indistinguishable from a video that simply had not been
 * indexed. The failure was invisible in production and permanent.
 *
 * The two halves of that bug are fixed differently on purpose:
 *
 * - **Writes fail loudly.** `saveEmbeddings` throws when no store is
 *   configured in production. A save that cannot persist is not a save.
 * - **Reads stay tolerant.** `loadEmbeddings` returns `null` for a video that
 *   genuinely has no index — but only after distinguishing that from a missing
 *   store, which it reports.
 */

import { sql } from 'drizzle-orm';
import { getDb, queryRows, requireDb } from '@/lib/db/client';

export interface ChunkEmbedding {
  start: number;
  duration: number;
  text: string;
  embedding: number[];
}

export interface VideoEmbeddings {
  videoId: string;
  chunks: ChunkEmbedding[];
  lastUpdated: string;
}

/**
 * True when the local-file fallback may be used.
 *
 * Gated on both "not production" and "no database", so a misconfigured
 * production deployment fails instead of quietly writing to a disk that will
 * not survive the request.
 */
function fileFallbackAllowed(): boolean {
  return process.env.NODE_ENV !== 'production' && !getDb();
}

/** Development-only path for a video's embeddings. */
async function filePathFor(videoId: string): Promise<string> {
  const path = await import('node:path');
  const safeId = videoId.replace(/[^a-zA-Z0-9_-]/g, '_');
  return path.join(process.cwd(), '.data', 'embeddings', `${safeId}.json`);
}

/**
 * Persist a video's transcript chunk embeddings, replacing any previous set.
 *
 * Throws when there is nowhere durable to write. Callers on the pipeline path
 * treat that as a step failure rather than continuing with an index that does
 * not exist.
 */
export async function saveEmbeddings(videoId: string, chunks: ChunkEmbedding[]): Promise<void> {
  if (chunks.length === 0) {
    // Enforced by CHECK as well; failing here names the caller's mistake.
    throw new Error(`Refusing to save an empty embedding set for video ${videoId}`);
  }

  if (fileFallbackAllowed()) {
    const { mkdir, writeFile } = await import('node:fs/promises');
    const path = await import('node:path');
    const filePath = await filePathFor(videoId);
    await mkdir(path.dirname(filePath), { recursive: true });
    const data: VideoEmbeddings = {
      videoId,
      chunks,
      lastUpdated: new Date().toISOString(),
    };
    await writeFile(filePath, JSON.stringify(data, null, 2), 'utf-8');
    return;
  }

  // requireDb, not getDb: this is the loud failure described above.
  const db = requireDb();
  await db.execute(sql`
    INSERT INTO video_embeddings (video_id, chunks, chunk_count, updated_at)
    VALUES (${videoId}, ${JSON.stringify(chunks)}::jsonb, ${chunks.length}, now())
    ON CONFLICT (video_id) DO UPDATE
      SET chunks      = EXCLUDED.chunks,
          chunk_count = EXCLUDED.chunk_count,
          updated_at  = now()
  `);
}

/**
 * Load a video's embeddings, or `null` when that video has never been indexed.
 *
 * `null` means "not indexed", never "storage was unreachable" — an unreachable
 * store throws, because answering a search with an empty index is the silent
 * degradation this module was rewritten to eliminate.
 */
export async function loadEmbeddings(videoId: string): Promise<VideoEmbeddings | null> {
  if (fileFallbackAllowed()) {
    try {
      const { readFile } = await import('node:fs/promises');
      const raw = await readFile(await filePathFor(videoId), 'utf-8');
      return JSON.parse(raw) as VideoEmbeddings;
    } catch {
      return null;
    }
  }

  const db = requireDb();
  const rows = await queryRows<{ chunks: ChunkEmbedding[]; updated_at: string }>(
    db,
    sql`SELECT chunks, updated_at FROM video_embeddings WHERE video_id = ${videoId}`,
  );
  const row = rows[0];
  if (!row) return null;

  return {
    videoId,
    chunks: row.chunks,
    lastUpdated: new Date(row.updated_at).toISOString(),
  };
}
