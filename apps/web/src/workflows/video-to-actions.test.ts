import { beforeEach, describe, expect, it, vi } from 'vitest';

const fetchTranscript = vi.fn();
const normalizeTranscriptSegments = vi.fn();
const transcriptTextFromSegments = vi.fn();
const calculateDurationCoverageSeconds = vi.fn();
const assessAnalysisEvidence = vi.fn();
const analyzeVideoWithGemini = vi.fn();
const runActionAgent = vi.fn();

vi.mock('@/lib/transcription-service', () => ({
  fetchTranscript: (...args: unknown[]) => fetchTranscript(...args),
}));

vi.mock('@/lib/analysis-evidence', () => ({
  fatalQualityFailure: () => 'quality failed',
  normalizeTranscriptSegments: (...args: unknown[]) => normalizeTranscriptSegments(...args),
  transcriptTextFromSegments: (...args: unknown[]) => transcriptTextFromSegments(...args),
  calculateDurationCoverageSeconds: (...args: unknown[]) =>
    calculateDurationCoverageSeconds(...args),
  assessAnalysisEvidence: (...args: unknown[]) => assessAnalysisEvidence(...args),
}));

vi.mock('@/lib/gemini-video-analyzer', () => ({
  analyzeVideoWithGemini: (...args: unknown[]) => analyzeVideoWithGemini(...args),
}));

vi.mock('@/lib/action-agent', () => ({
  runActionAgent: (...args: unknown[]) => runActionAgent(...args),
}));

describe('videoToActionsWorkflow', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    normalizeTranscriptSegments.mockImplementation((segments: unknown) =>
      Array.isArray(segments) ? segments : [],
    );
    transcriptTextFromSegments.mockReturnValue('');
    calculateDurationCoverageSeconds.mockReturnValue(8);
    assessAnalysisEvidence.mockReturnValue({ passed: true, issues: [] });
    analyzeVideoWithGemini.mockResolvedValue({
      title: 'Fixture',
      summary: 'ok',
      transcript: [],
      events: [],
      actions: [],
      topics: [],
      architectureCode: '',
      ingestScript: '',
      e22Snippets: [],
      quality: {
        state: 'verified',
        passed: true,
        issues: [],
      },
      provenance: {
        sourceUrl: 'https://www.youtube.com/watch?v=auJzb1D-fag',
        sourceHost: 'www.youtube.com',
        acquisitionMethod: 'captions',
        transcriptSource: 'youtube',
        transcriptVerified: true,
        acquiredAt: '2026-01-01T00:00:00.000Z',
        segmentCount: 1,
        timedSegmentCount: 1,
        durationCoverageSeconds: 8,
        contentSha256: 'abc123',
        warnings: [],
      },
    });
    runActionAgent.mockResolvedValue({
      provider: 'gateway:test',
      actions: [{ tool: 'dispatch_agent', status: 'pending', result: 'Ship the thing' }],
    });
    fetchTranscript.mockResolvedValue({
      success: true,
      transcript:
        'This transcript is long enough to pass the quality gate and feed the action agent.',
      segments: [
        {
          start: 0,
          duration: 8,
          text: 'This transcript is long enough to pass the quality gate and feed the action agent.',
        },
      ],
      source: 'youtube',
      sourceUrl: 'https://www.youtube.com/watch?v=auJzb1D-fag',
      acquisitionMethod: 'captions',
      verified: true,
      acquiredAt: '2026-01-01T00:00:00.000Z',
    });
  });

  it('runs the action agent in the durable workflow using transcript + events context', async () => {
    const { videoToActionsWorkflow } = await import('./video-to-actions');
    const result = await videoToActionsWorkflow({
      url: 'https://www.youtube.com/watch?v=auJzb1D-fag',
      videoTitle: 'Fixture video',
      events: [{ type: 'action', title: 'Ship', description: 'now' }],
    });

    expect(runActionAgent).toHaveBeenCalledTimes(1);
    expect(runActionAgent).toHaveBeenCalledWith(
      expect.objectContaining({
        videoTitle: 'Fixture video',
        executeTools: false,
      }),
    );
    expect(String(runActionAgent.mock.calls[0]?.[0]?.transcript)).toContain('EVENTS FROM ANALYZE');
    expect(result.provider).toBe('gateway:test');
    expect(result.actionCount).toBe(1);
    expect(result.actions).toEqual([
      { tool: 'dispatch_agent', status: 'pending', result: 'Ship the thing' },
    ]);
  });
});
