import 'server-only';

import { experimental_evaluate as evaluate } from 'ai';
import { aiGateway } from '@/lib/ai-gateway';
import {
  JEV_DEFAULT_MODEL,
  readTypesafeConfidence,
  toProbability,
  type JevEvaluatePayload,
} from '@/lib/billing/jev-lead-score';
import {
  planShardManifest,
  validateShardManifest,
  type ShardManifest,
  type ShardPlanDecisions,
  type ShardPlanOptions,
} from '@/lib/video-pack-shard-planner';
import { hasAiGatewayKey } from '@/lib/vercel-ai-gateway';
import type { YouTubeMetadata } from '@/lib/youtube-metadata';

/**
 * Jev extract adapter (System 1 routing for the shard pipeline).
 *
 * Jev chooses the next action; application code owns every 0/1.
 * `validateShardManifest` remains the sole coverage/cost/cap gate —
 * this adapter never sets `ok` and never certifies a manifest.
 *
 * Live `evaluate()` runs ONLY when the billing gateway secret exists;
 * otherwise every entry point skips (returns null decisions) and the
 * deterministic planner proceeds alone. Tests always mock `evaluate()`.
 */

export const EXTRACT_NEXT_QUESTION_ID = 'extract_next';

export type JevExtractAction =
  | 'chunk'
  | 'model'
  | 'retry'
  | 'consolidate'
  | 'request-more-evidence'
  | 'stop';

const EXTRACT_ACTIONS: readonly JevExtractAction[] = [
  'chunk',
  'model',
  'retry',
  'consolidate',
  'request-more-evidence',
  'stop',
];

export interface JevExtractDecision {
  action: JevExtractAction;
  confidence: number;
  probabilities: Record<JevExtractAction, number>;
  rationale: string;
  model: string;
}

export interface ExtractPlannerState {
  videoId: string;
  shardCount: number;
  durationSeconds: number;
  costUnits: number;
  costBoundUnits: number;
  validationFailures: string[];
  attempt: number;
}

const EXTRACT_NEXT_QUESTIONS = {
  [EXTRACT_NEXT_QUESTION_ID]: {
    type: 'choice' as const,
    instructions: 'Given this Video Pack shard plan state, what should the extractor do next?',
    criteria: {
      chunk: 'Plan is valid or fixable by (re)sharding; proceed to run shard workers.',
      model: 'The assigned model is wrong for this content; switch model and re-plan.',
      retry: 'A transient failure occurred; retry the same plan.',
      consolidate: 'Shard outputs are ready; merge them into one spec.',
      'request-more-evidence':
        'Coverage or evidence is insufficient; gather more before proceeding.',
      stop: 'Cost bound exceeded, invalid plan, or no path forward; abort without spending.',
    },
  },
};

function isJevExtractAction(value: unknown): value is JevExtractAction {
  return (
    typeof value === 'string' && (EXTRACT_ACTIONS as readonly string[]).includes(value)
  );
}

export function buildExtractEvaluationState(state: ExtractPlannerState): string {
  const failures =
    state.validationFailures.length > 0 ? state.validationFailures.join('; ') : '(none)';
  return [
    'Choose the next extractor action for this Video Pack shard plan.',
    '',
    `video_id: ${state.videoId}`,
    `shards: ${state.shardCount}`,
    `duration_seconds: ${state.durationSeconds}`,
    `cost_units: ${state.costUnits} / bound ${state.costBoundUnits}`,
    `validation_failures: ${failures}`,
    `attempt: ${state.attempt}`,
  ].join('\n');
}

export function mapJevEvaluateResultToExtractDecision(
  result: JevEvaluatePayload,
  modelFallback: string,
): JevExtractDecision | null {
  const answer = result.answers[EXTRACT_NEXT_QUESTION_ID];
  if (!answer || answer.type !== 'choice' || !isJevExtractAction(answer.choice)) {
    return null;
  }
  const action = answer.choice;
  const probabilities = Object.fromEntries(
    EXTRACT_ACTIONS.map((candidate) => [
      candidate,
      toProbability(answer.probabilities?.[candidate], candidate === action ? 0.5 : 0),
    ]),
  ) as Record<JevExtractAction, number>;
  const confidence =
    readTypesafeConfidence(result.providerMetadata, EXTRACT_NEXT_QUESTION_ID) ??
    toProbability(answer.probabilities?.[action], 0.5);
  return {
    action,
    confidence,
    probabilities,
    rationale: '',
    model: result.response?.modelId?.trim() || modelFallback,
  };
}

export type JevExtractEvaluate = typeof evaluate;

/**
 * Ask Jev for the next action. Returns null (skip) when the billing
 * gateway secret is missing, the call fails, or the answer is unmapped.
 */
export async function decideExtractNext(
  state: ExtractPlannerState,
  deps: { evaluateFn?: JevExtractEvaluate } = {},
): Promise<JevExtractDecision | null> {
  if (!hasAiGatewayKey()) {
    return null;
  }
  try {
    const result = await (deps.evaluateFn ?? evaluate)({
      model: aiGateway.evaluationModel(JEV_DEFAULT_MODEL),
      state: buildExtractEvaluationState(state),
      questions: EXTRACT_NEXT_QUESTIONS,
      abortSignal: AbortSignal.timeout(12_000),
    });
    return mapJevEvaluateResultToExtractDecision(result, JEV_DEFAULT_MODEL);
  } catch {
    return null;
  }
}

/**
 * Translate a Jev decision into planner input. `stop` yields null (the
 * caller must not plan); every other action passes the base decisions
 * through — the action itself is consumed by the orchestrator, and the
 * 0/1 stays with `validateShardManifest`.
 */
export function jevDecisionToShardPlanDecisions(
  decision: JevExtractDecision,
  base: ShardPlanDecisions = {},
): ShardPlanDecisions | null {
  if (decision.action === 'stop') {
    return null;
  }
  return { ...base };
}

export interface PlannedShardsWithJev {
  decision: JevExtractDecision | null;
  manifest: ShardManifest | null;
}

/**
 * Plan shards with Jev routing. Without a gateway secret (or on any Jev
 * failure) the deterministic planner proceeds alone. A `stop` decision
 * yields no manifest. Callers must still run `validateShardManifest` —
 * Jev output never implies a 0/1.
 */
export async function planShardsWithJev(
  videoId: string,
  sourceUrl: string,
  metadata: YouTubeMetadata | null,
  durationSeconds: number | null,
  options: ShardPlanOptions = {},
  deps: { evaluateFn?: JevExtractEvaluate; attempt?: number } = {},
): Promise<PlannedShardsWithJev> {
  const base = planShardManifest(videoId, sourceUrl, metadata, durationSeconds, options);
  const failures = validateShardManifest(base).failures;
  const decision = await decideExtractNext(
    {
      videoId,
      shardCount: base.shards.length,
      durationSeconds: base.durationSeconds,
      costUnits: base.costUnits,
      costBoundUnits: base.costBoundUnits,
      validationFailures: failures,
      attempt: deps.attempt ?? 1,
    },
    deps.evaluateFn ? { evaluateFn: deps.evaluateFn } : {},
  );
  if (!decision) {
    return { decision: null, manifest: base };
  }
  const planDecisions = jevDecisionToShardPlanDecisions(decision);
  if (!planDecisions) {
    return { decision, manifest: null };
  }
  return {
    decision,
    manifest: planShardManifest(videoId, sourceUrl, metadata, durationSeconds, options, planDecisions),
  };
}
