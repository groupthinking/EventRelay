import 'server-only';

/**
 * Indexes completed video analyses into the durable Upstash Search index so
 * cross-video search (/api/search) fills organically from the pipeline.
 *
 * This is the durable complement to the local-disk stores (`training-store`,
 * `embedding-store`), whose writes fail on Vercel's read-only filesystem
 * (ENOENT /var/task/apps/web/data in production logs). Indexing is ancillary:
 * callers run it via waitUntil after the SSE stream completes, and a missing
 * Upstash config results in an honest skip — never fabricated success.
 */

import { getSearchIndex, resolveSearchIndexName } from './upstash-search';
import type { SearchDocument } from './upstash-search';
import type { VideoAnalysisResult } from './gemini-video-analyzer';

/** Target size of one transcript document's text (~400 tokens). */
const CHUNK_CHAR_TARGET = 1600;
/** Bound the per-video batch well under the /api/search upsert cap of 100. */
const MAX_TRANSCRIPT_DOCS = 40;

export function extractVideoId(videoUrl: string): string {
  return (
    videoUrl.match(/[?&]v=([^&]+)/)?.[1] || videoUrl.replace(/[^a-zA-Z0-9_-]/g, '_')
  );
}

/** Merge transcript segments into ~CHUNK_CHAR_TARGET-sized texts, keeping the start offset of each chunk. */
function chunkTranscriptText(
  transcript: VideoAnalysisResult['transcript'],
): { start: number; text: string }[] {
  const chunks: { start: number; text: string }[] = [];
  let current = '';
  let currentStart = 0;
  for (const segment of transcript) {
    const text = segment.text?.trim();
    if (!text) continue;
    if (!current) currentStart = segment.start;
    current = current ? `${current} ${text}` : text;
    if (current.length >= CHUNK_CHAR_TARGET) {
      chunks.push({ start: currentStart, text: current });
      current = '';
    }
  }
  if (current) chunks.push({ start: currentStart, text: current });
  return chunks;
}

export function buildVideoDocuments(
  videoUrl: string,
  analysis: VideoAnalysisResult,
): SearchDocument[] {
  const videoId = extractVideoId(videoUrl);
  const indexedAt = new Date().toISOString();

  const documents: SearchDocument[] = [
    {
      id: `video:${videoId}`,
      content: {
        title: analysis.title || videoId,
        summary: analysis.summary || '',
        topics: (analysis.topics || []).join(', '),
        events: (analysis.events || []).map((e) => e.label).join('; '),
      },
      metadata: { url: videoUrl, videoId, type: 'video_summary', indexedAt },
    },
  ];

  const chunks = chunkTranscriptText(analysis.transcript || []);
  const dropped = Math.max(0, chunks.length - MAX_TRANSCRIPT_DOCS);
  for (const [i, chunk] of chunks.slice(0, MAX_TRANSCRIPT_DOCS).entries()) {
    documents.push({
      id: `video:${videoId}:t${i}`,
      content: {
        title: analysis.title || videoId,
        text: chunk.text,
      },
      metadata: {
        url: videoUrl,
        videoId,
        type: 'transcript_chunk',
        startSeconds: chunk.start,
        indexedAt,
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
 * Upserts the analysis into the Upstash Search index. Returns the number of
 * documents indexed, or null when Upstash Search is not configured (skip is
 * logged once per call; this path must never fail the pipeline).
 */
export async function indexVideoAnalysis(
  videoUrl: string,
  analysis: VideoAnalysisResult,
): Promise<number | null> {
  const index = getSearchIndex();
  if (!index) {
    console.log('[SearchIndex] Skipped: UPSTASH_SEARCH_REST_URL/TOKEN not configured.');
    return null;
  }
  const documents = buildVideoDocuments(videoUrl, analysis);
  await index.upsert(documents);
  console.log(
    `[SearchIndex] Upserted ${documents.length} documents for ${extractVideoId(videoUrl)} into "${resolveSearchIndexName()}".`,
  );
  return documents.length;
}
