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
  GATEWAY_CHAT_MODEL: 'openai/gpt-4o',
}));

const { hasAiGatewayKey } = vi.hoisted(() => ({
  hasAiGatewayKey: vi.fn(),
}));

vi.mock('@/lib/vercel-ai-gateway', () => ({
  hasAiGatewayKey,
}));

import type { JevEvaluatePayload } from '@/lib/billing/jev-lead-score';
import {
  buildExtractEvaluationState,
  decideExtractNext,
  jevDecisionToShardPlanDecisions,
  mapJevEvaluateResultToExtractDecision,
  planShardsWithJev,
  type JevExtractDecision,
} from '@/lib/video-pack-extract-jev';
import { validateShardManifest } from '@/lib/video-pack-shard-planner';

const SOURCE_URL = 'https://www.youtube.com/watch?v=auJzb1D-fag';

beforeEach(() => {
  hasAiGatewayKey.mockReset();
  experimental_evaluate.mockReset();
  evaluationModel.mockClear();
  hasAiGatewayKey.mockReturnValue(true);
  // Live Jev is opt-in; default it on so the live-path tests exercise evaluate.
  process.env.EXTRACT_JEV_LIVE = '1';
});

afterEach(() => {
  delete process.env.EXTRACT_JEV_LIVE;
});

function choicePayload(choice: string, modelId = 'typesafe-ai/jev'): JevEvaluatePayload {
  return {
    answers: {
      extract_next: {
        type: 'choice',
        choice,
        probabilities: { [choice]: 0.81 },
      },
    },
    providerMetadata: { typesafe: { confidence: 0.81 } },
    response: { modelId },
  };
}

describe('mapJevEvaluateResultToExtractDecision', () => {
  it.each([
    ['chunk'],
    ['model'],
    ['retry'],
    ['consolidate'],
    ['request-more-evidence'],
    ['stop'],
  ] as const)('maps the %s action with confidence and full probabilities', (action) => {
    const mapped = mapJevEvaluateResultToExtractDecision(choicePayload(action), 'typesafe-ai/jev');
    expect(mapped).toMatchObject({ action, confidence: 0.81, model: 'typesafe-ai/jev' });
    expect(mapped?.probabilities[action]).toBe(0.81);
    expect(mapped).not.toHaveProperty('ok');
  });

  it('rejects unknown choices and missing answers', () => {
    expect(mapJevEvaluateResultToExtractDecision(choicePayload('dance'), 'typesafe-ai/jev')).toBeNull();
    expect(
      mapJevEvaluateResultToExtractDecision({ answers: {} }, 'typesafe-ai/jev'),
    ).toBeNull();
  });

  it('falls back to the selected probability without typesafe metadata', () => {
    const mapped = mapJevEvaluateResultToExtractDecision(
      {
        answers: {
          extract_next: { type: 'choice', choice: 'retry', probabilities: { retry: 0.62 } },
        },
      },
      'fallback-model',
    );
    expect(mapped).toMatchObject({ action: 'retry', confidence: 0.62, model: 'fallback-model' });
  });
});

describe('buildExtractEvaluationState', () => {
  it('renders manifest facts, failures, and attempt for the judge', () => {
    const state = buildExtractEvaluationState({
      videoId: 'auJzb1D-fag',
      shardCount: 3,
      durationSeconds: 620,
      costUnits: 620,
      costBoundUnits: 620,
      validationFailures: ['coverage gap of 12s between shard 0 and shard 1'],
      attempt: 2,
    });
    expect(state).toContain('auJzb1D-fag');
    expect(state).toContain('620 / bound 620');
    expect(state).toContain('coverage gap of 12s');
    expect(state).toContain('attempt: 2');
  });
});

describe('decideExtractNext', () => {
  it('skips without calling evaluate when the gateway secret is missing', async () => {
    hasAiGatewayKey.mockReturnValue(false);
    const decision = await decideExtractNext({
      videoId: 'auJzb1D-fag',
      shardCount: 1,
      durationSeconds: 120,
      costUnits: 120,
      costBoundUnits: 120,
      validationFailures: [],
      attempt: 1,
    });
    expect(decision).toBeNull();
    expect(experimental_evaluate).not.toHaveBeenCalled();
  });

  it('skips without the EXTRACT_JEV_LIVE flag even when the gateway key exists', async () => {
    delete process.env.EXTRACT_JEV_LIVE;
    hasAiGatewayKey.mockReturnValue(true);
    const decision = await decideExtractNext({
      videoId: 'auJzb1D-fag',
      shardCount: 1,
      durationSeconds: 120,
      costUnits: 120,
      costBoundUnits: 120,
      validationFailures: [],
      attempt: 1,
    });
    expect(decision).toBeNull();
    expect(experimental_evaluate).not.toHaveBeenCalled();
  });

  it('calls evaluate with the Jev model and maps the decision', async () => {
    experimental_evaluate.mockResolvedValue(choicePayload('consolidate'));
    const decision = await decideExtractNext({
      videoId: 'auJzb1D-fag',
      shardCount: 2,
      durationSeconds: 400,
      costUnits: 400,
      costBoundUnits: 400,
      validationFailures: [],
      attempt: 1,
    });
    expect(experimental_evaluate).toHaveBeenCalledTimes(1);
    const call = experimental_evaluate.mock.calls[0]?.[0] as { model?: string };
    expect(call.model).toBe('evaluation:typesafe-ai/jev');
    expect(decision).toMatchObject({ action: 'consolidate', confidence: 0.81 });
  });

  it('returns null when evaluate throws or the answer is unmapped', async () => {
    experimental_evaluate.mockRejectedValueOnce(new Error('gateway down'));
    const state = {
      videoId: 'auJzb1D-fag',
      shardCount: 1,
      durationSeconds: 120,
      costUnits: 120,
      costBoundUnits: 120,
      validationFailures: [] as string[],
      attempt: 1,
    };
    await expect(decideExtractNext(state)).resolves.toBeNull();
    experimental_evaluate.mockResolvedValueOnce(choicePayload('dance'));
    await expect(decideExtractNext(state)).resolves.toBeNull();
  });
});

describe('jevDecisionToShardPlanDecisions', () => {
  const decision = (action: JevExtractDecision['action']): JevExtractDecision => ({
    action,
    confidence: 0.9,
    probabilities: {
      chunk: 0,
      model: 0,
      retry: 0,
      consolidate: 0,
      'request-more-evidence': 0,
      stop: 0,
      [action]: 0.9,
    },
    rationale: '',
    model: 'typesafe-ai/jev',
  });

  it('returns null for stop (do not plan)', () => {
    expect(jevDecisionToShardPlanDecisions(decision('stop'), { maxWorkers: 4 })).toBeNull();
  });

  it('passes base decisions through for every other action', () => {
    for (const action of ['chunk', 'model', 'retry', 'consolidate', 'request-more-evidence'] as const) {
      expect(jevDecisionToShardPlanDecisions(decision(action), { maxWorkers: 2 })).toEqual({
        maxWorkers: 2,
      });
    }
  });
});

describe('planShardsWithJev', () => {
  it('plans deterministically and skips Jev without the secret', async () => {
    hasAiGatewayKey.mockReturnValue(false);
    const { decision, manifest } = await planShardsWithJev(
      'auJzb1D-fag',
      SOURCE_URL,
      null,
      360,
    );
    expect(decision).toBeNull();
    expect(experimental_evaluate).not.toHaveBeenCalled();
    expect(manifest?.shards).toHaveLength(2);
    expect(manifest && validateShardManifest(manifest).ok).toBe(1);
  });

  it('treats a stop decision as a skip: null decision + deterministic base manifest', async () => {
    experimental_evaluate.mockResolvedValue(choicePayload('stop'));
    const { decision, manifest } = await planShardsWithJev(
      'auJzb1D-fag',
      SOURCE_URL,
      null,
      360,
    );
    // stop no longer aborts: the planner proceeds with the deterministic base.
    expect(decision).toBeNull();
    expect(manifest?.shards).toHaveLength(2);
    expect(manifest && validateShardManifest(manifest).ok).toBe(1);
  });

  it('returns a validator-gated manifest on a chunk decision', async () => {
    experimental_evaluate.mockResolvedValue(choicePayload('chunk'));
    const { decision, manifest } = await planShardsWithJev(
      'auJzb1D-fag',
      SOURCE_URL,
      null,
      360,
    );
    expect(decision?.action).toBe('chunk');
    expect(manifest?.shards).toHaveLength(2);
    // The 0/1 still belongs to the validator — Jev output never implies it.
    expect(manifest && validateShardManifest(manifest)).toEqual({ ok: 1, failures: [] });
    expect(decision).not.toHaveProperty('ok');
  });
});
