import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const { gatewayChat, hasAiGatewayKey } = vi.hoisted(() => ({
  gatewayChat: vi.fn(),
  hasAiGatewayKey: vi.fn(),
}));

vi.mock('@/lib/vercel-ai-gateway', () => ({
  gatewayChat,
  hasAiGatewayKey,
  stripJsonCodeFence: (value: string) => value.replace(/^```json\n/u, '').replace(/\n```$/u, ''),
}));

import { parseJevLeadScore, scoreLeadWithJev } from '@/lib/billing/jev-lead-score';

beforeEach(() => {
  hasAiGatewayKey.mockReset();
  gatewayChat.mockReset();
});

afterEach(() => {
  vi.clearAllMocks();
});

describe('parseJevLeadScore', () => {
  it('parses a valid Jev response payload', () => {
    expect(
      parseJevLeadScore(
        JSON.stringify({
          decision: 'action_items',
          confidence: 0.87,
          probabilities: {
            action_items: 0.87,
            clarification: 0.13,
          },
          rationale: 'The user asks for direct execution steps.',
        }),
      ),
    ).toEqual({
      decision: 'action_items',
      confidence: 0.87,
      probabilities: {
        action_items: 0.87,
        clarification: 0.13,
      },
      rationale: 'The user asks for direct execution steps.',
    });
  });

  it('rejects unknown decisions', () => {
    expect(
      parseJevLeadScore(
        JSON.stringify({
          decision: 'unsupported',
          confidence: 0.5,
          probabilities: { action_items: 0.5, clarification: 0.5 },
          rationale: 'n/a',
        }),
      ),
    ).toBeNull();
  });
});

describe('scoreLeadWithJev', () => {
  it('returns null when AI Gateway key is unavailable', async () => {
    hasAiGatewayKey.mockReturnValue(false);
    await expect(
      scoreLeadWithJev({ query: 'Need next steps', history: [] }),
    ).resolves.toBeNull();
    expect(gatewayChat).not.toHaveBeenCalled();
  });

  it('returns a normalized score when Jev responds with valid JSON', async () => {
    hasAiGatewayKey.mockReturnValue(true);
    gatewayChat.mockResolvedValue({
      model: 'typesafe-ai/jev',
      content: JSON.stringify({
        decision: 'clarification',
        confidence: 0.66,
        probabilities: { action_items: 0.34, clarification: 0.66 },
        rationale: 'The request is ambiguous and needs constraints.',
      }),
    });

    await expect(
      scoreLeadWithJev({
        query: 'Can you help with this?',
        history: [{ role: 'user', content: 'I have a vague requirement.' }],
      }),
    ).resolves.toEqual({
      model: 'typesafe-ai/jev',
      provider: 'vercel-ai-gateway',
      decision: 'clarification',
      confidence: 0.66,
      probabilities: { action_items: 0.34, clarification: 0.66 },
      rationale: 'The request is ambiguous and needs constraints.',
    });
  });
});
