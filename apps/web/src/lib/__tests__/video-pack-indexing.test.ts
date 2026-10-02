/**
 * Proves the unified pipeline: when a Video Pack extraction completes, the
 * ready pack is indexed for cross-video search — with its source_hash
 * evidence lineage intact — and indexing can never fail the pack run.
 */
import { describe, expect, it, vi, beforeEach } from 'vitest';

const extractMock = vi.fn();
const putPackRecordMock = vi.fn();
const hydrateMock = vi.fn((pack: unknown) => Promise.resolve(pack));
const indexVideoPackMock = vi.fn();

vi.mock('@/lib/video-pack-extractor', () => ({
  extractVideoPackSpec: (...args: unknown[]) => extractMock(...args),
  VideoPackExtractError: class VideoPackExtractError extends Error {},
}));

vi.mock('@/lib/video-pack-store', () => ({
  claimPackProcessing: vi.fn(),
  getPackRecord: vi.fn(),
  isProcessingStale: vi.fn(),
  putPackRecord: (...args: unknown[]) => putPackRecordMock(...args),
}));

vi.mock('@/lib/keyframe-frame-capture', () => ({
  hydrateKeyframeImages: (pack: unknown) => hydrateMock(pack),
}));

vi.mock('@/lib/search-indexer', () => ({
  indexVideoPack: (...args: unknown[]) => indexVideoPackMock(...args),
}));

import { buildIdentityPack, persistVideoPackExtraction } from '@/lib/video-pack';
import type { ExtractedVideoPackSpec } from '@/lib/video-pack-extractor';

function specFixture(): ExtractedVideoPackSpec {
  return {
    transcript: {
      language: 'en',
      full_text: 'A real extracted transcript with enough substance.',
      segments: [{ idx: 0, start_s: 0, end_s: 30, text: 'A real extracted transcript.' }],
    },
    keyframes: [],
    concepts: ['deployment'],
    requirements: [],
    code_snippets: [],
    visual_context: null,
    architecture: null,
    artifacts: [],
    stack: { tools: [] },
    chapters: [],
    action_items: [],
  };
}

beforeEach(() => {
  vi.clearAllMocks();
  indexVideoPackMock.mockResolvedValue(2);
});

describe('pack completion triggers search indexing (unified pipeline)', () => {
  it('indexes the ready pack with its source_hash after a successful extraction', async () => {
    extractMock.mockResolvedValue(specFixture());
    const identity = buildIdentityPack(
      'auJzb1D-fag',
      'https://www.youtube.com/watch?v=auJzb1D-fag',
    );

    const result = await persistVideoPackExtraction(identity);

    expect(result).toEqual({ state: 'ready' });
    expect(putPackRecordMock).toHaveBeenCalledTimes(1);
    expect(putPackRecordMock.mock.calls[0][0]).toMatchObject({ state: 'ready' });
    expect(indexVideoPackMock).toHaveBeenCalledTimes(1);
    const indexedPack = indexVideoPackMock.mock.calls[0][0];
    expect(indexedPack.video_id).toBe('auJzb1D-fag');
    expect(indexedPack.provenance.source_hash).toMatch(/^[a-f0-9]{64}$/);
  });

  it('still returns ready when indexing throws — indexing is ancillary', async () => {
    extractMock.mockResolvedValue(specFixture());
    indexVideoPackMock.mockRejectedValueOnce(new Error('index down'));
    const identity = buildIdentityPack(
      'auJzb1D-fag',
      'https://www.youtube.com/watch?v=auJzb1D-fag',
    );

    const result = await persistVideoPackExtraction(identity);

    expect(result).toEqual({ state: 'ready' });
    expect(putPackRecordMock).toHaveBeenCalledTimes(1);
  });

  it('does not index when extraction fails', async () => {
    extractMock.mockRejectedValue(new Error('extractor down'));
    const identity = buildIdentityPack(
      'auJzb1D-fag',
      'https://www.youtube.com/watch?v=auJzb1D-fag',
    );

    const result = await persistVideoPackExtraction(identity);

    expect(result).toEqual({ state: 'error' });
    expect(indexVideoPackMock).not.toHaveBeenCalled();
  });
});
