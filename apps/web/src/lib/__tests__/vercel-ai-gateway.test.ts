import { afterEach, describe, expect, it, vi } from 'vitest';

import {
  gatewayChat,
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
  vi.unstubAllGlobals();
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

  it('keeps every line of multi-line (pretty-printed) fenced JSON', () => {
    const pretty = '{\n  "ok": true,\n  "n": 1\n}';
    expect(stripJsonCodeFence('```json\n' + pretty + '\n```')).toBe(pretty);
    expect(JSON.parse(stripJsonCodeFence('```json\n' + pretty + '\n```'))).toEqual({ ok: true, n: 1 });
  });

  it('chunks text using embeddings-demo sentence split', () => {
    expect(chunkTextForEmbedding('First idea. Second idea.')).toEqual([
      'First idea',
      'Second idea',
    ]);
  });
});

it.each(['gemini-2.5-flash', 'gemini-3.8-flash', 'openai/gpt-4o'])('Gateway payload follows model policy for %s', async (model) => {
  process.env.AI_GATEWAY_API_KEY = 'test-key';
  const transport = vi.fn().mockResolvedValue({ ok: true, text: async () => JSON.stringify({ choices: [{ message: { content: 'result' } }] }) });
  vi.stubGlobal('fetch', transport);
  await gatewayChat({ model, messages: [{ role: 'user', content: 'test' }], temperature: 0.3 });
  const payload = JSON.parse(transport.mock.calls[0][1].body);
  expect('temperature' in payload).toBe(model !== 'gemini-3.8-flash');
  expect(payload.max_tokens).toBe(4096);
});

it('sends the Gemini 3.8 default without deprecated sampling fields', async () => {
  process.env.AI_GATEWAY_API_KEY = 'test-key';
  const transport = vi.fn().mockResolvedValue({ ok: true, text: async () => JSON.stringify({ choices: [{ message: { content: 'result' } }] }) });
  vi.stubGlobal('fetch', transport);
  await gatewayChat({ messages: [{ role: 'user', content: 'test' }], temperature: 0.3 });
  const payload = JSON.parse(transport.mock.calls[0][1].body);
  expect(payload.model).toBe('google/gemini-3.8-flash');
  for (const field of ['temperature', 'top_p', 'top_k', 'thinking_budget']) {
    expect(payload).not.toHaveProperty(field);
  }
});
