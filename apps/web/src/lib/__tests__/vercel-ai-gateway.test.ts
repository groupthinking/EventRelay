import { afterEach, describe, expect, it } from 'vitest';

import {
  chunkTextForEmbedding,
  hasAiGatewayKey,
  resolveAiGatewayKey,
  stripJsonCodeFence,
  toGatewayModelId,
} from '@/lib/vercel-ai-gateway';

const ENV_KEYS = [
  'AI_GATEWAY_API_KEY',
  'VERCEL_AI_GATEWAY_API_KEY',
  'VERCEL_AI_GATEWAY_API',
  'VERCEL_API_KEY',
] as const;

afterEach(() => {
  for (const key of ENV_KEYS) delete process.env[key];
});

describe('vercel-ai-gateway', () => {
  it('resolves AI_GATEWAY_API_KEY first', () => {
    process.env.VERCEL_API_KEY = 'vercel-token';
    process.env.AI_GATEWAY_API_KEY = 'vck_test';
    expect(resolveAiGatewayKey()).toBe('vck_test');
    expect(hasAiGatewayKey()).toBe(true);
  });

  it('prefixes gemini model ids for gateway routing', () => {
    expect(toGatewayModelId('gemini-2.5-flash')).toBe('google/gemini-2.5-flash');
    expect(toGatewayModelId('google/gemini-2.5-flash')).toBe('google/gemini-2.5-flash');
  });

  it('strips markdown json fences', () => {
    expect(stripJsonCodeFence('```json\n{"ok":true}\n```')).toBe('{"ok":true}');
  });

  it('chunks text using embeddings-demo sentence split', () => {
    expect(chunkTextForEmbedding('First idea. Second idea.')).toEqual([
      'First idea',
      'Second idea',
    ]);
  });
});