import { describe, expect, it, vi } from 'vitest';
import type { ShardVideoInteractionRunner } from '@/lib/google-genai-video';
import { planShardManifest } from '@/lib/video-pack-shard-planner';
import {
  fanOutShardsOnProbePass,
  normalizeProbeText,
  runClipProbe,
  type ClipProbe,
} from '@/lib/video-pack-clip-probe';

const SOURCE_URL = 'https://www.youtube.com/watch?v=auJzb1D-fag';

function probeFixture(): ClipProbe {
  return {
    sourceUrl: SOURCE_URL,
    start_s: 0,
    end_s: 180,
    model: 'gemini-3.8-flash',
    prompt: 'PROBE: describe only what is visible or audible in this clip.',
    forbiddenPhrases: ['torque wrench calibration'],
    expectedPhrases: ['safety briefing'],
  };
}

function windowOnlyRunner(): ShardVideoInteractionRunner {
  return vi.fn(async () => ({
    text: 'The clip opens with a SAFETY   BRIEFING before any tools appear.',
    interactionId: 'int-probe',
  }));
}

describe('normalizeProbeText', () => {
  it('lowercases and collapses whitespace', () => {
    expect(normalizeProbeText('  Torque\nWRENCH\tCalibration ')).toBe('torque wrench calibration');
  });
});

describe('runClipProbe', () => {
  it('passes when the outside fact is absent and window evidence is present', async () => {
    const runVideo = windowOnlyRunner();
    const probe = probeFixture();
    const result = await runClipProbe(probe, runVideo);
    expect(result.passed).toBe(true);
    expect(result.leakedPhrases).toEqual([]);
    expect(result.missingPhrases).toEqual([]);
    expect(result.interactionId).toBe('int-probe');
    expect(runVideo).toHaveBeenCalledTimes(1);
    const call = vi.mocked(runVideo).mock.calls[0]?.[0];
    expect(call).toMatchObject({
      sourceUrl: SOURCE_URL,
      start_s: 0,
      end_s: 180,
      model: 'gemini-3.8-flash',
    });
  });

  it('fails closed with leaked phrases when the outside fact appears', async () => {
    const runVideo: ShardVideoInteractionRunner = vi.fn(async () => ({
      text: 'Safety briefing first. Later the host covers Torque Wrench Calibration in detail.',
      interactionId: 'int-probe',
    }));
    const result = await runClipProbe(probeFixture(), runVideo);
    expect(result.passed).toBe(false);
    expect(result.leakedPhrases).toEqual(['torque wrench calibration']);
    expect(result.missingPhrases).toEqual([]);
  });

  it('fails when window evidence is missing (vacuous output cannot pass)', async () => {
    const runVideo: ShardVideoInteractionRunner = vi.fn(async () => ({
      text: 'I could not access any video content.',
      interactionId: 'int-probe',
    }));
    const result = await runClipProbe(probeFixture(), runVideo);
    expect(result.passed).toBe(false);
    expect(result.leakedPhrases).toEqual([]);
    expect(result.missingPhrases).toEqual(['safety briefing']);
  });

  it('rejects misconfigured probes with no forbidden or expected phrases', async () => {
    const runVideo = windowOnlyRunner();
    await expect(
      runClipProbe({ ...probeFixture(), forbiddenPhrases: [] }, runVideo),
    ).rejects.toThrow(/forbidden phrase/);
    await expect(
      runClipProbe({ ...probeFixture(), expectedPhrases: [] }, runVideo),
    ).rejects.toThrow(/expected phrase/);
    expect(runVideo).not.toHaveBeenCalled();
  });
});

describe('fanOutShardsOnProbePass', () => {
  it('runs the probe first, then fans out within cap 4', async () => {
    const manifest = planShardManifest('auJzb1D-fag', SOURCE_URL, null, 1080);
    expect(manifest.shards).toHaveLength(6);
    expect(manifest.parallelCap).toBe(4);
    const order: string[] = [];
    const runVideo: ShardVideoInteractionRunner = vi.fn(async () => {
      order.push('probe');
      return { text: 'safety briefing clip content here', interactionId: 'int-probe' };
    });
    let inFlight = 0;
    let maxInFlight = 0;
    const worker = vi.fn(async (shard: { index: number }) => {
      inFlight += 1;
      maxInFlight = Math.max(maxInFlight, inFlight);
      order.push(`worker:${shard.index}`);
      await new Promise((resolve) => setTimeout(resolve, 10));
      inFlight -= 1;
      return `spec-${shard.index}`;
    });

    const { probe, results } = await fanOutShardsOnProbePass(
      manifest,
      probeFixture(),
      worker,
      runVideo,
    );

    expect(probe.passed).toBe(true);
    expect(results).toHaveLength(6);
    expect(worker).toHaveBeenCalledTimes(6);
    expect(runVideo).toHaveBeenCalledTimes(1);
    expect(order[0]).toBe('probe');
    expect(maxInFlight).toBeLessThanOrEqual(4);
    expect(maxInFlight).toBeGreaterThan(1);
  });

  it('refuses fan-out with zero worker calls when the probe fails', async () => {
    const manifest = planShardManifest('auJzb1D-fag', SOURCE_URL, null, 1080);
    const runVideo: ShardVideoInteractionRunner = vi.fn(async () => ({
      text: 'safety briefing, plus torque wrench calibration from later in the video',
      interactionId: 'int-probe',
    }));
    const worker = vi.fn(async () => 'never');

    await expect(
      fanOutShardsOnProbePass(manifest, probeFixture(), worker, runVideo),
    ).rejects.toThrow(/refusing fan-out/);
    expect(runVideo).toHaveBeenCalledTimes(1);
    expect(worker).not.toHaveBeenCalled();
  });
});

/**
 * [LIVE] Optional real-model clip proof. Skipped unless LIVE_CLIP_PROBE=1.
 * Spends real Gemini tokens and REQUIRES a human-verified outside fact for
 * the target window — the fixture phrases below are placeholders until an
 * operator verifies them against the actual video. Never runs in CI.
 */
describe.skipIf(process.env.LIVE_CLIP_PROBE !== '1')('[LIVE] real-model clip enforcement', () => {
  it(
    'outside-range fact is absent from a real 180s call',
    async () => {
      if (!process.env.GEMINI_API_KEY && !process.env.GOOGLE_API_KEY) {
        throw new Error('LIVE_CLIP_PROBE=1 requires GEMINI_API_KEY (no live call made).');
      }
      const { runShardVideoInteraction } = await import('@/lib/google-genai-video');
      const result = await runClipProbe(
        {
          sourceUrl: process.env.LIVE_CLIP_PROBE_URL ?? SOURCE_URL,
          start_s: Number(process.env.LIVE_CLIP_PROBE_START ?? 0),
          end_s: Number(process.env.LIVE_CLIP_PROBE_END ?? 180),
          model: 'gemini-3.8-flash',
          prompt: 'Describe only what is visible or audible in this clip.',
          forbiddenPhrases: (process.env.LIVE_CLIP_PROBE_FORBIDDEN ?? '').split('|').filter(Boolean),
          expectedPhrases: (process.env.LIVE_CLIP_PROBE_EXPECTED ?? '').split('|').filter(Boolean),
        },
        runShardVideoInteraction,
      );
      expect(result.passed).toBe(true);
    },
    120_000,
  );
});
