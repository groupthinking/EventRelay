import { describe, expect, it } from 'vitest';
import {
  AGENTIC_VIDEO_THINKING_LEVEL,
  buildShardInteractionCreateParams,
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

describe('shard sink source + fps boundary (#2214)', () => {
  it.each([
    'https://attacker.example/x/youtube.com/watch?v=auJzb1D-fag',
    'https://youtu.be/auJzb1D-fag',
    'https://m.youtube.com/watch?v=auJzb1D-fag',
    'https://www.youtube.com/watch?v=auJzb1D-fag&list=PL1',
    'http://www.youtube.com/watch?v=auJzb1D-fag',
    'https://user:pw@www.youtube.com/watch?v=auJzb1D-fag',
    'https://www.youtube.com:443/watch?v=auJzb1D-fag',
    'https://www.youtube.com.attacker.example/watch?v=auJzb1D-fag',
    'javascript:alert(1)//www.youtube.com/watch?v=auJzb1D-fag',
  ])('rejects non-canonical sourceUrl %s before any provider call', async (sourceUrl) => {
    const client = stubClient('ok');
    expect(() => buildShardInteractionInput({ ...CALL, sourceUrl })).toThrow(/canonical YouTube/);
    await expect(runShardVideoInteraction({ ...CALL, sourceUrl }, { client })).rejects.toThrow(/canonical YouTube/);
    expect(client.seen).toHaveLength(0);
  });

  it.each([Number.NaN, 0, -1, Number.POSITIVE_INFINITY, 1000])('rejects fps %s', (fps) => {
    expect(() => buildShardInteractionInput({ ...CALL, fps })).toThrow(/Invalid shard fps/);
  });

  it('keeps fps 1 by default and passes a valid explicit fps through', () => {
    const [video] = buildShardInteractionInput(CALL);
    expect(video).toMatchObject({ processing: { fps: 1 } });
    const [explicit] = buildShardInteractionInput({ ...CALL, fps: 0.5 });
    expect(explicit).toMatchObject({ processing: { fps: 0.5 } });
  });
});

describe('agentic long-video input', () => {
  const longCall: ShardVideoCall = {
    ...CALL,
    start_s: 0,
    end_s: 620,
    processing: 'agentic',
    model: 'gemini-3.8-flash',
  };

  it('emits processing agentic, thinking_level high, and gemini-3.8-flash with no fps or offsets', () => {
    const params = buildShardInteractionCreateParams(longCall);
    expect(params.model).toBe('gemini-3.8-flash');
    expect(params.generation_config).toEqual({ thinking_level: AGENTIC_VIDEO_THINKING_LEVEL });
    expect(AGENTIC_VIDEO_THINKING_LEVEL).toBe('high');
    expect(params.input[0]).toEqual({
      type: 'video',
      uri: longCall.sourceUrl,
      mime_type: 'video/mp4',
      processing: 'agentic',
    });
    expect(JSON.stringify(params.input[0])).not.toMatch(/fps|start_offset|end_offset/);
  });

  it('keeps a short call on the static object and the same model', () => {
    const params = buildShardInteractionCreateParams(CALL);
    expect(params.model).toBe('gemini-3.8-flash');
    expect(params.generation_config).toBeUndefined();
    expect(params.input[0]).toEqual({
      type: 'video',
      uri: CALL.sourceUrl,
      mime_type: 'video/mp4',
      processing: { type: 'static', start_offset: '0s', end_offset: '180s', fps: 1 },
    });
  });

  it('sends thinking_level high on the agentic client call and omits it for static', async () => {
    const agenticClient = stubClient('{"ok":true}');
    await runShardVideoInteraction(longCall, { client: agenticClient });
    expect(agenticClient.seen[0]).toMatchObject({
      model: 'gemini-3.8-flash',
      generation_config: { thinking_level: 'high' },
    });
    const staticClient = stubClient('{"ok":true}');
    await runShardVideoInteraction(CALL, { client: staticClient });
    const staticParams = staticClient.seen[0] as { generation_config?: unknown };
    expect(staticParams.generation_config).toBeUndefined();
  });

  it('rejects a non-canonical agentic URL before any provider call', () => {
    expect(() =>
      buildShardInteractionInput({ ...longCall, sourceUrl: 'https://youtu.be/auJzb1D-fag' }),
    ).toThrow(/canonical YouTube/);
  });
});
