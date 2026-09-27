import 'server-only';

import { GATEWAY_CHAT_MODEL, aiGateway } from '@/lib/ai-gateway';
import { mapWithBoundedConcurrency } from '@/lib/video-pack-extract-segments';
import { hasAiGatewayKey } from '@/lib/vercel-ai-gateway';
import { fetchYouTubeCaptions, type CaptionSegment } from '@/lib/youtube-captions';

/**
 * Gate 2 transcript team (locked scope 2026-09-22).
 *
 * 1. Fetch captions/timed text ONCE (YouTube captions first).
 * 2. Denial-of-wallet guard: paid providers never run when captions hit.
 * 3. Parallel text-chunk analysis over gateway text models.
 *
 * No Gemini video calls. No media download. Video stays on the direct
 * Interactions path; the gateway is used here for TEXT analysis only.
 *
 * TODO(open-item): paid STT fallback (incl. user-named
 * `grok-voice-transcribe-2.0`). xAI STT accepts multipart `file` bytes or a
 * server-side `url` (POST api.x.ai/v1/stt), but YouTube exposes no stable
 * direct audio URL — resolving one needs audio-stream extraction (signed,
 * expiring, IP-bound googlevideo URLs) that does not exist in-repo and
 * likely fails xAI server-side fetch. Until a no-download audio resolver
 * is proven, the team stays captions-only and returns null on a caption
 * miss. Do not invent vendors or wire unproven fallbacks.
 */

export interface TranscriptTeamSegment {
  start_s: number;
  end_s: number;
  text: string;
}

export interface TranscriptChunk {
  index: number;
  start_s: number;
  end_s: number;
  text: string;
  charCount: number;
}

export interface TranscriptChunkEvidence {
  index: number;
  start_s: number;
  end_s: number;
  /** Short grounded bullets from this chunk only. Empty when !analyzed. */
  bullets: string[];
  /** Named tools/concepts from this chunk only. Empty when !analyzed. */
  entities: string[];
  analyzed: boolean;
}

export interface TranscriptTeamResult {
  transcript: string;
  segments: TranscriptTeamSegment[];
  source: 'youtube-captions';
  acquisitionMethod: 'youtube-captions';
  chunks: TranscriptChunk[];
  evidence: TranscriptChunkEvidence[];
  failedChunkIndexes: number[];
  /**
   * Paid providers invoked during this run. Always [] while captions-only;
   * any future fallback MUST record itself here (guard proof).
   */
  paidProvidersCalled: string[];
}

/** Bounded fan-out for text-chunk analysis (cheap text models only). */
export const TRANSCRIPT_CHUNK_MAX_PARALLEL = 4;
/** Target text size per analysis chunk. */
export const TRANSCRIPT_CHUNK_TARGET_CHARS = 4000;
/** Hard cap so pathological transcripts cannot fan out unboundedly. */
export const TRANSCRIPT_CHUNK_MAX_COUNT = 12;

/**
 * Pack timed segments into text chunks (greedy, order-preserving, pure).
 * Ranges always cover exactly the segments packed — no invention.
 */
export function chunkTranscriptSegments(
  segments: TranscriptTeamSegment[],
  options: { targetChars?: number; maxChunks?: number } = {},
): TranscriptChunk[] {
  const targetChars = Math.max(1, options.targetChars ?? TRANSCRIPT_CHUNK_TARGET_CHARS);
  const maxChunks = Math.max(1, options.maxChunks ?? TRANSCRIPT_CHUNK_MAX_COUNT);
  const clean = segments.filter((s) => s.text.trim().length > 0 && s.end_s >= s.start_s);
  if (clean.length === 0) return [];

  const chunks: TranscriptChunk[] = [];
  let current: TranscriptTeamSegment[] = [];
  let currentChars = 0;
  const flush = () => {
    if (current.length === 0) return;
    const first = current[0];
    const last = current[current.length - 1];
    const text = current.map((s) => s.text.trim()).join(' ');
    chunks.push({
      index: chunks.length,
      start_s: first.start_s,
      end_s: last.end_s,
      text,
      charCount: text.length,
    });
    current = [];
    currentChars = 0;
  };
  for (const segment of clean) {
    const text = segment.text.trim();
    if (current.length > 0 && currentChars + text.length > targetChars) {
      flush();
    }
    current.push({ ...segment, text });
    currentChars += text.length;
  }
  flush();

  // Over cap: widen by merging adjacent chunks (never drop content).
  while (chunks.length > maxChunks) {
    let mergeAt = 0;
    let smallest = Number.POSITIVE_INFINITY;
    for (let i = 0; i < chunks.length - 1; i += 1) {
      const size = chunks[i].charCount + chunks[i + 1].charCount;
      if (size < smallest) {
        smallest = size;
        mergeAt = i;
      }
    }
    const [first, second] = [chunks[mergeAt], chunks[mergeAt + 1]];
    const text = `${first.text} ${second.text}`;
    chunks.splice(mergeAt, 2, {
      index: mergeAt,
      start_s: first.start_s,
      end_s: second.end_s,
      text,
      charCount: text.length,
    });
    for (let i = mergeAt + 1; i < chunks.length; i += 1) {
      chunks[i].index = i;
    }
  }
  return chunks;
}

export type FetchCaptions = (
  url: string,
  language?: string,
) => Promise<{ transcript: string; segments: CaptionSegment[]; source: string } | null>;

export interface FetchedCaptions {
  transcript: string;
  segments: TranscriptTeamSegment[];
}

function toTeamSegments(segments: CaptionSegment[]): TranscriptTeamSegment[] {
  return segments.flatMap((segment) => {
    const text = segment.text.trim().replace(/\s+/g, ' ');
    const start_s = Number.isFinite(segment.start) && segment.start >= 0 ? segment.start : 0;
    const duration = Number.isFinite(segment.duration) && segment.duration > 0 ? segment.duration : 0;
    if (!text) return [];
    return [{ start_s, end_s: start_s + duration, text }];
  });
}

/**
 * Single captions acquisition. One call, no retries here (the captions
 * module owns transport retries), no paid providers, no media.
 */
export async function fetchCaptionsOnce(
  sourceUrl: string,
  language: string,
  fetchCaptions: FetchCaptions = fetchYouTubeCaptions,
): Promise<FetchedCaptions | null> {
  const captions = await fetchCaptions(sourceUrl, language);
  if (!captions) return null;
  const segments = toTeamSegments(captions.segments);
  const transcript = segments.map((s) => s.text).join(' ').replace(/\s+/g, ' ').trim();
  if (segments.length === 0 || transcript.length < 40) return null;
  return { transcript, segments };
}

export type AnalyzeTranscriptChunk = (
  chunk: TranscriptChunk,
  videoId: string,
) => Promise<TranscriptChunkEvidence>;

function parseChunkEvidence(text: string, chunk: TranscriptChunk): TranscriptChunkEvidence {
  const base = {
    index: chunk.index,
    start_s: chunk.start_s,
    end_s: chunk.end_s,
  };
  try {
    const cleaned = text.replace(/^```(?:json)?/i, '').replace(/```$/, '').trim();
    const parsed = JSON.parse(cleaned) as { bullets?: unknown; entities?: unknown };
    const bullets = Array.isArray(parsed.bullets)
      ? parsed.bullets.filter((b): b is string => typeof b === 'string' && b.trim().length > 0).slice(0, 6)
      : [];
    const entities = Array.isArray(parsed.entities)
      ? parsed.entities.filter((e): e is string => typeof e === 'string' && e.trim().length > 0).slice(0, 10)
      : [];
    if (bullets.length === 0 && entities.length === 0) {
      return { ...base, bullets: [], entities: [], analyzed: false };
    }
    return { ...base, bullets, entities, analyzed: true };
  } catch {
    return { ...base, bullets: [], entities: [], analyzed: false };
  }
}

/**
 * Default chunk analyzer: gateway TEXT model (openai/gpt-4o). Text in,
 * JSON out — never video, never media. Per-chunk failures yield
 * analyzed:false and never throw, so one bad chunk cannot sink the team;
 * failures are reported explicitly in failedChunkIndexes.
 */
export async function analyzeTranscriptChunkWithGateway(
  chunk: TranscriptChunk,
  videoId: string,
): Promise<TranscriptChunkEvidence> {
  const base = {
    index: chunk.index,
    start_s: chunk.start_s,
    end_s: chunk.end_s,
  };
  if (!hasAiGatewayKey()) {
    return { ...base, bullets: [], entities: [], analyzed: false };
  }
  try {
    const { generateText } = await import('ai');
    const result = await generateText({
      model: aiGateway(GATEWAY_CHAT_MODEL),
      messages: [
        {
          role: 'user',
          content: [
            {
              type: 'text',
              text: [
                `Extract evidence bullets and named entities from this video transcript chunk (video ${videoId}, seconds ${chunk.start_s}–${chunk.end_s}).`,
                'Use ONLY the text below. Do not invent content from outside the chunk.',
                'Return ONLY a JSON object: {"bullets": string[≤6], "entities": string[≤10]}.',
                '',
                chunk.text,
              ].join('\n'),
            },
          ],
        },
      ],
      abortSignal: AbortSignal.timeout(30_000),
    });
    return parseChunkEvidence(result.text, chunk);
  } catch {
    return { ...base, bullets: [], entities: [], analyzed: false };
  }
}

/**
 * Run the transcript team: fetch once → chunk → analyze in parallel.
 * Returns null when captions miss (paid STT fallback is TODO(open-item)).
 */
export async function runTranscriptTeam(
  input: { videoId: string; sourceUrl: string; language?: string },
  deps: {
    fetchCaptions?: FetchCaptions;
    analyzeChunk?: AnalyzeTranscriptChunk;
    parallelCap?: number;
  } = {},
): Promise<TranscriptTeamResult | null> {
  const fetched = await fetchCaptionsOnce(
    input.sourceUrl,
    input.language ?? 'en',
    deps.fetchCaptions,
  );
  if (!fetched) return null;

  const chunks = chunkTranscriptSegments(fetched.segments);
  const analyze = deps.analyzeChunk ?? analyzeTranscriptChunkWithGateway;
  const cap = Math.min(Math.max(1, deps.parallelCap ?? TRANSCRIPT_CHUNK_MAX_PARALLEL), TRANSCRIPT_CHUNK_MAX_PARALLEL);
  const evidence = await mapWithBoundedConcurrency(chunks, cap, async (chunk) =>
    analyze(chunk, input.videoId),
  );
  return {
    transcript: fetched.transcript,
    segments: fetched.segments,
    source: 'youtube-captions',
    acquisitionMethod: 'youtube-captions',
    chunks,
    evidence,
    failedChunkIndexes: evidence.filter((e) => !e.analyzed).map((e) => e.index),
    paidProvidersCalled: [],
  };
}

/**
 * Backfill voids only: when the model emitted zero usable segments, use
 * caption segments (re-indexed). Never overwrites model output.
 */
export function backfillTranscriptSegments(
  specSegments: Array<{ idx?: number; start_s?: number; end_s?: number; text?: string }>,
  captions: TranscriptTeamSegment[],
): Array<{ idx: number; start_s: number; end_s: number; text: string }> {
  const usable = (specSegments ?? []).filter(
    (s): s is { idx?: number; start_s: number; end_s: number; text: string } =>
      typeof s?.text === 'string' &&
      s.text.trim().length > 0 &&
      typeof s.start_s === 'number' &&
      typeof s.end_s === 'number',
  );
  if (usable.length > 0) {
    return usable.map((s, i) => ({ idx: s.idx ?? i, start_s: s.start_s, end_s: s.end_s, text: s.text }));
  }
  return captions.map((s, i) => ({ idx: i, start_s: s.start_s, end_s: s.end_s, text: s.text }));
}
