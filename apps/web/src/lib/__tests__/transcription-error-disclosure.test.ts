import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';

// `fetchTranscript`'s error string is returned to the caller verbatim by
// `/api/transcribe`'s `!result.success` branches. That is only safe while every
// value it can carry is a fixed, app-authored literal. These tests pin the two
// values that were not: the caller-supplied `audioUrl`'s HTTP status, and a
// message that varied on whether provider API keys were configured.

vi.mock('server-only', () => ({}));
vi.mock('@/lib/ssrf-guard', () => ({
  assertPublicHttpUrl: vi.fn(async (input: string) => new URL(input)),
}));
vi.mock('@/lib/youtube-metadata', () => ({
  fetchYouTubeMetadata: vi.fn(async () => null),
  formatMetadataAsContext: vi.fn(() => ''),
}));
vi.mock('@/lib/gemini-client', () => ({
  getGeminiClient: vi.fn(() => null),
  hasGeminiKey: vi.fn(() => false),
}));
vi.mock('@/lib/vercel-ai-gateway', () => ({
  gatewayChat: vi.fn(async () => null),
  hasAiGatewayKey: vi.fn(() => false),
  toGatewayModelId: vi.fn((m: string) => m),
}));

import { fetchTranscript } from '@/lib/transcription-service';

const AUDIO_URL = 'https://cdn.example.com/clip.mp3';

let consoleError: ReturnType<typeof vi.spyOn>;
const savedEnv = { ...process.env };

beforeEach(() => {
  consoleError = vi.spyOn(console, 'error').mockImplementation(() => {});
  vi.spyOn(console, 'warn').mockImplementation(() => {});
});

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
  process.env = { ...savedEnv };
});

describe('fetchTranscript error disclosure', () => {
  it('does not echo the status of a caller-supplied audioUrl', async () => {
    process.env.OPENAI_API_KEY = 'sk-test-key';
    // 403 from a host the caller chose. Echoing it back is a cross-origin read
    // the browser's same-origin policy would otherwise deny them.
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => new Response('forbidden', { status: 403 })),
    );

    const result = await fetchTranscript({ audioUrl: AUDIO_URL });

    expect(result.success).toBe(false);
    expect(result.error).toBe('Could not retrieve the audio file');
    // The probe result must not survive anywhere in the caller-visible payload.
    expect(JSON.stringify(result)).not.toContain('403');
    // ...but an operator can still see it.
    expect(consoleError).toHaveBeenCalledWith(expect.stringContaining('403'));
  });

  it('reports the same status-free message whatever the upstream status is', async () => {
    process.env.OPENAI_API_KEY = 'sk-test-key';
    const errors: string[] = [];

    for (const status of [401, 403, 404, 500]) {
      vi.stubGlobal(
        'fetch',
        vi.fn(async () => new Response('nope', { status })),
      );
      const result = await fetchTranscript({ audioUrl: AUDIO_URL });
      errors.push(result.error ?? '');
    }

    // One distinguishable message per status would rebuild the oracle.
    expect(new Set(errors).size).toBe(1);
  });

  it('does not disclose whether provider API keys are configured', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => new Response('{}', { status: 500 })),
    );

    delete process.env.OPENAI_API_KEY;
    const withoutKeys = await fetchTranscript({ url: 'https://youtu.be/auJzb1D-fag' });

    process.env.OPENAI_API_KEY = 'sk-test-key';
    const withKeys = await fetchTranscript({ url: 'https://youtu.be/auJzb1D-fag' });

    expect(withoutKeys.success).toBe(false);
    expect(withKeys.success).toBe(false);
    // Configuration state is not a caller-facing fact.
    expect(withoutKeys.error).toBe(withKeys.error);
    expect(withoutKeys.error).not.toMatch(/OPENAI_API_KEY|GEMINI_API_KEY|Vercel/i);
    // The distinction stays available to operators.
    expect(consoleError).toHaveBeenCalledWith(
      expect.stringContaining('no OPENAI_API_KEY or GEMINI_API_KEY configured'),
    );
  });
});
