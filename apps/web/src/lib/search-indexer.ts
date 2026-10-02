import 'server-only';

/**
 * Indexes completed Video Packs into the durable Upstash Search index so
 * cross-video search (/api/search) fills organically from the canonical
 * Video Pack pipeline (`POST /api/video/pack` → Upstash).
 *
 * This is the durable complement to the local-disk stores (`training-store`,
 * `embedding-store`), whose writes fail on Vercel's read-only filesystem
 * (ENOENT /var/task/apps/web/data in production logs). Indexing is ancillary:
 * a missing Upstash config — or any upsert failure — results in an honest
 * skip, never a failed pack run and never fabricated success.
 *
 * Evidence lineage: every document carries the pack's `source_hash` in its
 * metadata, so indexed content always traces back to a hashed Video Pack.
 */

import { getSearchIndex, resolveSearchIndexName } from './upstash-search';
import type { SearchDocument } from './upstash-search';
import type { VideoPackV0Json } from './video-pack';

/** Target size of one transcript document's text (~400 tokens). */
const CHUNK_CHAR_TARGET = 1600;
/** Bound the per-video batch well under the /api/search upsert cap of 100. */
const MAX_TRANSCRIPT_DOCS = 40;

/** Merge pack transcript segments into ~CHUNK_CHAR_TARGET-sized texts, keeping the start offset of each chunk. */
function chunkPackTranscript(
  segments: VideoPackV0Json['transcript']['segments'],
): { start: number; text: string }[] {
  const chunks: { start: number; text: string }[] = [];
  let current = '';
  let currentStart = 0;
  for (const segment of segments || []) {
    const text = segment.text?.trim();
    if (!text) continue;
    if (!current) currentStart = segment.start_s;
    current = current ? `${current} ${text}` : text;
    if (current.length >= CHUNK_CHAR_TARGET) {
      chunks.push({ start: currentStart, text: current });
      current = '';
    }
  }
  if (current) chunks.push({ start: currentStart, text: current });
  return chunks;
}

export function buildVideoPackDocuments(pack: VideoPackV0Json): SearchDocument[] {
  const videoId = pack.video_id;
  const indexedAt = new Date().toISOString();
  const sourceHash = pack.provenance?.source_hash ?? '';
  const title = pack.concepts?.[0] || videoId;

  const documents: SearchDocument[] = [
    {
      id: `video:${videoId}`,
      content: {
        title,
        summary: (pack.concepts || []).join(', '),
        topics: (pack.concepts || []).join(', '),
        requirements: (pack.requirements || []).map((r) => r.title).join('; '),
        action_items: (pack.action_items || []).map((a) => a.title).join('; '),
      },
      metadata: {
        url: pack.source_url,
        videoId,
        type: 'video_summary',
        indexedAt,
        source_hash: sourceHash,
      },
    },
  ];

  const chunks = chunkPackTranscript(pack.transcript?.segments || []);
  const dropped = Math.max(0, chunks.length - MAX_TRANSCRIPT_DOCS);
  for (const [i, chunk] of chunks.slice(0, MAX_TRANSCRIPT_DOCS).entries()) {
    documents.push({
      id: `video:${videoId}:t${i}`,
      content: {
        title,
        text: chunk.text,
      },
      metadata: {
        url: pack.source_url,
        videoId,
        type: 'transcript_chunk',
        startSeconds: chunk.start,
        indexedAt,
        source_hash: sourceHash,
      },
    });
  }
  if (dropped > 0) {
    console.warn(
      `[SearchIndex] Transcript for ${videoId} exceeds ${MAX_TRANSCRIPT_DOCS} chunks; dropped ${dropped} tail chunks.`,
    );
  }

  return documents;
}

/**
 * Upserts the ready pack into the Upstash Search index. Returns the number of
 * documents indexed, or null when Upstash Search is not configured or the
 * upsert failed. This path must never throw — indexing is ancillary to the
 * pack run.
 */
export async function indexVideoPack(pack: VideoPackV0Json): Promise<number | null> {
  const index = getSearchIndex();
  if (!index) {
    console.log('[SearchIndex] Skipped: UPSTASH_SEARCH_REST_URL/TOKEN not configured.');
    return null;
  }
  try {
    const documents = buildVideoPackDocuments(pack);
    await index.upsert(documents);
    console.log(
      `[SearchIndex] Upserted ${documents.length} documents for ${pack.video_id} into "${resolveSearchIndexName()}".`,
    );
    return documents.length;
  } catch (error) {
    console.warn(
      '[SearchIndex] Upsert failed (non-fatal):',
      error instanceof Error ? error.message : error,
    );
    return null;
  }
}
