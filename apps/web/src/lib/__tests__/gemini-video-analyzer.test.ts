import { describe, it, expect, afterEach, vi } from 'vitest';

const { gatewayChatMock } = vi.hoisted(() => ({ gatewayChatMock: vi.fn() }));

vi.mock('@/lib/vercel-ai-gateway', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/lib/vercel-ai-gateway')>();
  return {
    ...actual,
    hasAiGatewayKey: () => true,
    gatewayChat: gatewayChatMock,
  };
});

vi.mock('@/lib/transcription-service', () => ({
  fetchTranscript: vi.fn(async () => ({ success: false, error: 'unavailable in tests' })),
}));

import {
  AnalysisParseError,
  analyzeVideoWithGemini,
  parseAnalysisResult,
} from '@/lib/gemini-video-analyzer';

const VALID_ANALYSIS = {
  title: 'T',
  summary: 'S',
  transcript: [{ start: 0, duration: 5, text: 'hello' }],
  events: [],
  actions: [],
  topics: ['a'],
  architectureCode: '',
  ingestScript: '',
  e22Snippets: [],
};
const VALID_JSON = JSON.stringify(VALID_ANALYSIS);
const TEST_EVIDENCE = {
  transcript: 'This is verified source speech with enough content to support deterministic analysis.',
  segments: [{
    start: 0,
    duration: 5,
    text: 'This is verified source speech with enough content to support deterministic analysis.',
  }],
  provenance: {
    sourceUrl: 'https://www.youtube.com/watch?v=auJzb1D-fag',
    sourceHost: 'www.youtube.com',
    acquisitionMethod: 'backend-caption-api',
    transcriptSource: 'youtube-captions',
    transcriptVerified: true,
    acquiredAt: '2026-08-16T12:00:00.000Z',
    segmentCount: 1,
    timedSegmentCount: 1,
    durationCoverageSeconds: 5,
    warnings: [],
  },
};

afterEach(() => {
  gatewayChatMock.mockReset();
  vi.useRealTimers();
});

describe('parseAnalysisResult', () => {
  it('parses clean JSON', () => {
    expect(parseAnalysisResult(VALID_JSON).title).toBe('T');
  });

  it('parses fenced JSON', () => {
    expect(parseAnalysisResult('```json\n' + VALID_JSON + '\n```').title).toBe('T');
  });

  it('parses pretty-printed multi-line fenced JSON', () => {
    const pretty = JSON.stringify(VALID_ANALYSIS, null, 2);
    expect(parseAnalysisResult('```json\n' + pretty + '\n```').title).toBe('T');
  });

  it('salvages a JSON object wrapped in prose', () => {
    const noisy = `Here is the analysis you asked for:\n${VALID_JSON}\nLet me know if you need more.`;
    expect(parseAnalysisResult(noisy).summary).toBe('S');
  });

  it('throws AnalysisParseError on unsalvageable output', () => {
    expect(() => parseAnalysisResult("{'title': 'single quotes are not JSON'}")).toThrow(
      AnalysisParseError,
    );
  });

  it('throws AnalysisParseError on truncated JSON (unterminated string)', () => {
    expect(() => parseAnalysisResult(VALID_JSON.slice(0, VALID_JSON.length / 2))).toThrow(
      AnalysisParseError,
    );
  });
});

describe('analyzeVideoWithGemini retry on parse failure', () => {
  it('retries when the model returns malformed JSON and succeeds on the next attempt', async () => {
    vi.useFakeTimers();
    gatewayChatMock
      .mockResolvedValueOnce({ content: "{'not': 'json'}" })
      .mockResolvedValueOnce({ content: VALID_JSON });

    const promise = analyzeVideoWithGemini(
      'https://www.youtube.com/watch?v=auJzb1D-fag',
      TEST_EVIDENCE,
    );
    await vi.advanceTimersByTimeAsync(5_000); // cover the 2s backoff after attempt 1
    const result = await promise;

    expect(result.title).toBe('T');
    expect(gatewayChatMock).toHaveBeenCalledTimes(2);
  });

  it('gives up after max retries of malformed JSON', async () => {
    vi.useFakeTimers();
    gatewayChatMock.mockResolvedValue({ content: 'not json at all' });

    const promise = analyzeVideoWithGemini(
      'https://www.youtube.com/watch?v=auJzb1D-fag',
      TEST_EVIDENCE,
    );
    const assertion = expect(promise).rejects.toThrow(/failed after 3 attempts/);
    await vi.advanceTimersByTimeAsync(20_000); // cover 2s + 4s backoffs
    await assertion;
    expect(gatewayChatMock).toHaveBeenCalledTimes(3);
  });
});
