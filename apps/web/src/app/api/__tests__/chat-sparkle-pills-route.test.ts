import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const { generateText, aiGateway } = vi.hoisted(() => ({
  generateText: vi.fn(),
  aiGateway: vi.fn((model: string) => model),
}));

const { grokChatCompletion } = vi.hoisted(() => ({
  grokChatCompletion: vi.fn(),
}));

vi.mock('ai', () => ({
  generateText,
}));

vi.mock('@/lib/ai-gateway', () => ({
  aiGateway,
  GATEWAY_CHAT_MODEL: 'openai/gpt-4o',
}));

vi.mock('@/lib/billing/grok-client', () => ({
  grokChatCompletion,
}));

import { POST } from '@/app/api/chat/route';
import { resetEntitlementStoreForTests } from '@/lib/billing/entitlement-store';
import { resetChatQuotaForTests } from '@/lib/billing/chat-quota';
import { buildIdentityPack } from '@/lib/video-pack';
import { QJ_TRANSCRIPT, QJ_VIDEO_ID } from '@/lib/__fixtures__/qj-z5ohr7sga-emit';
import * as store from '@/lib/video-pack-store';

describe('POST /api/chat sparkle pills interview-first flow', () => {
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

  it('asks clarifying interview questions before producing a sparkle-pill system plan', async () => {
    const request = new Request('http://localhost/api/chat', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({
        query: 'Build me a system for using sparkle pills',
      }),
    });

    const response = await POST(request);
    const body = await response.json();

    expect(response.status).toBe(200);
    expect(body.requiresInterview).toBe(true);
    expect(body.interviewQuestions).toEqual(expect.arrayContaining([expect.any(String)]));
    expect(body.answer).toContain('Before I design the system');
    expect(generateText).not.toHaveBeenCalled();
    expect(grokChatCompletion).not.toHaveBeenCalled();
  });

  it('returns a concrete sparkle-pill workflow after interview answers are provided', async () => {
    const request = new Request('http://localhost/api/chat', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({
        query: 'Build me a system for using sparkle pills',
        sparkleInterview: {
          useCase: 'I need to manage daily focus sessions across work and school.',
          trigger: 'Start each weekday at 08:30',
          tools: ['Google Calendar', 'Slack'],
          constraints: 'No notifications after 21:00',
          successSignal: '5 sessions completed per week',
        },
      }),
    });

    const response = await POST(request);
    const body = await response.json();

    expect(response.status).toBe(200);
    expect(body.requiresInterview).toBe(false);
    expect(body.provider).toBe('sparkle-pills-planner');
    expect(body.answer).toContain('Sparkle Pills System Plan');
    expect(body.answer).toContain('Start each weekday at 08:30');
    expect(body.answer).toContain('5 sessions completed per week');
    expect(generateText).not.toHaveBeenCalled();
    expect(grokChatCompletion).not.toHaveBeenCalled();
  });

  it('keeps pack-bound sparkle requests on grounded chat instead of deterministic planner', async () => {
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
        query: 'Build me a system for using sparkle pills',
        video_id: QJ_VIDEO_ID,
        pack_id: `vp:v0:${QJ_VIDEO_ID}`,
        sparkleInterview: {
          useCase: 'Weekday focus sessions',
          trigger: 'Weekdays at 08:30',
          tools: ['Calendar', 'Slack'],
          constraints: 'No messages after 21:00',
          successSignal: '5 sessions weekly',
        },
      }),
    });

    const response = await POST(request);
    const body = await response.json();

    expect(response.status).toBe(200);
    expect(body.provider).toBe('vercel-ai-gateway');
    expect(body.requiresInterview).toBeUndefined();
    expect(body.answer).toBe('gateway reply');
    expect(generateText).toHaveBeenCalledTimes(1);
  });

  it('keeps pack-bound sparkle requests fail-closed when no ready pack exists', async () => {
    vi.spyOn(store, 'getPackRecordWithMeta').mockResolvedValue({
      outcome: 'miss',
      store: { backend: 'memory', ok: true },
    });

    const request = new Request('http://localhost/api/chat', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({
        query: 'Build me a system for using sparkle pills',
        video_id: QJ_VIDEO_ID,
        pack_id: `vp:v0:${QJ_VIDEO_ID}`,
      }),
    });

    const response = await POST(request);
    const body = await response.json();

    expect(response.status).toBe(404);
    expect(body.code).toBe('pack_not_found');
    expect(generateText).not.toHaveBeenCalled();
  });

  it('continues sparkle interview without repeating sparkle phrase by using sparkleIntent', async () => {
    const request = new Request('http://localhost/api/chat', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({
        query: 'Use case: automate weekday focus sessions.',
        sparkleIntent: true,
        sparkleInterview: {
          useCase: 'weekday focus sessions',
        },
      }),
    });

    const response = await POST(request);
    const body = await response.json();

    expect(response.status).toBe(200);
    expect(body.requiresInterview).toBe(true);
    expect(body.interviewQuestions).toEqual(expect.arrayContaining([expect.any(String)]));
    expect(generateText).not.toHaveBeenCalled();
  });
});
