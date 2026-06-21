import { createOpenAI } from '@ai-sdk/openai';

/**
 * Vercel AI Gateway client.
 *
 * Routes requests through https://ai-gateway.vercel.sh so you get:
 *  - unified billing
 *  - automatic rate-limit retries
 *  - request logging in the Vercel dashboard
 *
 * Requires AI_GATEWAY_API_KEY env var (set in Vercel project settings).
 */
export const aiGateway = createOpenAI({
  apiKey: process.env.AI_GATEWAY_API_KEY ?? '',
  baseURL: 'https://ai-gateway.vercel.sh/v1',
});

/** Default model for chat fallback */
export const GATEWAY_CHAT_MODEL = 'openai/gpt-4o';

/** Model for video generation */
export const GATEWAY_VIDEO_MODEL = 'google/veo-3.1-generate-001';
