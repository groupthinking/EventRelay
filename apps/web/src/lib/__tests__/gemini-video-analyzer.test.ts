import { describe, it, expect, afterEach, vi } from 'vitest';

const { gatewayChatMock, fetchTranscriptMock } = vi.hoisted(() => ({
  gatewayChatMock: vi.fn(),
  fetchTranscriptMock: vi.fn(async () => ({ success: false, error: 'unavailable in tests' })),
}));

vi.mock('@/lib/vercel-ai-gateway', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/lib/vercel-ai-gateway')>();
  return {
    ...actual,
    hasAiGatewayKey: () => true,
    gatewayChat: gatewayChatMock,
  };
});

vi.mock('@/lib/transcription-service', () => ({
  fetchTranscript: fetchTranscriptMock,
}));

import {
  AnalysisParseError,
  analyzeVideoWithGemini,
  buildTranscriptOnlyAnalysis,
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

afterEach(() => {
  gatewayChatMock.mockReset();
  fetchTranscriptMock.mockReset();
  fetchTranscriptMock.mockResolvedValue({ success: false, error: 'unavailable in tests' });
  vi.useRealTimers();
});

describe('buildTranscriptOnlyAnalysis', () => {
  it('preserves the exact transcript without inventing structured analysis', () => {
    const transcript = 'one two three four';
    const result = buildTranscriptOnlyAnalysis(transcript);

    expect(result.transcript).toEqual([{ start: 0, duration: 0, text: transcript }]);
    expect(result.summary).toContain('Captured 4 words');
    expect(result.events).toEqual([]);
    expect(result.actions).toEqual([]);
    expect(result.topics).toEqual([]);
    expect(result.architectureCode).toBe('');
    expect(result.ingestScript).toBe('');
    expect(result.e22Snippets).toEqual([]);
  });
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

    const promise = analyzeVideoWithGemini('https://www.youtube.com/watch?v=abc123');
    await vi.advanceTimersByTimeAsync(5_000); // cover the 2s backoff after attempt 1
    const result = await promise;

    expect(result.title).toBe('T');
    expect(gatewayChatMock).toHaveBeenCalledTimes(2);
  });

  it('gives up after max retries of malformed JSON', async () => {
    vi.useFakeTimers();
    gatewayChatMock.mockResolvedValue({ content: 'not json at all' });

    const promise = analyzeVideoWithGemini('https://www.youtube.com/watch?v=abc123');
    const assertion = expect(promise).rejects.toThrow(/failed after 3 attempts/);
    await vi.advanceTimersByTimeAsync(20_000); // cover 2s + 4s backoffs
    await assertion;
    expect(gatewayChatMock).toHaveBeenCalledTimes(3);
  });

  it('returns the captured transcript when structured analysis aborts', async () => {
    const transcript = 'A real transcript that remains useful after structured analysis times out.';
    fetchTranscriptMock.mockResolvedValueOnce({
      success: true,
      transcript,
      wordCount: 10,
      source: 'openai-web-search',
    });
    const abortError = new Error('This operation was aborted');
    abortError.name = 'AbortError';
    gatewayChatMock.mockRejectedValueOnce(abortError);

    const result = await analyzeVideoWithGemini('https://www.youtube.com/watch?v=abc123');

    expect(result.transcript).toEqual([{ start: 0, duration: 0, text: transcript }]);
    expect(result.actions).toEqual([]);
    expect(result.events).toEqual([]);
    expect(gatewayChatMock).toHaveBeenCalledTimes(1);
  });

  it('keeps non-timeout provider failures fail-closed after transcript capture', async () => {
    fetchTranscriptMock.mockResolvedValueOnce({
      success: true,
      transcript: 'A captured transcript.',
      wordCount: 3,
      source: 'youtube',
    });
    gatewayChatMock.mockRejectedValueOnce(new Error('PERMISSION_DENIED'));

    await expect(
      analyzeVideoWithGemini('https://www.youtube.com/watch?v=abc123'),
    ).rejects.toThrow('PERMISSION_DENIED');
  });
});
