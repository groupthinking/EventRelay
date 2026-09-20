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

import { POST } from '@/app/api/chat/route';
import { resetChatQuotaForTests } from '@/lib/billing/chat-quota';
import { resetEntitlementStoreForTests } from '@/lib/billing/entitlement-store';
import { buildIdentityPack } from '@/lib/video-pack';
import { QJ_TRANSCRIPT, QJ_VIDEO_ID } from '@/lib/__fixtures__/qj-z5ohr7sga-emit';
import * as store from '@/lib/video-pack-store';

describe('POST /api/chat pack grounding (#2122)', () => {
  beforeEach(() => {
    process.env.AI_GATEWAY_API_KEY = 'vck_test';
    resetEntitlementStoreForTests();
    resetChatQuotaForTests();
    generateText.mockResolvedValue({ text: 'grounded reply' });
    vi.restoreAllMocks();
  });

  afterEach(() => {
    delete process.env.AI_GATEWAY_API_KEY;
    delete process.env.BACKEND_URL;
    vi.unstubAllGlobals();
    vi.clearAllMocks();
  });

  it('allows anonymous requests and injects pack system context', async () => {
    process.env.BACKEND_URL = 'https://backend.example.test';
    const backendFetch = vi.fn();
    vi.stubGlobal('fetch', backendFetch);

    const pack = buildIdentityPack(QJ_VIDEO_ID);
    pack.transcript = QJ_TRANSCRIPT;
    pack.id = `vp:v0:${QJ_VIDEO_ID}`;
    vi.spyOn(store, 'getPackRecordWithMeta').mockResolvedValue({
      outcome: 'hit',
      record: { state: 'ready', pack },
      store: { backend: 'memory', ok: true },
    });

    const request = new Request('http://localhost/api/chat', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({
        query: 'What tools are mentioned?',
        video_id: QJ_VIDEO_ID,
        pack_id: `vp:v0:${QJ_VIDEO_ID}`,
      }),
    });

    const response = await POST(request);
    const body = await response.json();

    expect(response.status).toBe(200);
    expect(body.answer).toBe('grounded reply');
    expect(body.provider).toBe('vercel-ai-gateway');
    expect(backendFetch).not.toHaveBeenCalled();
    expect(generateText).toHaveBeenCalledWith(
      expect.objectContaining({
        instructions: expect.stringContaining(`packId: vp:v0:${QJ_VIDEO_ID}`),
        messages: [
          { role: 'user', content: 'What tools are mentioned?' },
        ],
      }),
    );
    const gatewayArgs = generateText.mock.calls[0]?.[0] as {
      messages?: { role: string }[];
    };
    expect(gatewayArgs.messages?.some((m) => m.role === 'system')).toBe(false);
  });

  it('fails closed when pack is missing', async () => {
    vi.spyOn(store, 'getPackRecordWithMeta').mockResolvedValue({
      outcome: 'miss',
      store: { backend: 'memory', ok: true },
    });

    const request = new Request('http://localhost/api/chat', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({
        query: 'Hello',
        video_id: QJ_VIDEO_ID,
      }),
    });

    const response = await POST(request);
    const body = await response.json();

    expect(response.status).toBe(404);
    expect(body.code).toBe('pack_not_found');
    expect(generateText).not.toHaveBeenCalled();
  });

  it('fails closed on pack_id mismatch', async () => {
    const request = new Request('http://localhost/api/chat', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({
        query: 'Hello',
        video_id: QJ_VIDEO_ID,
        pack_id: 'vp:v0:wrongVideoId1',
      }),
    });

    const response = await POST(request);
    const body = await response.json();

    expect(response.status).toBe(400);
    expect(body.code).toBe('pack_binding_invalid');
  });
});
