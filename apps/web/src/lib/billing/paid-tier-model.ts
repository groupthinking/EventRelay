import { GROK_BILLING_LEAD_MODEL } from './grok-lead';

/** Default model for free-tier chat (cost-controlled). */
export const FREE_TIER_CHAT_MODEL = process.env.FREE_TIER_CHAT_MODEL || 'gpt-4o-mini';

export type PaidTierRouting = {
  model: string;
  runtime: 'grok-composer' | 'standard';
  plan: 'free' | 'pro';
};

export function resolvePaidTierRouting(isPro: boolean): PaidTierRouting {
  if (isPro) {
    return {
      model: GROK_BILLING_LEAD_MODEL,
      runtime: 'grok-composer',
      plan: 'pro',
    };
  }
  return {
    model: FREE_TIER_CHAT_MODEL,
    runtime: 'standard',
    plan: 'free',
  };
}

export const PRO_FEATURES = {
  unlimitedChat: true,
  agentDispatch: true,
  apiAccess: true,
  priorityProcessing: true,
} as const;

export const FREE_CHAT_DAILY_LIMIT = 5;