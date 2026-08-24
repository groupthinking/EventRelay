import { describe, it, expect, afterEach, vi } from 'vitest';

vi.mock('@/lib/cloudevents', () => ({
  publishEvent: vi.fn().mockResolvedValue(undefined),
  EventTypes: new Proxy({}, { get: (_target, prop) => String(prop) }),
}));

vi.mock('@/lib/gemini-video-analyzer', () => ({
  analyzeVideoWithGemini: vi.fn(),
}));

vi.mock('@/lib/transcription-service', () => ({
  fetchTranscript: vi.fn(),
}));

vi.mock('@/lib/gemini-client', () => ({
  hasGeminiKey: vi.fn(() => false),
  getGeminiConfig: vi.fn(() => ({ configured: false, mode: 'none' })),
  classifyGeminiError: vi.fn((error: unknown) => ({
    code: 'GEMINI_ERROR',
    message: error instanceof Error ? error.message : String(error),
    userMessage: 'Gemini video analysis failed.',
  })),
}));

vi.mock('@/lib/pipeline-backend-health', () => ({
  PIPELINE_HEALTH_TIMEOUT_MS: 5_000,
  getBackendConfig: vi.fn(() => ({ configured: false, url: '' })),
  checkBackendHealth: vi.fn(async () => ({
    configured: false,
    available: false,
    host: null,
    reason: 'BACKEND_URL is not configured',
  })),
  parseBackendJson: vi.fn(),
}));

import {
  POST,
  MAX_DURATION_MS,
  PIPELINE_BACKEND_TIMEOUT_MS,
  PIPELINE_GEMINI_TIMEOUT_MS,
  PIPELINE_HEALTH_TIMEOUT_MS,
  PipelineDeadline,
  maxDuration,
} from '@/app/api/pipeline/route';

function postRequest(body: unknown) {
  return new Request('http://localhost:3000/api/pipeline', {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(body),
  });
}

afterEach(() => {
  vi.clearAllMocks();
  vi.unstubAllGlobals();
});

describe('pipeline timeouts', () => {
  it('clamps sequential fallback steps to the shared maxDuration budget', () => {
    expect(MAX_DURATION_MS).toBe(maxDuration * 1000);
    expect(PIPELINE_HEALTH_TIMEOUT_MS).toBeGreaterThanOrEqual(5_000);

    expect(PIPELINE_BACKEND_TIMEOUT_MS).toBeLessThanOrEqual(MAX_DURATION_MS);
    expect(PIPELINE_GEMINI_TIMEOUT_MS).toBeLessThanOrEqual(MAX_DURATION_MS);

    const deadline = PipelineDeadline.fromMaxDuration();
    expect(deadline.budgetMs(PIPELINE_BACKEND_TIMEOUT_MS)).toBeGreaterThan(0);
  });
});

describe('POST /api/pipeline', () => {
  it('returns 400 when no video url is provided', async () => {
    const res = await POST(postRequest({}));
    expect(res.status).toBe(400);
    const body = await res.json();
    expect(body.error).toBe('Video URL is required');
  });

  it('falls through to Gemini when async backend kickoff returns HTML/503', async () => {
    const { getBackendConfig, checkBackendHealth, parseBackendJson } = await import(
      '@/lib/pipeline-backend-health'
    );
    const { hasGeminiKey } = await import('@/lib/gemini-client');
    const { analyzeVideoWithGemini } = await import('@/lib/gemini-video-analyzer');

    vi.mocked(getBackendConfig).mockReturnValue({
      configured: true,
      url: 'https://api.uvai.io',
    });
    vi.mocked(checkBackendHealth).mockResolvedValue({
      configured: true,
      available: true,
      host: 'api.uvai.io',
      source: 'BACKEND_URL',
    });
    vi.mocked(hasGeminiKey).mockReturnValue(true);
    vi.mocked(analyzeVideoWithGemini).mockResolvedValue({
      title: 'Test video',
      summary: 'Gemini fallback analysis',
      events: [],
      actions: [],
      topics: ['test'],
      architectureCode: 'ingest -> analyze',
      ingestScript: 'print("ingest")',
      e22Snippets: [],
      transcript: [],
    } as Awaited<ReturnType<typeof analyzeVideoWithGemini>>);

    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: false,
        status: 503,
        text: async () => '<html>503</html>',
      }),
    );
    vi.mocked(parseBackendJson).mockResolvedValue(null);

    const res = await POST(postRequest({
      url: 'https://www.youtube.com/watch?v=auJzb1D-fag',
      async: true,
    }));
    const body = await res.json();

    expect(res.status).toBe(200);
    expect(body.pipeline).toBe('gemini-only');
    expect(body.status).toBe('partial');
    expect(body.result.video_analysis.summary).toBe('Gemini fallback analysis');
  });

  it('returns transcript-only when Gemini fails but transcript fetch succeeds', async () => {
    const { checkBackendHealth } = await import('@/lib/pipeline-backend-health');
    const { hasGeminiKey, classifyGeminiError } = await import('@/lib/gemini-client');
    const { analyzeVideoWithGemini } = await import('@/lib/gemini-video-analyzer');
    const { fetchTranscript } = await import('@/lib/transcription-service');

    vi.mocked(checkBackendHealth).mockResolvedValue({
      configured: true,
      available: false,
      host: 'api.uvai.io',
      source: 'BACKEND_URL',
      reason: 'Backend health returned 503',
    });
    vi.mocked(hasGeminiKey).mockReturnValue(true);
    vi.mocked(analyzeVideoWithGemini).mockRejectedValue(
      new Error('403 BILLING_DISABLED for aiplatform.googleapis.com'),
    );
    vi.mocked(classifyGeminiError).mockReturnValue({
      code: 'BILLING_DISABLED',
      message: '403 BILLING_DISABLED',
      userMessage: 'Enable GCP billing or set GEMINI_API_KEY.',
    });
    vi.mocked(fetchTranscript).mockResolvedValue({
      success: true,
      transcript: 'Hello world from the video transcript.',
      source: 'openai-web-search',
      wordCount: 7,
    });

    const res = await POST(postRequest({
      url: 'https://www.youtube.com/watch?v=auJzb1D-fag',
      async: false,
    }));
    const body = await res.json();

    expect(res.status).toBe(200);
    expect(body.pipeline).toBe('transcript-only');
    expect(body.gemini_error?.code).toBe('BILLING_DISABLED');
    expect(body.result.video_analysis.transcript_preview).toContain('Hello world');
  });

  it('returns a partial fallback handoff when automatic execution is unavailable', async () => {
    const { checkBackendHealth } = await import('@/lib/pipeline-backend-health');
    const { hasGeminiKey } = await import('@/lib/gemini-client');
    vi.mocked(checkBackendHealth).mockResolvedValue({
      configured: false,
      available: false,
      host: null,
      source: null,
      reason: 'No backend URL configured',
    });
    vi.mocked(hasGeminiKey).mockReturnValue(false);

    const res = await POST(postRequest({
      url: 'https://www.youtube.com/watch?v=auJzb1D-fag',
      project_type: 'automation',
      deployment_target: 'vercel',
    }));
    const body = await res.json();

    expect(res.status).toBe(200);
    expect(body.status).toBe('partial');
    expect(body.pipeline).toBe('local-fallback');
    expect(body.degraded).toBe(true);
    expect(body.backend.configured).toBe(false);
    expect(body.result.build_status).toBe('handoff_ready_backend_unavailable');
    expect(body.result.deployment.status).toBe('blocked_by_configuration');
  });
});
