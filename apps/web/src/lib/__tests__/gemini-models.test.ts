import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

beforeEach(() => {
  vi.resetModules();
  for (const key of ['GEMINI_FAST_MODEL', 'GEMINI_SEARCH_MODEL', 'GEMINI_STRUCTURED_MODEL', 'VERCEL_AI_GATEWAY_MODEL']) {
    vi.stubEnv(key, '');
  }
});
afterEach(() => vi.unstubAllEnvs());

describe('Gemini model selection', () => {
  it('defaults all web workloads and gateway routing to Gemini 3.8', async () => {
    const models = await import('@/lib/gemini-models');
    expect(models.GEMINI_FAST_MODEL).toBe('gemini-3.8-flash');
    expect(models.GEMINI_SEARCH_MODEL).toBe('gemini-3.8-flash');
    expect(models.GEMINI_STRUCTURED_MODEL).toBe('gemini-3.8-flash');
    const gateway = await import('@/lib/vercel-ai-gateway');
    expect(gateway.VERCEL_AI_GATEWAY_DEFAULT_MODEL).toBe('google/gemini-3.8-flash');
    expect(gateway.toGatewayModelId('')).toBe('google/gemini-3.8-flash');
    vi.stubEnv('AI_GATEWAY_API_KEY', 'test-key');
    const client = await import('@/lib/gemini-client');
    expect(client.getGeminiRoutingLabel()).toBe('gateway:google/gemini-3.8-flash');
  });

  it('keeps older per-workload models and trims overrides', async () => {
    vi.stubEnv('GEMINI_FAST_MODEL', ' gemini-2.5-flash ');
    vi.stubEnv('GEMINI_SEARCH_MODEL', ' gemini-2.5-pro ');
    vi.stubEnv('GEMINI_STRUCTURED_MODEL', ' gemini-3.7-flash ');
    vi.stubEnv('VERCEL_AI_GATEWAY_MODEL', ' google/gemini-2.5-flash ');
    const models = await import('@/lib/gemini-models');
    expect(models.GEMINI_FAST_MODEL).toBe('gemini-2.5-flash');
    expect(models.GEMINI_SEARCH_MODEL).toBe('gemini-2.5-pro');
    expect(models.GEMINI_STRUCTURED_MODEL).toBe('gemini-3.7-flash');
    const gateway = await import('@/lib/vercel-ai-gateway');
    expect(gateway.VERCEL_AI_GATEWAY_DEFAULT_MODEL).toBe('google/gemini-2.5-flash');
    vi.stubEnv('AI_GATEWAY_API_KEY', 'test-key');
    const client = await import('@/lib/gemini-client');
    expect(client.getGeminiRoutingLabel()).toBe('gateway:google/gemini-2.5-flash');
  });

  it('inherits the fast-model override for search and structured requests', async () => {
    vi.stubEnv('GEMINI_FAST_MODEL', 'gemini-2.5-flash');
    const models = await import('@/lib/gemini-models');
    expect(models.GEMINI_SEARCH_MODEL).toBe('gemini-2.5-flash');
    expect(models.GEMINI_STRUCTURED_MODEL).toBe('gemini-2.5-flash');
  });
});
