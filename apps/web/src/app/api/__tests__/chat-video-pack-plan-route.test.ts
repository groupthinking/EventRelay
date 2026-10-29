import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const { generateText } = vi.hoisted(() => ({ generateText: vi.fn() }));
const { grokChatCompletion } = vi.hoisted(() => ({ grokChatCompletion: vi.fn() }));
vi.mock('ai', () => ({ generateText }));
vi.mock('@/lib/ai-gateway', () => ({
  aiGateway: vi.fn((model: string) => model),
  GATEWAY_CHAT_MODEL: 'openai/gpt-4o',
}));
vi.mock('@/lib/billing/grok-client', () => ({ grokChatCompletion }));

import { POST } from '@/app/api/chat/route';
import { resetEntitlementStoreForTests } from '@/lib/billing/entitlement-store';
import { resetChatQuotaForTests } from '@/lib/billing/chat-quota';
import { buildIdentityPack } from '@/lib/video-pack';
import { QJ_TRANSCRIPT, QJ_VIDEO_ID } from '@/lib/__fixtures__/qj-z5ohr7sga-emit';
import * as store from '@/lib/video-pack-store';

const packId = `vp:v0:${QJ_VIDEO_ID}`;
const interview = {
  useCase: 'A tire-change safety checklist from the video',
  trigger: 'User detects a flat tire',
  tools: ['Target repository', 'Test runner'],
  constraints: 'Do not invent safety instructions',
  successSignal: 'The checklist follows source-backed steps',
};

function request(body: Record<string, unknown>): Request {
  return new Request('http://localhost/api/chat', {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(body),
  });
}

describe('POST /api/chat Video Pack plan', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    process.env.AI_GATEWAY_API_KEY = 'vck_test';
    resetEntitlementStoreForTests();
    resetChatQuotaForTests();
    generateText.mockResolvedValue({ text: 'gateway reply' });
  });

  afterEach(() => {
    delete process.env.AI_GATEWAY_API_KEY;
    vi.restoreAllMocks();
    vi.clearAllMocks();
  });

  function readyPack() {
    const pack = buildIdentityPack(QJ_VIDEO_ID);
    pack.transcript = QJ_TRANSCRIPT;
    pack.requirements = [{ id: 'REQ-01', title: 'Park on level ground', detail: 'Set the parking brake' }];
    vi.spyOn(store, 'getPackRecordWithMeta').mockResolvedValue({
      outcome: 'hit',
      record: { state: 'ready', pack },
      store: { backend: 'memory', ok: true },
    });
  }

  it('asks for a use case on the ready, matching hosted pack before planning', async () => {
    readyPack();
    const response = await POST(request({
      query: 'Plan a build from this Video Pack',
      video_id: QJ_VIDEO_ID,
      pack_id: packId,
    }));
    const body = await response.json();

    expect(response.status).toBe(200);
    expect(body.requiresInterview).toBe(true);
    expect(body.interviewQuestions).toHaveLength(5);
    expect(body.interviewQuestions[0]).toContain('deliverable');
    expect(generateText).not.toHaveBeenCalled();
    expect(grokChatCompletion).not.toHaveBeenCalled();
  });

  it('uses interview answers and pack excerpts in the second turn', async () => {
    readyPack();
    const response = await POST(request({
      query: 'Here are my answers',
      planIntent: true,
      planInterview: interview,
      video_id: QJ_VIDEO_ID,
      pack_id: packId,
    }));
    const body = await response.json();

    expect(response.status).toBe(200);
    expect(body.requiresInterview).toBe(false);
    expect(body.provider).toBe('video-pack-planner');
    expect(body.answer).toContain(packId);
    expect(body.answer).toContain('Park on level ground');
    expect(body.answer).toContain('Frontend: No explicit evidence');
    expect(body.answer).toContain(interview.successSignal);
    expect(body.answer).toContain('No codebase change, test result, or live deployment is claimed');
    expect(generateText).not.toHaveBeenCalled();
  });

  it('requires a Video Pack rather than returning an ungrounded plan', async () => {
    const response = await POST(request({
      query: 'Build me a system for using sparkle pills',
      planInterview: interview,
    }));
    const body = await response.json();

    expect(response.status).toBe(400);
    expect(body.code).toBe('pack_required');
    expect(generateText).not.toHaveBeenCalled();
  });

  it('fails closed when the pack is missing', async () => {
    vi.spyOn(store, 'getPackRecordWithMeta').mockResolvedValue({
      outcome: 'miss',
      store: { backend: 'memory', ok: true },
    });
    const response = await POST(request({
      query: 'Plan a build from this Video Pack',
      video_id: QJ_VIDEO_ID,
      pack_id: packId,
    }));
    const body = await response.json();

    expect(response.status).toBe(404);
    expect(body.code).toBe('pack_not_found');
    expect(generateText).not.toHaveBeenCalled();
  });
});
