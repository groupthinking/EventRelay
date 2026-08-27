import { describe, expect, it } from 'vitest';
import {
  assessAnalysisEvidence,
  calculateDurationCoverageSeconds,
  fatalQualityFailure,
  hasTranscriptAdvice,
  normalizeTranscriptSegments,
  type AnalysisProvenance,
} from '@/lib/analysis-evidence';

function provenance(overrides: Partial<AnalysisProvenance> = {}): AnalysisProvenance {
  return {
    sourceUrl: 'https://www.youtube.com/watch?v=auJzb1D-fag',
    sourceHost: 'www.youtube.com',
    acquisitionMethod: 'backend-caption-api',
    transcriptSource: 'youtube-captions',
    transcriptVerified: true,
    acquiredAt: '2026-08-16T12:00:00.000Z',
    segmentCount: 1,
    timedSegmentCount: 1,
    durationCoverageSeconds: 12,
    warnings: [],
    ...overrides,
  };
}

describe('analysis evidence gate', () => {
  it('passes a verified timestamped transcript', () => {
    const segments = [{ start: 0, duration: 12, text: 'This is verified source speech with enough content for analysis.' }];
    const result = assessAnalysisEvidence({
      transcript: segments[0].text,
      segments,
      provenance: provenance(),
      now: '2026-08-16T12:01:00.000Z',
    });

    expect(result.passed).toBe(true);
    expect(result.state).toBe('verified');
    expect(result.issues).toEqual([]);
  });

  it('marks a real but untimed transcript degraded, not failed', () => {
    const text = 'This verified speech is long enough to analyze, but source timestamps were unavailable.';
    const result = assessAnalysisEvidence({
      transcript: text,
      segments: [{ start: 0, duration: 0, text }],
      provenance: provenance({ timedSegmentCount: 0, durationCoverageSeconds: null }),
    });

    expect(result.passed).toBe(true);
    expect(result.state).toBe('degraded');
  });

  it('lets usable derived speech through as degraded instead of blocking the page', () => {
    const text = 'The way we interact with AI is changing. Text was only the beginning of how models see the world.';
    const result = assessAnalysisEvidence({
      transcript: text,
      segments: [{ start: 0, duration: 0, text }],
      provenance: provenance({
        transcriptVerified: false,
        transcriptSource: 'gemini-search-metadata',
        acquisitionMethod: 'generative-search-context',
      }),
    });
    expect(result.passed).toBe(true);
    expect(result.state).toBe('degraded');
    expect(fatalQualityFailure(result)).toBeNull();
  });

  it('fails the workflow only when evidence itself did not pass', () => {
    expect(fatalQualityFailure({
      state: 'failed',
      passed: false,
      issues: ['Transcript is empty or too short to support analysis.'],
      transcriptCharacters: 0,
      segmentCount: 0,
      timedSegmentCount: 0,
      checkedAt: '2026-08-27T08:00:00.000Z',
    })).toMatch(/quality gate failed/i);
    expect(fatalQualityFailure(undefined)).toMatch(/missing provenance/);
  });

  it('rejects transcript-retrieval advice even when it is long', () => {
    const text = "I don't have direct access to the transcript. You can obtain it using Transcript.you by pasting the YouTube URL.";
    const result = assessAnalysisEvidence({
      transcript: text,
      segments: [{ start: 0, duration: 0, text }],
      provenance: provenance({ transcriptSource: 'gemini-search', transcriptVerified: false }),
    });

    expect(hasTranscriptAdvice(text)).toBe(true);
    expect(result.passed).toBe(false);
    expect(result.issues.join(' ')).toMatch(/advice/i);
  });

  it('normalizes only non-empty transcript segments', () => {
    expect(normalizeTranscriptSegments([
      { start: '4', duration: '2.5', text: ' hello ' },
      { start: -1, duration: null, text: 'world' },
      { text: '' },
      null,
    ])).toEqual([
      { start: 4, duration: 2.5, text: 'hello' },
      { start: 0, duration: 0, text: 'world' },
    ]);
  });

  it('calculates timed coverage without double-counting overlapping captions', () => {
    expect(calculateDurationCoverageSeconds([
      { start: 0, duration: 5, text: 'a' },
      { start: 3, duration: 4, text: 'b' },
      { start: 10, duration: 2, text: 'c' },
      { start: 20, duration: 0, text: 'untimed' },
    ])).toBe(9);
    expect(calculateDurationCoverageSeconds([{ start: 0, duration: 0, text: 'untimed' }])).toBeNull();
  });
});
