import 'server-only';

import { createGateway, type GatewayProvider } from '@ai-sdk/gateway';
import { resolveAiGatewayKey, hasAiGatewayKey } from './vercel-ai-gateway';

/**
 * Configured Vercel AI Gateway client using the AI SDK (@ai-sdk/gateway).
 *
 * This module wraps @ai-sdk/gateway with the project's AI_GATEWAY_API_KEY
 * and exposes typed model references for use with `streamText`, `generateText`,
 * and `experimental_generateVideo`.
 *
 * Environment variable: AI_GATEWAY_API_KEY (vck_… key from Vercel Dashboard)
 * Fallback env vars are resolved via resolveAiGatewayKey() in vercel-ai-gateway.ts.
 */

export { hasAiGatewayKey };

/**
 * Returns a configured AI Gateway provider instance.
 * Use with AI SDK functions: streamText({ model: getGateway()('openai/gpt-4o'), ... })
 */
export function getGateway(): GatewayProvider {
  const apiKey = resolveAiGatewayKey();
  if (!apiKey) {
    throw new Error(
      'AI_GATEWAY_API_KEY is not configured. ' +
        'Set it in your environment or Vercel project settings.',
    );
  }
  return createGateway({ apiKey });
}

/** Pre-configured model IDs available through the gateway. */
export const GATEWAY_MODELS = {
  chat: 'openai/gpt-4o' as const,
  video: 'google/veo-3.1-generate-001' as const,
};
