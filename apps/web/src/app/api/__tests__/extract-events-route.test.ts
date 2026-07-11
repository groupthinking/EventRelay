import { describe, it, expect, afterEach, beforeEach, vi } from 'vitest';

// The route uses `Type.*` at module load and lazily constructs the OpenAI
// client, so stub both SDKs to keep the test hermetic and offline.
vi.mock('@google/genai', () => ({
  Type: { OBJECT: 'OBJECT', ARRAY: 'ARRAY', STRING: 'STRING', NUMBER: 'NUMBER' },
}));
vi.mock('openai', () => ({
  default: class OpenAI {
    responses = { create: vi.fn() };
  },
}));
vi.mock('@/lib/gemini-client', () => ({
  getGeminiClient: vi.fn(),
  hasGeminiKey: vi.fn(() => false),
}));

import { POST } from '@/app/api/extract-events/route';

function postRequest(body: unknown) {
  return new Request('http://localhost/api/extract-events', {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(body),
  });
}

const ORIGINAL_OPENAI_KEY = process.env.OPENAI_API_KEY;

beforeEach(() => {
  delete process.env.OPENAI_API_KEY;
});

afterEach(() => {
  if (ORIGINAL_OPENAI_KEY === undefined) delete process.env.OPENAI_API_KEY;
  else process.env.OPENAI_API_KEY = ORIGINAL_OPENAI_KEY;
  vi.clearAllMocks();
});

describe('POST /api/extract-events', () => {
  it('returns 400 when neither transcript nor videoUrl is provided', async () => {
    const res = await POST(postRequest({}));
    expect(res.status).toBe(400);
    const body = await res.json();
    expect(body.error).toMatch(/transcript.*videoUrl is required/);
  });

  it('returns success:false with empty data when no AI provider is configured', async () => {
    const res = await POST(postRequest({ transcript: 'a '.repeat(60) }));
    const body = await res.json();
    expect(body.success).toBe(false);
    expect(body.error).toMatch(/No AI API key configured/);
    expect(body.data).toEqual({ events: [], actions: [], summary: '', topics: [] });
  });
});
