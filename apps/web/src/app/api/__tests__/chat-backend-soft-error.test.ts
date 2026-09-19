import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const { generateText, aiGateway } = vi.hoisted(() => ({
  generateText: vi.fn(),
  aiGateway: vi.fn((model: string) => model),
}));

vi.mock('ai', () => ({
  generateText,
}));

vi.mock('@/lib/ai-gateway', () => ({
  aiGateway,
  GATEWAY_CHAT_MODEL: 'openai/gpt-4o',
}));

vi.mock('@/lib/billing/grok-client', () => ({
  grokChatCompletion: vi.fn(),
}));

import { looksLikeBackendProviderSoftError, POST } from '@/app/api/chat/route';
import { resetChatQuotaForTests } from '@/lib/billing/chat-quota';
import { resetEntitlementStoreForTests } from '@/lib/billing/entitlement-store';

describe('looksLikeBackendProviderSoftError', () => {
  it('detects Vertex publisher model 404 copy', () => {
    expect(
      looksLikeBackendProviderSoftError(
        'Publisher Model `projects/foo/locations/us-central1/publishers/google/models/gemini-3.5-flash` was not found',
      ),
    ).toBe(true);
  });

  it('does not flag normal answers', () => {
    expect(looksLikeBackendProviderSoftError('Use a jack and lug wrench.')).toBe(false);
  });
});

describe('POST /api/chat backend soft-error fallback', () => {
  beforeEach(() => {
    process.env.AI_GATEWAY_API_KEY = 'vck_test';
    process.env.BACKEND_URL = 'https://backend.example.test';
    resetEntitlementStoreForTests();
    resetChatQuotaForTests();
    generateText.mockResolvedValue({ text: 'gateway fallback reply' });
  });

  afterEach(() => {
    delete process.env.AI_GATEWAY_API_KEY;
    delete process.env.BACKEND_URL;
    vi.unstubAllGlobals();
    vi.clearAllMocks();
  });

  it('falls through to gateway when backend returns a provider soft-error body', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({
          response:
            'Publisher Model `gemini-3.5-flash` was not found for API version',
        }),
      }),
    );

    const request = new Request('http://localhost/api/chat', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ query: 'Summarize the video' }),
    });

    const response = await POST(request);
    const body = await response.json();

    expect(response.status).toBe(200);
    expect(body.answer).toBe('gateway fallback reply');
    expect(body.provider).toBe('vercel-ai-gateway');
    expect(generateText).toHaveBeenCalled();
  });
});
