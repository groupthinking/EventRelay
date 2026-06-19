import { describe, it, expect, afterEach, vi } from 'vitest';

vi.mock('@/lib/cloudevents', () => ({
  publishEvent: vi.fn().mockResolvedValue(undefined),
  EventTypes: new Proxy({}, { get: (_target, prop) => String(prop) }),
}));

vi.mock('@/lib/gemini-video-analyzer', () => ({
  analyzeVideoWithGemini: vi.fn(),
}));

vi.mock('@/lib/gemini-client', () => ({
  hasGeminiKey: vi.fn(() => false),
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

  it('returns a partial fallback handoff when automatic execution is unavailable', async () => {
    const res = await POST(postRequest({
      url: 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
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
