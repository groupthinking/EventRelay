import { describe, expect, it, vi } from 'vitest';

const runActionAgent = vi.fn().mockResolvedValue({
  provider: 'gateway:test',
  actions: [
    {
      tool: 'create_workflow_task',
      status: 'pending',
      result: 'Prepared for review.',
    },
  ],
});

vi.mock('@/lib/action-agent', () => ({ runActionAgent }));
vi.mock('@/lib/transcription-service', () => ({
  fetchTranscript: vi.fn().mockResolvedValue({
    transcript: 'fetched transcript with enough words to pass the evidence gate',
    segments: [{ start: 0, duration: 1, text: 'fetched transcript' }],
    sourceUrl: 'https://www.youtube.com/watch?v=auJzb1D-fag',
    source: 'youtube',
    verified: true,
  }),
}));
vi.mock('@/lib/gemini-video-analyzer', () => ({
  analyzeVideoWithGemini: vi.fn().mockResolvedValue({
    title: 'Fixture',
    summary: 'Summary',
    transcript: [],
    events: [],
    actions: [],
    topics: [],
    architectureCode: '',
    ingestScript: '',
    e22Snippets: [],
    provenance: {
      sourceUrl: 'https://www.youtube.com/watch?v=auJzb1D-fag',
      sourceHost: 'www.youtube.com',
      acquisitionMethod: 'captions',
      transcriptSource: 'youtube',
      transcriptVerified: true,
      acquiredAt: new Date().toISOString(),
      segmentCount: 1,
      timedSegmentCount: 1,
      durationCoverageSeconds: 1,
      contentSha256: 'hash',
      warnings: [],
    },
    quality: { passed: true, state: 'verified', issues: [] },
  }),
}));
vi.mock('@/lib/gemini-client', () => ({
  getGeminiRoutingLabel: vi.fn().mockResolvedValue('gateway:test'),
}));

describe('videoToActionsWorkflow', () => {
  it('sends same-run transcript and events to the preview action agent', async () => {
    const { videoToActionsWorkflow } = await import('../video-to-actions');
    const transcript = 'provided Analyze transcript with enough words to pass the gate';

    const result = await videoToActionsWorkflow({
      url: 'https://www.youtube.com/watch?v=auJzb1D-fag',
      videoTitle: 'Fixture',
      transcript,
      events: [{ type: 'action', title: 'Ship', description: 'now' }],
    });

    expect(runActionAgent).toHaveBeenCalledWith(
      expect.objectContaining({
        transcript: expect.stringContaining(transcript),
        videoTitle: 'Fixture',
        executeTools: false,
      }),
    );
    expect(result.usedProvidedTranscript).toBe(true);
    expect(result.actions[0]?.tool).toBe('create_workflow_task');
  });
});
