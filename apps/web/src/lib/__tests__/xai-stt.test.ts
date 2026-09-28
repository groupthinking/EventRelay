import { afterEach, describe, expect, it, vi } from 'vitest';
import { transcribeWithXai, XAI_STT_ENDPOINT, XAI_STT_MODEL } from '@/lib/xai-stt';

const KEY_ENVS = ['GROK_XAI_API_KEY', 'XAI_API_KEY', 'GROK_API_KEY'] as const;

const original: Record<(typeof KEY_ENVS)[number], string | undefined> = {
  GROK_XAI_API_KEY: process.env.GROK_XAI_API_KEY,
  XAI_API_KEY: process.env.XAI_API_KEY,
  GROK_API_KEY: process.env.GROK_API_KEY,
};

function clearKeys(): void {
  for (const name of KEY_ENVS) delete process.env[name];
}

afterEach(() => {
  for (const name of KEY_ENVS) {
    const value = original[name];
    if (value === undefined) delete process.env[name];
    else process.env[name] = value;
  }
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe('transcribeWithXai', () => {
  it('sends model then url with the GROK_XAI_API_KEY bearer', async () => {
    clearKeys();
    process.env.GROK_XAI_API_KEY = 'working-grok-key';
    process.env.XAI_API_KEY = 'stale-xai-key';
    const fetchImpl = vi.fn(async (_input: string, _init?: RequestInit) =>
      new Response(JSON.stringify({ text: 'build the queue', duration: 12.5, language: 'en' }), {
        status: 200,
        headers: { 'content-type': 'application/json' },
      }),
    );

    const result = await transcribeWithXai(
      { url: 'https://cdn.loom.com/sessions/transcoded/c43a642f815f4378b6f80a889bb73d8d.mp4' },
      { fetch: fetchImpl as unknown as typeof fetch },
    );

    expect(result).toEqual({
      text: 'build the queue',
      duration: 12.5,
      language: 'en',
      model: XAI_STT_MODEL,
    });
    expect(fetchImpl).toHaveBeenCalledTimes(1);
    const [endpoint, init] = fetchImpl.mock.calls[0] ?? [];
    if (init === undefined) throw new Error('xAI STT fetch was not called with RequestInit');
    expect(endpoint).toBe(XAI_STT_ENDPOINT);
    expect(new Headers(init.headers).get('Authorization')).toBe('Bearer working-grok-key');
    const form = init.body as FormData;
    expect([...form.keys()]).toEqual(['model', 'url']);
    expect(form.get('model')).toBe(XAI_STT_MODEL);
    expect(String(form.get('url'))).toContain('cdn.loom.com');
    expect(String(form.get('url'))).not.toContain('/share/');
  });

  it('appends the audio file last', async () => {
    clearKeys();
    process.env.XAI_API_KEY = 'fallback-xai-key';
    const fetchImpl = vi.fn(async (_input: string, _init?: RequestInit) =>
      new Response(JSON.stringify({ text: 'aac transcript', duration: 4 }), { status: 200 }),
    );
    const bytes = new Uint8Array([0xff, 0xf1, 0x50]);
    await transcribeWithXai(
      { file: { bytes, filename: 'loom-audio.aac', contentType: 'audio/aac' } },
      { fetch: fetchImpl as unknown as typeof fetch },
    );
    const init = fetchImpl.mock.calls[0]?.[1];
    if (init === undefined) throw new Error('xAI STT fetch was not called with RequestInit');
    const form = init.body as FormData;
    expect([...form.keys()]).toEqual(['model', 'file']);
    expect(form.get('url')).toBeNull();
    expect(new Headers(init.headers).get('Authorization')).toBe('Bearer fallback-xai-key');
  });

  it('rejects an empty transcript or a missing duration', async () => {
    clearKeys();
    process.env.GROK_XAI_API_KEY = 'working-grok-key';
    const fetchImpl = vi.fn()
      .mockResolvedValueOnce(new Response(JSON.stringify({ text: '  ', duration: 3 }), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ text: 'hello', duration: 0 }), { status: 200 }));
    await expect(
      transcribeWithXai({ url: 'https://cdn.loom.com/a.mp4' }, { fetch: fetchImpl }),
    ).rejects.toThrow(/xai_stt_empty/);
    await expect(
      transcribeWithXai({ url: 'https://cdn.loom.com/a.mp4' }, { fetch: fetchImpl }),
    ).rejects.toThrow(/xai_stt_empty/);
  });

  it('names the missing key without calling xAI', async () => {
    clearKeys();
    const fetchImpl = vi.fn();
    await expect(transcribeWithXai({ url: 'https://cdn.loom.com/a.mp4' }, { fetch: fetchImpl })).rejects.toThrow(
      'XAI_API_KEY missing fromEnv:none',
    );
    expect(fetchImpl).not.toHaveBeenCalled();
  });
});
