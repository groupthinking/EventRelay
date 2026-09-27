import { describe, expect, it } from 'vitest';
import {
  buildShardInteractionInput,
  hasDirectGoogleKey,
  resolveDirectGoogleKey,
  runShardVideoInteraction,
  secondsToOffset,
  type InteractionsClient,
  type ShardVideoCall,
} from '@/lib/google-genai-video';

const CALL: ShardVideoCall = {
  sourceUrl: 'https://www.youtube.com/watch?v=auJzb1D-fag',
  start_s: 0,
  end_s: 180,
  model: 'gemini-3.8-flash',
  systemInstruction: 'SYSTEM',
  sectionPrompt: 'PROMPT',
};

function stubClient(outputText: string | undefined): InteractionsClient & { seen: unknown[] } {
  const seen: unknown[] = [];
  return {
    seen,
    interactions: {
      create: async (...args: unknown[]) => {
        seen.push(args[0]);
        return { output_text: outputText, id: 'int_1' };
      },
    },
  };
}

describe('secondsToOffset', () => {
  it('formats decimal seconds with an s suffix', () => {
    expect(secondsToOffset(0)).toBe('0s');
    expect(secondsToOffset(180)).toBe('180s');
    expect(secondsToOffset(10.5)).toBe('10.5s');
  });

  it('rejects negative and non-finite offsets', () => {
    expect(() => secondsToOffset(-1)).toThrowError(/Invalid shard offset/);
    expect(() => secondsToOffset(Number.NaN)).toThrowError(/Invalid shard offset/);
  });
});

describe('buildShardInteractionInput', () => {
  it('emits a static-clipped video block plus the prompts', () => {
    const input = buildShardInteractionInput(CALL);
    expect(input).toHaveLength(2);
    const [video, text] = input;
    expect(video).toEqual({
      type: 'video',
      uri: CALL.sourceUrl,
      mime_type: 'video/mp4',
      processing: { type: 'static', start_offset: '0s', end_offset: '180s', fps: 1 },
    });
    expect(text).toEqual({ type: 'text', text: 'SYSTEM\n\nPROMPT' });
  });

  it('refuses to build input for an invalid range (no full-video fallback)', () => {
    expect(() => buildShardInteractionInput({ ...CALL, end_s: 0 })).toThrowError(
      /refusing full-video fallback/,
    );
    expect(() => buildShardInteractionInput({ ...CALL, start_s: -5 })).toThrowError(
      /refusing full-video fallback/,
    );
  });
});

describe('runShardVideoInteraction', () => {
  it('returns text plus the interaction id', async () => {
    const client = stubClient('{"ok":true}');
    const result = await runShardVideoInteraction(CALL, { client });
    expect(result).toEqual({ text: '{"ok":true}', interactionId: 'int_1' });
    const params = client.seen[0] as { model: string; input: unknown[] };
    expect(params.model).toBe('gemini-3.8-flash');
    expect(params.input).toHaveLength(2);
  });

  it('fails closed on empty model output', async () => {
    const client = stubClient('   ');
    await expect(runShardVideoInteraction(CALL, { client })).rejects.toThrowError(
      /refusing to continue without evidence/,
    );
  });

  it('fails closed on an invalid range without calling the model', async () => {
    const client = stubClient('{"ok":true}');
    await expect(
      runShardVideoInteraction({ ...CALL, start_s: 200, end_s: 100 }, { client }),
    ).rejects.toThrowError(/refusing full-video fallback/);
    expect(client.seen).toHaveLength(0);
  });
});

describe('direct key resolution', () => {
  it('reads GEMINI_API_KEY / GOOGLE_API_KEY and never the gateway key', () => {
    const prevGemini = process.env.GEMINI_API_KEY;
    const prevGoogle = process.env.GOOGLE_API_KEY;
    try {
      delete process.env.GEMINI_API_KEY;
      delete process.env.GOOGLE_API_KEY;
      expect(resolveDirectGoogleKey()).toBe('');
      expect(hasDirectGoogleKey()).toBe(false);
      process.env.GEMINI_API_KEY = 'direct-key';
      expect(resolveDirectGoogleKey()).toBe('direct-key');
      expect(hasDirectGoogleKey()).toBe(true);
    } finally {
      if (prevGemini === undefined) delete process.env.GEMINI_API_KEY;
      else process.env.GEMINI_API_KEY = prevGemini;
      if (prevGoogle === undefined) delete process.env.GOOGLE_API_KEY;
      else process.env.GOOGLE_API_KEY = prevGoogle;
    }
  });
});
