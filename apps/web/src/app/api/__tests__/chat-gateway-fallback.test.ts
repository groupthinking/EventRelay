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
  grokChatCompletion: vi.fn().mockResolvedValue({
    answer: 'pro reply',
    model: 'grok-4-1-fast',
    provider: 'xai',
  }),
}));

import { POST } from '@/app/api/chat/route';
import { resetEntitlementStoreForTests } from '@/lib/billing/entitlement-store';
import { resetChatQuotaForTests } from '@/lib/billing/chat-quota';

describe('POST /api/chat AI Gateway fallback', () => {
  beforeEach(() => {
    process.env.AI_GATEWAY_API_KEY = 'vck_test';
    resetEntitlementStoreForTests();
    resetChatQuotaForTests();
    generateText.mockResolvedValue({ text: 'gateway reply' });
  });

  afterEach(() => {
    delete process.env.AI_GATEWAY_API_KEY;
    vi.clearAllMocks();
  });

  it('uses the AI Gateway when BACKEND_URL is unset and preserves history context', async () => {
    const request = new Request('http://localhost/api/chat', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({
        query: 'What happens next?',
        video_url: 'https://www.youtube.com/watch?v=auJzb1D-fag',
        history: [
          { role: 'user', content: 'Summarize the intro.' },
          { role: 'assistant', content: 'It introduces the workflow.' },
        ],
      }),
    });

    const response = await POST(request);
    const body = await response.json();

    expect(response.status).toBe(200);
    expect(body.answer).toBe('gateway reply');
    expect(aiGateway).toHaveBeenCalledWith('openai/gpt-4o');
    expect(generateText).toHaveBeenCalledWith(
      expect.objectContaining({
        messages: [
          { role: 'user', content: 'Summarize the intro.' },
          { role: 'assistant', content: 'It introduces the workflow.' },
          { role: 'user', content: 'What happens next?' },
        ],
      }),
    );
  });
});
