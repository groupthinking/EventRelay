import 'server-only';

import {
  runShardVideoInteraction,
  type ShardVideoInteractionRunner,
} from '@/lib/google-genai-video';
import { mapWithBoundedConcurrency } from '@/lib/video-pack-extract-segments';
import type { ShardManifest, VideoShard } from '@/lib/video-pack-shard-planner';
import { VideoPackExtractError } from '@/lib/video-pack-extractor';

/**
 * Gate 3 clip probe (locked scope 2026-09-22).
 *
 * Proves provider-enforced clipping with ONE Interactions call on a known
 * window: a fact that exists ONLY outside the window MUST be absent from
 * the model output. If it appears, the probe fails and fan-out is refused
 * (zero worker calls). An expected inside-window phrase is also required,
 * so vacuous/empty output cannot pass.
 *
 * Claim ≠ PASS: the probe LOGIC (detection + fail-closed gating) is proven
 * by unit tests with an injected runner. Whether Gemini honors the clip on
 * a real video is proven only by the flagged live script
 * (scripts/clip-probe-live.mjs) — never by these tests alone.
 */

export interface ClipProbe {
  sourceUrl: string;
  start_s: number;
  end_s: number;
  model: string;
  /** Prompt for the single probe call (window description request). */
  prompt: string;
  /** Phrases known to exist ONLY outside [start_s, end_s]. Must be absent. */
  forbiddenPhrases: string[];
  /** Phrases known to exist INSIDE [start_s, end_s]. Must be present. */
  expectedPhrases: string[];
}

export interface ClipProbeResult {
  passed: boolean;
  /** Forbidden phrases found in the output (empty when passed). */
  leakedPhrases: string[];
  /** Expected phrases missing from the output (empty when passed). */
  missingPhrases: string[];
  interactionId: string | null;
}

export function normalizeProbeText(text: string): string {
  return text.toLowerCase().replace(/\s+/g, ' ').trim();
}

function findPhrases(haystack: string, phrases: string[]): string[] {
  const normalized = normalizeProbeText(haystack);
  return phrases.filter((phrase) => {
    const needle = normalizeProbeText(phrase);
    return needle.length > 0 && normalized.includes(needle);
  });
}

/**
 * Run one clipped probe call. Never throws on a model-content verdict —
 * failure is data (passed:false), so callers can refuse fan-out cleanly.
 * Transport errors from the runner propagate to the caller.
 */
export async function runClipProbe(
  probe: ClipProbe,
  runVideoInteraction: ShardVideoInteractionRunner = runShardVideoInteraction,
): Promise<ClipProbeResult> {
  if (probe.forbiddenPhrases.length === 0) {
    throw new VideoPackExtractError('Clip probe requires at least one forbidden phrase.');
  }
  if (probe.expectedPhrases.length === 0) {
    throw new VideoPackExtractError('Clip probe requires at least one expected phrase.');
  }
  const result = await runVideoInteraction({
    sourceUrl: probe.sourceUrl,
    start_s: probe.start_s,
    end_s: probe.end_s,
    model: probe.model,
    systemInstruction:
      'You are a precise video-evidence extractor. The attached clip is your entire observable universe: describe only what is visible or audible inside its seconds and never claim coverage outside them.',
    sectionPrompt: probe.prompt,
  });
  const leakedPhrases = findPhrases(result.text, probe.forbiddenPhrases);
  const foundExpected = findPhrases(result.text, probe.expectedPhrases);
  const missingPhrases = probe.expectedPhrases.filter((phrase) => {
    const needle = normalizeProbeText(phrase);
    return (
      needle.length > 0 &&
      !foundExpected.some((found) => normalizeProbeText(found) === needle)
    );
  });
  return {
    passed: leakedPhrases.length === 0 && missingPhrases.length === 0,
    leakedPhrases,
    missingPhrases,
    interactionId: result.interactionId,
  };
}

export type ShardWorker<T> = (shard: VideoShard, index: number) => Promise<T>;

/**
 * Probe-gated fan-out: runs the probe first; on failure throws WITHOUT
 * calling any worker. Cap stays at the manifest parallelCap (≤ 4).
 */
export async function fanOutShardsOnProbePass<T>(
  manifest: ShardManifest,
  probe: ClipProbe,
  worker: ShardWorker<T>,
  runVideoInteraction: ShardVideoInteractionRunner = runShardVideoInteraction,
): Promise<{ probe: ClipProbeResult; results: T[] }> {
  const probeResult = await runClipProbe(probe, runVideoInteraction);
  if (!probeResult.passed) {
    const reasons = [
      ...probeResult.leakedPhrases.map((p) => `outside-range leak: "${p}"`),
      ...probeResult.missingPhrases.map((p) => `window evidence missing: "${p}"`),
    ];
    throw new VideoPackExtractError(
      `Clip probe failed, refusing fan-out: ${reasons.join('; ')}`,
    );
  }
  const results = await mapWithBoundedConcurrency(
    manifest.shards,
    manifest.parallelCap,
    async (shard, index) => worker(shard, index),
  );
  return { probe: probeResult, results };
}
