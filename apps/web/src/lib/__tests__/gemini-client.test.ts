import { afterEach, describe, expect, it } from 'vitest';

import {
  classifyGeminiError,
  getGeminiAuthMode,
  getGeminiConfig,
  resolveGeminiApiKey,
} from '@/lib/gemini-client';

const ENV_KEYS = [
  'GEMINI_API_KEY',
  'GOOGLE_API_KEY',
  'Vertex_AI_API_KEY',
  'GOOGLE_GENAI_USE_VERTEXAI',
] as const;

function clearGeminiEnv() {
  for (const key of ENV_KEYS) {
    delete process.env[key];
  }
}

afterEach(() => {
  clearGeminiEnv();
});

describe('gemini-client auth resolution', () => {
  it('prefers AI Studio keys over Vertex when both are set', () => {
    process.env.Vertex_AI_API_KEY = 'vertex-key';
    process.env.GEMINI_API_KEY = 'studio-key';

    expect(getGeminiAuthMode()).toBe('studio');
    expect(resolveGeminiApiKey()).toBe('studio-key');
    expect(getGeminiConfig()).toEqual({ configured: true, mode: 'studio' });
  });

  it('uses Vertex when GOOGLE_GENAI_USE_VERTEXAI=true', () => {
    process.env.Vertex_AI_API_KEY = 'vertex-key';
    process.env.GEMINI_API_KEY = 'studio-key';
    process.env.GOOGLE_GENAI_USE_VERTEXAI = 'true';

    expect(getGeminiAuthMode()).toBe('vertex');
    expect(resolveGeminiApiKey()).toBe('vertex-key');
  });

  it('falls back to Vertex key when no studio key exists', () => {
    process.env.Vertex_AI_API_KEY = 'vertex-only';

    expect(getGeminiAuthMode()).toBe('vertex');
    expect(resolveGeminiApiKey()).toBe('vertex-only');
  });

  it('classifies billing-disabled Gemini errors', () => {
    const classified = classifyGeminiError(
      new Error('403 BILLING_DISABLED for aiplatform.googleapis.com'),
    );

    expect(classified.code).toBe('BILLING_DISABLED');
    expect(classified.userMessage).toContain('billing');
  });
});