import { afterEach, describe, expect, it, vi } from 'vitest';
import type { JevEvaluatePayload } from '@/lib/billing/jev-lead-score';
import type { ShardVideoInteractionRunner } from '@/lib/google-genai-video';
import { VideoPackExtractError, extractVideoPackSpec } from '@/lib/video-pack-extractor';
import { isTransientVideoPackExtractError } from '@/lib/video-pack-extract-reason';
import { planShardManifest, validateShardManifest } from '@/lib/video-pack-shard-planner';

const { experimental_evaluate } = vi.hoisted(() => ({
  experimental_evaluate: vi.fn(),
}));

vi.mock('ai', async () => {
  const actual = await vi.importActual<typeof import('ai')>('ai');
  return { ...actual, experimental_evaluate };
});

vi.mock('@/lib/youtube-metadata', () => ({
  fetchYouTubeMetadata: vi.fn(async () => null),
  preflightYouTubeVideoSource: vi.fn(async () => 'available'),
}));

vi.mock('@/lib/youtube-captions', () => ({
  fetchYouTubeCaptions: vi.fn(async () => null),
}));

const CANON = 'auJzb1D-fag';
const SOURCE_URL = `https://www.youtube.com/watch?v=${CANON}`;

const LONG_METADATA = {
  videoId: CANON,
  title: 'Flat tire change',
  channel: 'Test',
  description: '',
  durationSeconds: 620,
  chapters: [
    { time: '0:00', title: 'Intro' },
    { time: '3:00', title: 'Jack' },
    { time: '6:00', title: 'Finish' },
  ],
};

const SPEC_JSON = {
  transcript: {
    language: 'en',
    full_text: 'Me at the zoo. The elephants have really long trunks.',
    segments: [{ idx: 0, start_s: 0, end_s: 5.2, text: 'Me at the zoo.' }],
  },
  keyframes: [{ t_s: 1.2, desc: 'Elephants at the enclosure' }],
  concepts: ['zoo', 'elephants'],
  requirements: [],
  code_snippets: [],
};

function choicePayload(choice: string): JevEvaluatePayload {
  return {
    answers: {
      extract_next: {
        type: 'choice',
        choice,
        probabilities: { [choice]: 0.81 },
      },
    },
    providerMetadata: { typesafe: { confidence: 0.81 } },
    response: { modelId: 'typesafe-ai/jev' },
  };
}

function videoRunner(): ReturnType<typeof vi.fn<ShardVideoInteractionRunner>> {
  return vi.fn<ShardVideoInteractionRunner>(async () => ({
    text: JSON.stringify(SPEC_JSON),
    interactionId: 'int-jev-wire',
  }));
}

async function loadMetadataMock() {
  const { fetchYouTubeMetadata } = await import('@/lib/youtube-metadata');
  vi.mocked(fetchYouTubeMetadata).mockResolvedValue(LONG_METADATA);
}

afterEach(() => {
  delete process.env.GEMINI_API_KEY;
  delete process.env.GOOGLE_API_KEY;
  delete process.env.AI_GATEWAY_API_KEY;
  delete process.env.VERCEL_AI_GATEWAY_API_KEY;
  experimental_evaluate.mockReset();
  vi.restoreAllMocks();
});

describe('extractVideoPackSpec Jev wiring', () => {
  it('keeps the deterministic plan when the gateway secret is absent', async () => {
    delete process.env.AI_GATEWAY_API_KEY;
    delete process.env.VERCEL_AI_GATEWAY_API_KEY;
    process.env.GEMINI_API_KEY = 'test-direct-key';
    await loadMetadataMock();
    const runVideo = videoRunner();

    const spec = await extractVideoPackSpec(
      { sourceUrl: SOURCE_URL, videoId: CANON },
      { runVideoInteraction: runVideo },
    );

    const manifest = planShardManifest(CANON, SOURCE_URL, LONG_METADATA, 620);
    expect(validateShardManifest(manifest).ok).toBe(1);
    expect(experimental_evaluate).not.toHaveBeenCalled();
    expect(runVideo).toHaveBeenCalledTimes(manifest.shards.length);
    expect(runVideo.mock.calls.map(([call]) => [call.start_s, call.end_s])).toEqual(
      manifest.shards.map((shard) => [shard.start_s, shard.end_s]),
    );
    expect(spec.concepts).toEqual(['zoo', 'elephants']);
  });

  it('fails closed on stop before any Interactions call', async () => {
    process.env.AI_GATEWAY_API_KEY = 'vck_test';
    process.env.GEMINI_API_KEY = 'test-direct-key';
    experimental_evaluate.mockResolvedValue(choicePayload('stop'));
    await loadMetadataMock();
    const runVideo = videoRunner();

    await expect(
      extractVideoPackSpec(
        { sourceUrl: SOURCE_URL, videoId: CANON },
        { runVideoInteraction: runVideo },
      ),
    ).rejects.toSatisfy((error: unknown) => {
      expect(error).toBeInstanceOf(VideoPackExtractError);
      expect(error).toMatchObject({ message: expect.stringMatching(/stop/i) });
      expect((error as Error).message).toMatch(/refusing video calls/i);
      expect(isTransientVideoPackExtractError(error)).toBe(false);
      return true;
    });

    expect(experimental_evaluate).toHaveBeenCalledTimes(1);
    expect(runVideo).not.toHaveBeenCalled();
  });

  it('uses the Jev-returned manifest for other actions and still requires validator ok', async () => {
    process.env.AI_GATEWAY_API_KEY = 'vck_test';
    process.env.GEMINI_API_KEY = 'test-direct-key';
    experimental_evaluate.mockResolvedValue({
      ...choicePayload('chunk'),
      ok: 1,
    });
    await loadMetadataMock();
    const runVideo = videoRunner();

    await extractVideoPackSpec(
      { sourceUrl: SOURCE_URL, videoId: CANON },
      { runVideoInteraction: runVideo },
    );

    const manifest = planShardManifest(CANON, SOURCE_URL, LONG_METADATA, 620);
    expect(validateShardManifest(manifest)).toEqual({ ok: 1, failures: [] });
    expect(experimental_evaluate).toHaveBeenCalledTimes(2);
    const postCheck = experimental_evaluate.mock.calls[1]?.[0] as {
      state: string;
      questions: { extract_next: { criteria: Record<string, string> } };
    };
    expect(postCheck.state).toContain('merged Video Pack');
    expect(Object.keys(postCheck.questions.extract_next.criteria).sort()).toEqual([
      'consolidate',
      'request-more-evidence',
      'retry',
      'stop',
    ]);
    expect(runVideo.mock.calls.map(([call]) => [call.start_s, call.end_s])).toEqual(
      manifest.shards.map((shard) => [shard.start_s, shard.end_s]),
    );
    expect(runVideo.mock.calls[0]?.[0].model).toBe('gemini-3.8-flash');
  });

  it('rejects a chunk decision when validateShardManifest returns 0', async () => {
    process.env.AI_GATEWAY_API_KEY = 'vck_test';
    process.env.GEMINI_API_KEY = 'test-direct-key';
    experimental_evaluate.mockResolvedValue(choicePayload('chunk'));
    await loadMetadataMock();
    const planner = await import('@/lib/video-pack-shard-planner');
    vi.spyOn(planner, 'validateShardManifest').mockReturnValue({
      ok: 0,
      failures: ['forced checkpoint miss'],
    });
    const runVideo = videoRunner();

    await expect(
      extractVideoPackSpec(
        { sourceUrl: SOURCE_URL, videoId: CANON },
        { runVideoInteraction: runVideo },
      ),
    ).rejects.toThrow(/forced checkpoint miss/);

    expect(experimental_evaluate).toHaveBeenCalledTimes(1);
    expect(runVideo).not.toHaveBeenCalled();
  });

  it('treats an evaluate throw as a null decision and keeps the deterministic plan', async () => {
    process.env.AI_GATEWAY_API_KEY = 'vck_test';
    process.env.GEMINI_API_KEY = 'test-direct-key';
    experimental_evaluate.mockRejectedValue(new Error('gateway down'));
    await loadMetadataMock();
    const runVideo = videoRunner();

    await extractVideoPackSpec(
      { sourceUrl: SOURCE_URL, videoId: CANON },
      { runVideoInteraction: runVideo },
    );

    const manifest = planShardManifest(CANON, SOURCE_URL, LONG_METADATA, 620);
    expect(experimental_evaluate).toHaveBeenCalledTimes(2);
    const postCheck = experimental_evaluate.mock.calls[1]?.[0] as { state: string };
    expect(postCheck.state).toContain('merged Video Pack');
    expect(runVideo).toHaveBeenCalledTimes(manifest.shards.length);
  });
});
