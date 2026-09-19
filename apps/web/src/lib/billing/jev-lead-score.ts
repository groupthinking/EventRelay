import { gatewayChat, hasAiGatewayKey, stripJsonCodeFence } from '@/lib/vercel-ai-gateway';

const DEFAULT_JEV_MODEL = process.env.BILLING_JEV_MODEL?.trim() || 'typesafe-ai/jev';

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

type JevLeadPayload = {
  decision?: unknown;
  confidence?: unknown;
  probabilities?: {
    action_items?: unknown;
    clarification?: unknown;
  } | null;
  rationale?: unknown;
};

function toProbability(value: unknown, fallback: number): number {
  if (typeof value !== 'number' || Number.isNaN(value)) {
    return fallback;
  }
  return Math.max(0, Math.min(1, value));
}

export function parseJevLeadScore(text: string): Omit<JevLeadScore, 'model' | 'provider'> | null {
  let payload: JevLeadPayload;
  try {
    payload = JSON.parse(stripJsonCodeFence(text)) as JevLeadPayload;
  } catch {
    return null;
  }

  const decision =
    payload.decision === 'action_items' || payload.decision === 'clarification'
      ? payload.decision
      : null;
  if (!decision) {
    return null;
  }

  const confidence = toProbability(payload.confidence, 0.5);
  const actionItemsProb = toProbability(payload.probabilities?.action_items, decision === 'action_items' ? confidence : 1 - confidence);
  const clarificationProb = toProbability(payload.probabilities?.clarification, 1 - actionItemsProb);

  return {
    decision,
    confidence,
    probabilities: {
      action_items: actionItemsProb,
      clarification: clarificationProb,
    },
    rationale:
      typeof payload.rationale === 'string' && payload.rationale.trim()
        ? payload.rationale.trim().slice(0, 400)
        : 'No rationale supplied by Jev.',
  };
}

function buildLeadScoringPrompt(query: string, history: LeadHistoryMessage[]): string {
  const clippedHistory = history.slice(-4).map((entry) => `${entry.role}: ${entry.content}`);
  const historyBlock = clippedHistory.length ? clippedHistory.join('\n') : '(none)';
  return [
    'Classify whether this chat request should be routed to action-first guidance or clarification-first guidance.',
    'Return strict JSON only with keys: decision, confidence, probabilities, rationale.',
    'decision must be either "action_items" or "clarification".',
    'confidence must be a number from 0 to 1.',
    'probabilities must include numeric action_items and clarification from 0 to 1.',
    'rationale must be a short sentence.',
    '',
    `query: ${query}`,
    `recent_history:\n${historyBlock}`,
  ].join('\n');
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
    const result = await gatewayChat({
      model: DEFAULT_JEV_MODEL,
      temperature: 0,
      max_tokens: 220,
      timeoutMs: 12_000,
      messages: [
        {
          role: 'system',
          content:
            'You are Jev, a typed decision model. Output only JSON and never include markdown.',
        },
        {
          role: 'user',
          content: buildLeadScoringPrompt(query, input.history),
        },
      ],
    });

    const parsed = parseJevLeadScore(result.content);
    if (!parsed) {
      return null;
    }

    return {
      ...parsed,
      model: result.model || DEFAULT_JEV_MODEL,
      provider: 'vercel-ai-gateway',
    };
  } catch {
    return null;
  }
}
