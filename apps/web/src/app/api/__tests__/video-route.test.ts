import { describe, it, expect, afterEach, vi } from 'vitest';

// The route pulls in event publishing, Gemini analysis, and a training store
// at import time. Stub them so the handler logic can be tested in isolation.
vi.mock('@/lib/cloudevents', () => ({
  publishEvent: vi.fn().mockResolvedValue(undefined),
  EventTypes: new Proxy({}, { get: (_t, prop) => String(prop) }),
}));
vi.mock('@/lib/gemini-video-analyzer', () => ({
  analyzeVideoWithGemini: vi.fn(),
}));
vi.mock('@/lib/gemini-client', () => ({
  hasGeminiKey: vi.fn(() => false),
}));
vi.mock('@/lib/training-store', () => ({
  saveTrainingExample: vi.fn().mockResolvedValue(undefined),
}));

import { GET, POST } from '@/app/api/video/route';

function postRequest(body: unknown) {
  return new Request('http://localhost:3000/api/video', {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(body),
  });
}

afterEach(() => {
  vi.clearAllMocks();
  vi.unstubAllGlobals();
});

describe('POST /api/video', () => {
  it('returns 400 when no url is provided', async () => {
    const res = await POST(postRequest({}));
    expect(res.status).toBe(400);
    const body = await res.json();
    expect(body.error).toBe('Video URL is required');
  });

  it('reports failure honestly when every transcript strategy comes up empty', async () => {
    // No backend (BACKEND_URL='' in vitest config) and no Gemini key, so the
    // handler falls to the frontend chain; /api/transcribe yields nothing.
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => ({ success: false }),
        text: async () => '{}',
      } as unknown as Response),
    );
    const res = await POST(postRequest({ url: 'https://youtu.be/x' }));
    const body = await res.json();
    expect(body.status).toBe('failed');
    expect(body.result.success).toBe(false);
    expect(body.result.agents_used).toContain('frontend-pipeline');
  });
});

describe('GET /api/video', () => {
  it('reports frontend-only mode when no backend is configured', async () => {
    const res = await GET();
    const body = await res.json();
    expect(body.backend_status).toBe('not-configured');
    expect(body.frontend_pipeline).toBe('active');
  });
});
