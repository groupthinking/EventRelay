import 'server-only';

import { createGateway } from '@ai-sdk/gateway';
import { resolveAiGatewayKey } from '@/lib/vercel-ai-gateway';

export const GATEWAY_CHAT_MODEL = 'openai/gpt-4o';
export const GATEWAY_VIDEO_MODEL = 'google/veo-3.1-generate-001';

export const aiGateway = createGateway({
  apiKey: resolveAiGatewayKey() || undefined,
});
