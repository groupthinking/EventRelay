import { experimental_evaluate as evaluate } from 'ai';
import { aiGateway } from '@/lib/ai-gateway';
import { hasAiGatewayKey } from '@/lib/vercel-ai-gateway';

export const JEV_DEFAULT_MODEL = process.env.BILLING_JEV_MODEL?.trim() || 'typesafe-ai/jev';

const LEAD_DECISION_QUESTION_ID = 'lead_decision';

type LeadHistoryMessage = { role: 'user' | 'assistant'; content: string };

export type JevLeadDecision = 'action_items' | 'clarification';

export type JevLeadScore = {
  model: string;
  provider: 'vercel-ai-gateway';
  decision: JevLeadDecision;
  confidence: number;
  probabilities: {
    action_items: number;
    clarification: number;
  };
  rationale: string;
};

const LEAD_ROUTING_QUESTIONS = {
  [LEAD_DECISION_QUESTION_ID]: {
    type: 'choice' as const,
    instructions:
      'Should this chat be routed to action-first guidance or clarification-first guidance?',
    criteria: {
      action_items:
        'User needs concrete next steps, an execution plan, or action-oriented guidance.',
      clarification:
        'The request is ambiguous and needs constraints or clarifying questions first.',
    },
  },
};

export function toProbability(value: unknown, fallback: number): number {
  if (typeof value !== 'number' || Number.isNaN(value)) {
    return fallback;
  }
  return Math.max(0, Math.min(1, value));
}

function isJevLeadDecision(value: unknown): value is JevLeadDecision {
  return value === 'action_items' || value === 'clarification';
}

export function readTypesafeConfidence(
  providerMetadata: unknown,
  questionId: string = LEAD_DECISION_QUESTION_ID,
): number | null {
  if (!providerMetadata || typeof providerMetadata !== 'object') {
    return null;
  }
  const typesafe = (providerMetadata as { typesafe?: unknown }).typesafe;
  if (!typesafe || typeof typesafe !== 'object') {
    return null;
  }
  const confidence = (typesafe as { confidence?: unknown }).confidence;
  if (typeof confidence === 'number' && !Number.isNaN(confidence)) {
    return toProbability(confidence, 0.5);
  }
  if (confidence && typeof confidence === 'object') {
    const perQuestion = (confidence as Record<string, unknown>)[questionId];
    if (typeof perQuestion === 'number' && !Number.isNaN(perQuestion)) {
      return toProbability(perQuestion, 0.5);
    }
  }
  return null;
}

function buildLeadEvaluationState(query: string, history: LeadHistoryMessage[]): string {
  const clippedHistory = history.slice(-4).map((entry) => `${entry.role}: ${entry.content}`);
  const historyBlock = clippedHistory.length ? clippedHistory.join('\n') : '(none)';
  return [
    'Classify whether this chat request should be routed to action-first guidance or clarification-first guidance.',
    '',
    `query: ${query}`,
    `recent_history:\n${historyBlock}`,
  ].join('\n');
}

type LeadEvaluateAnswer = {
  type: 'choice';
  choice: string;
  probabilities?: Record<string, number>;
};

export type JevEvaluatePayload = {
  answers: Record<string, LeadEvaluateAnswer | undefined>;
  providerMetadata?: unknown;
  response?: { modelId?: string };
};

export function mapJevEvaluateResultToLeadScore(
  result: JevEvaluatePayload,
  modelFallback: string,
): Omit<JevLeadScore, 'provider'> | null {
  const answer = result.answers[LEAD_DECISION_QUESTION_ID];
  if (!answer || answer.type !== 'choice' || !isJevLeadDecision(answer.choice)) {
    return null;
  }

  const decision = answer.choice;
  const actionItemsProb = toProbability(answer.probabilities?.action_items, 0.5);
  const clarificationProb = toProbability(answer.probabilities?.clarification, 0.5);

  const selectedProb = toProbability(
    answer.probabilities?.[decision],
    decision === 'action_items' ? actionItemsProb : clarificationProb,
  );

  const confidence =
    readTypesafeConfidence(result.providerMetadata) ?? toProbability(selectedProb, 0.5);

  const probabilities = {
    action_items:
      typeof answer.probabilities?.action_items === 'number'
        ? toProbability(answer.probabilities.action_items, actionItemsProb)
        : decision === 'action_items'
          ? confidence
          : 1 - confidence,
    clarification:
      typeof answer.probabilities?.clarification === 'number'
        ? toProbability(answer.probabilities.clarification, clarificationProb)
        : decision === 'clarification'
          ? confidence
          : 1 - confidence,
  };

  return {
    model: result.response?.modelId?.trim() || modelFallback,
    decision,
    confidence,
    probabilities,
    rationale: '',
  };
}

export async function scoreLeadWithJev(input: {
  query: string;
  history: LeadHistoryMessage[];
}): Promise<JevLeadScore | null> {
  if (!hasAiGatewayKey()) {
    return null;
  }

  const query = input.query.trim();
  if (!query) {
    return null;
  }

  try {
    const result = await evaluate({
      model: aiGateway.evaluationModel(JEV_DEFAULT_MODEL),
      state: buildLeadEvaluationState(query, input.history),
      questions: LEAD_ROUTING_QUESTIONS,
      abortSignal: AbortSignal.timeout(12_000),
    });

    const mapped = mapJevEvaluateResultToLeadScore(result, JEV_DEFAULT_MODEL);
    if (!mapped) {
      return null;
    }

    return {
      ...mapped,
      provider: 'vercel-ai-gateway',
    };
  } catch {
    return null;
  }
}
