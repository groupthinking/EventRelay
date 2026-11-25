import { afterEach, describe, expect, it, vi } from 'vitest';
import {
  getXaiApiKey,
  grokChatCompletion,
  selectXaiApiKey,
  XAI_KEY_ENV_NAMES,
} from '../grok-client';

const KEY_ENVS = ['GROK_XAI_API_KEY', 'XAI_API_KEY', 'GROK_API_KEY'] as const;
const original: Record<(typeof KEY_ENVS)[number], string | undefined> = {
  GROK_XAI_API_KEY: process.env.GROK_XAI_API_KEY,
  XAI_API_KEY: process.env.XAI_API_KEY,
  GROK_API_KEY: process.env.GROK_API_KEY,
};

function clearKeys(): void {
  for (const name of KEY_ENVS) {
    delete process.env[name];
  }
}

function restoreKeys(): void {
  for (const name of KEY_ENVS) {
    const value = original[name];
    if (value === undefined) {
      delete process.env[name];
    } else {
      process.env[name] = value;
    }
  }
}

afterEach(() => {
  restoreKeys();
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe('selectXaiApiKey', () => {
  it('prefers GROK_XAI_API_KEY over XAI_API_KEY and GROK_API_KEY', () => {
    const selected = selectXaiApiKey({
      GROK_XAI_API_KEY: 'working-grok-key',
      XAI_API_KEY: 'stale-xai-key',
      GROK_API_KEY: 'legacy-grok-key',
    });
    expect(selected).toEqual({
      apiKey: 'working-grok-key',
      fromEnv: 'GROK_XAI_API_KEY',
    });
    expect(XAI_KEY_ENV_NAMES).toEqual([
      'GROK_XAI_API_KEY',
      'XAI_API_KEY',
      'GROK_API_KEY',
    ]);
  });

  it('falls through empty strings to the next supported name', () => {
    expect(
      selectXaiApiKey({
        GROK_XAI_API_KEY: '',
        XAI_API_KEY: 'fallback-xai-key',
        GROK_API_KEY: 'legacy-grok-key',
      }),
    ).toEqual({ apiKey: 'fallback-xai-key', fromEnv: 'XAI_API_KEY' });

    expect(
      selectXaiApiKey({
        GROK_XAI_API_KEY: '',
        XAI_API_KEY: '',
        GROK_API_KEY: 'legacy-grok-key',
      }),
    ).toEqual({ apiKey: 'legacy-grok-key', fromEnv: 'GROK_API_KEY' });
  });

  it('returns undefined when none of the three names are set', () => {
    expect(selectXaiApiKey({})).toBeUndefined();
  });

  it('reads process.env in the same order via getXaiApiKey', () => {
    clearKeys();
    process.env.XAI_API_KEY = 'stale-xai-key';
    process.env.GROK_XAI_API_KEY = 'working-grok-key';
    expect(getXaiApiKey()).toBe('working-grok-key');
  });
});

describe('grokChatCompletion key errors', () => {
  it('names no env when every key is missing and does not call xAI', async () => {
    clearKeys();
    const fetchMock = vi.fn();
    vi.stubGlobal('fetch', fetchMock);

    await expect(grokChatCompletion('hello')).rejects.toThrow(
      'XAI_API_KEY missing fromEnv:none',
    );
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it('sends the GROK_XAI_API_KEY bearer and labels xai_http errors with that name', async () => {
    clearKeys();
    const secret = 'working-grok-key-value';
    process.env.GROK_XAI_API_KEY = secret;
    process.env.XAI_API_KEY = 'stale-xai-key-value';

    const fetchMock = vi.fn().mockResolvedValue({
      ok: false,
      status: 400,
      text: async () =>
        `Incorrect API key provided: ${secret}. You can obtain an API key from https://console.x.ai.`,
    });
    vi.stubGlobal('fetch', fetchMock);

    await expect(grokChatCompletion('hello', 'grok-4-1-fast')).rejects.toThrow(
      /xai_http_400 fromEnv:GROK_XAI_API_KEY:/,
    );

    try {
      await grokChatCompletion('hello', 'grok-4-1-fast');
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      expect(message).toContain('fromEnv:GROK_XAI_API_KEY');
      expect(message).toContain('[redacted]');
      expect(message).not.toContain(secret);
      expect(message).not.toContain('stale-xai-key-value');
    }

    expect(fetchMock).toHaveBeenCalled();
    const init = fetchMock.mock.calls[0]?.[1] as RequestInit;
    const headers = init.headers as Record<string, string>;
    expect(headers.Authorization).toBe(`Bearer ${secret}`);
  });
});
