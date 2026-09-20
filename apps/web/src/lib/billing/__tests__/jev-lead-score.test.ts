import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const { experimental_evaluate, evaluationModel } = vi.hoisted(() => ({
  experimental_evaluate: vi.fn(),
  evaluationModel: vi.fn((modelId: string) => `evaluation:${modelId}`),
}));

vi.mock('ai', () => ({
  experimental_evaluate,
}));

vi.mock('@/lib/ai-gateway', () => ({
  aiGateway: {
    evaluationModel,
  },
}));

const { hasAiGatewayKey } = vi.hoisted(() => ({
  hasAiGatewayKey: vi.fn(),
}));

vi.mock('@/lib/vercel-ai-gateway', () => ({
  hasAiGatewayKey,
}));

import {
  mapJevEvaluateResultToLeadScore,
  scoreLeadWithJev,
} from '@/lib/billing/jev-lead-score';

beforeEach(() => {
  hasAiGatewayKey.mockReset();
  experimental_evaluate.mockReset();
  evaluationModel.mockClear();
});

afterEach(() => {
  vi.clearAllMocks();
});

describe('mapJevEvaluateResultToLeadScore', () => {
  it('maps a Choice answer into JevLeadScore fields', () => {
    expect(
      mapJevEvaluateResultToLeadScore(
        {
          answers: {
            lead_decision: {
              type: 'choice',
              choice: 'action_items',
              probabilities: { action_items: 0.87, clarification: 0.13 },
            },
          },
          providerMetadata: {
            typesafe: { confidence: 0.87 },
          },
          response: { modelId: 'typesafe-ai/jev' },
        },
        'typesafe-ai/jev',
      ),
    ).toEqual({
      model: 'typesafe-ai/jev',
      decision: 'action_items',
      confidence: 0.87,
      probabilities: {
        action_items: 0.87,
        clarification: 0.13,
      },
      rationale: '',
    });
  });

  it('rejects unknown choice keys', () => {
    expect(
      mapJevEvaluateResultToLeadScore(
        {
          answers: {
            lead_decision: {
              type: 'choice',
              choice: 'unsupported',
              probabilities: { unsupported: 1 },
            },
          },
        },
        'typesafe-ai/jev',
      ),
    ).toBeNull();
  });

  it('falls back to selected-option probability when typesafe confidence is missing', () => {
    expect(
      mapJevEvaluateResultToLeadScore(
        {
          answers: {
            lead_decision: {
              type: 'choice',
              choice: 'clarification',
              probabilities: { action_items: 0.34, clarification: 0.66 },
            },
          },
        },
        'typesafe-ai/jev',
      ),
    ).toEqual({
      model: 'typesafe-ai/jev',
      decision: 'clarification',
      confidence: 0.66,
      probabilities: {
        action_items: 0.34,
        clarification: 0.66,
      },
      rationale: '',
    });
  });
});

describe('scoreLeadWithJev', () => {
  it('returns null when AI Gateway key is unavailable', async () => {
    hasAiGatewayKey.mockReturnValue(false);
    await expect(
      scoreLeadWithJev({ query: 'Need next steps', history: [] }),
    ).resolves.toBeNull();
    expect(experimental_evaluate).not.toHaveBeenCalled();
  });

  it('calls Gateway evaluate with a typed Choice question', async () => {
    hasAiGatewayKey.mockReturnValue(true);
    experimental_evaluate.mockResolvedValue({
      answers: {
        lead_decision: {
          type: 'choice',
          choice: 'clarification',
          probabilities: { action_items: 0.34, clarification: 0.66 },
        },
      },
      providerMetadata: { typesafe: { confidence: 0.66 } },
      response: { modelId: 'typesafe-ai/jev' },
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
      rationale: '',
    });

    expect(evaluationModel).toHaveBeenCalledWith('typesafe-ai/jev');
    expect(experimental_evaluate).toHaveBeenCalledWith(
      expect.objectContaining({
        model: 'evaluation:typesafe-ai/jev',
        questions: expect.objectContaining({
          lead_decision: expect.objectContaining({ type: 'choice' }),
        }),
        abortSignal: expect.any(AbortSignal),
      }),
    );
  });

  it('returns null when evaluate throws', async () => {
    hasAiGatewayKey.mockReturnValue(true);
    experimental_evaluate.mockRejectedValue(new Error('gateway_down'));

    await expect(
      scoreLeadWithJev({ query: 'Need next steps', history: [] }),
    ).resolves.toBeNull();
  });
});
