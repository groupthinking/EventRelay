import { describe, expect, it, vi } from 'vitest';
import type { CaptionSegment } from '@/lib/youtube-captions';
import {
  analyzeTranscriptChunkWithGateway,
  backfillTranscriptSegments,
  chunkTranscriptSegments,
  fetchCaptionsOnce,
  runTranscriptTeam,
  TRANSCRIPT_CHUNK_MAX_PARALLEL,
  type TranscriptTeamSegment,
} from '@/lib/transcript-team';

const SOURCE_URL = 'https://www.youtube.com/watch?v=auJzb1D-fag';

function captionSegments(n: number, wordsPerSegment = 40): CaptionSegment[] {
  return Array.from({ length: n }, (_, i) => ({
    start: i * 5,
    duration: 5,
    text: `spoken words segment ${i} ${'filler '.repeat(wordsPerSegment)}`.trim(),
  }));
}

function teamSegments(n: number): TranscriptTeamSegment[] {
  return Array.from({ length: n }, (_, i) => ({
    start_s: i * 5,
    end_s: i * 5 + 5,
    text: `Segment ${i} spoken content here.`,
  }));
}

describe('chunkTranscriptSegments', () => {
  it('packs segments greedily with exact time ranges', () => {
    const chunks = chunkTranscriptSegments(teamSegments(4), { targetChars: 60 });
    expect(chunks.length).toBeGreaterThanOrEqual(2);
    expect(chunks[0]).toMatchObject({ index: 0, start_s: 0 });
    const last = chunks[chunks.length - 1];
    expect(last.end_s).toBe(20);
    for (const [i, chunk] of chunks.entries()) {
      expect(chunk.index).toBe(i);
      expect(chunk.end_s).toBeGreaterThanOrEqual(chunk.start_s);
      expect(chunk.charCount).toBe(chunk.text.length);
    }
  });

  it('drops empty segments and returns [] for empty input', () => {
    expect(chunkTranscriptSegments([])).toEqual([]);
    expect(
      chunkTranscriptSegments([
        { start_s: 0, end_s: 5, text: '   ' },
        { start_s: 5, end_s: 10, text: 'Real words here.' },
      ]),
    ).toHaveLength(1);
  });

  it('merges (never drops) when over the chunk cap', () => {
    const chunks = chunkTranscriptSegments(teamSegments(20), { targetChars: 50, maxChunks: 3 });
    expect(chunks).toHaveLength(3);
    const joined = chunks.map((c) => c.text).join(' ');
    expect(joined).toContain('Segment 0');
    expect(joined).toContain('Segment 19');
    expect(chunks[0].start_s).toBe(0);
    expect(chunks[2].end_s).toBe(100);
  });
});

describe('fetchCaptionsOnce', () => {
  it('calls the fetcher exactly once and normalizes segments', async () => {
    const fetchCaptions = vi.fn(async () => ({
      transcript: 'a '.repeat(50),
      segments: captionSegments(3, 10),
      source: 'youtube-captions',
    }));
    const result = await fetchCaptionsOnce(SOURCE_URL, 'en', fetchCaptions);
    expect(fetchCaptions).toHaveBeenCalledTimes(1);
    expect(fetchCaptions).toHaveBeenCalledWith(SOURCE_URL, 'en');
    expect(result?.segments).toHaveLength(3);
    expect(result?.segments[0]).toMatchObject({ start_s: 0, end_s: 5 });
  });

  it('returns null on a caption miss (no fallback, no throw)', async () => {
    const fetchCaptions = vi.fn(async () => null);
    await expect(fetchCaptionsOnce(SOURCE_URL, 'en', fetchCaptions)).resolves.toBeNull();
    expect(fetchCaptions).toHaveBeenCalledTimes(1);
  });
});

describe('runTranscriptTeam', () => {
  it('fetches once, chunks, and analyzes in parallel with no paid providers', async () => {
    const fetchCaptions = vi.fn(async () => ({
      transcript: 'word '.repeat(200),
      segments: captionSegments(10, 30),
      source: 'youtube-captions',
    }));
    const seen: number[] = [];
    const result = await runTranscriptTeam(
      { videoId: 'auJzb1D-fag', sourceUrl: SOURCE_URL },
      {
        fetchCaptions,
        analyzeChunk: async (chunk) => {
          seen.push(chunk.index);
          return {
            index: chunk.index,
            start_s: chunk.start_s,
            end_s: chunk.end_s,
            bullets: [`About ${chunk.start_s}s`],
            entities: ['Test'],
            analyzed: true,
          };
        },
      },
    );
    expect(result).not.toBeNull();
    expect(fetchCaptions).toHaveBeenCalledTimes(1);
    expect(result?.source).toBe('youtube-captions');
    expect(result?.paidProvidersCalled).toEqual([]);
    expect(result?.evidence).toHaveLength(result?.chunks.length ?? 0);
    expect(result?.failedChunkIndexes).toEqual([]);
    expect([...seen].sort((a, b) => a - b)).toEqual(
      result?.chunks.map((c) => c.index) ?? [],
    );
  });

  it('records analyzed:false flags without throwing', async () => {
    const fetchCaptions = vi.fn(async () => ({
      transcript: 'word '.repeat(200),
      segments: captionSegments(6, 40),
      source: 'youtube-captions',
    }));
    const result = await runTranscriptTeam(
      { videoId: 'auJzb1D-fag', sourceUrl: SOURCE_URL },
      {
        fetchCaptions,
        analyzeChunk: async (chunk) => ({
          index: chunk.index,
          start_s: chunk.start_s,
          end_s: chunk.end_s,
          bullets: [],
          entities: [],
          analyzed: false,
        }),
      },
    );
    expect(result?.evidence.every((e) => !e.analyzed)).toBe(true);
    expect(result?.failedChunkIndexes).toEqual(result?.chunks.map((c) => c.index));
  });

  it('lets an injected throwing analyzer propagate (caller bug, not evidence)', async () => {
    const fetchCaptions = vi.fn(async () => ({
      transcript: 'word '.repeat(200),
      segments: captionSegments(2, 40),
      source: 'youtube-captions',
    }));
    await expect(
      runTranscriptTeam(
        { videoId: 'auJzb1D-fag', sourceUrl: SOURCE_URL },
        {
          fetchCaptions,
          analyzeChunk: async () => {
            throw new Error('analyzer bug');
          },
        },
      ),
    ).rejects.toThrow('analyzer bug');
  });

  it('returns null when captions miss (captions-only, no paid fallback)', async () => {
    const analyzeChunk = vi.fn();
    const result = await runTranscriptTeam(
      { videoId: 'auJzb1D-fag', sourceUrl: SOURCE_URL },
      { fetchCaptions: async () => null, analyzeChunk },
    );
    expect(result).toBeNull();
    expect(analyzeChunk).not.toHaveBeenCalled();
  });

  it('caps parallelism at TRANSCRIPT_CHUNK_MAX_PARALLEL', () => {
    expect(TRANSCRIPT_CHUNK_MAX_PARALLEL).toBe(4);
  });
});

describe('analyzeTranscriptChunkWithGateway', () => {
  it('returns analyzed:false without a gateway key (no throw, no call)', async () => {
    const prev = process.env.AI_GATEWAY_API_KEY;
    const prevVercel = process.env.VERCEL_AI_GATEWAY_API_KEY;
    try {
      delete process.env.AI_GATEWAY_API_KEY;
      delete process.env.VERCEL_AI_GATEWAY_API_KEY;
      const evidence = await analyzeTranscriptChunkWithGateway(
        { index: 0, start_s: 0, end_s: 180, text: 'hello world', charCount: 11 },
        'auJzb1D-fag',
      );
      expect(evidence).toMatchObject({ analyzed: false, bullets: [], entities: [] });
    } finally {
      if (prev !== undefined) process.env.AI_GATEWAY_API_KEY = prev;
      if (prevVercel !== undefined) process.env.VERCEL_AI_GATEWAY_API_KEY = prevVercel;
    }
  });
});

describe('backfillTranscriptSegments', () => {
  it('keeps model segments when present', () => {
    const model = [{ idx: 0, start_s: 1, end_s: 2, text: 'Model speech.' }];
    const captions: TranscriptTeamSegment[] = [{ start_s: 0, end_s: 5, text: 'Caption speech.' }];
    expect(backfillTranscriptSegments(model, captions)).toEqual(model);
  });

  it('fills voids from captions with fresh indexes', () => {
    const captions: TranscriptTeamSegment[] = [
      { start_s: 0, end_s: 5, text: 'Caption one.' },
      { start_s: 5, end_s: 9, text: 'Caption two.' },
    ];
    expect(backfillTranscriptSegments([], captions)).toEqual([
      { idx: 0, start_s: 0, end_s: 5, text: 'Caption one.' },
      { idx: 1, start_s: 5, end_s: 9, text: 'Caption two.' },
    ]);
    expect(backfillTranscriptSegments([{ text: '  ' }], captions)).toHaveLength(2);
  });
});
