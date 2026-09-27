import 'server-only';

import {
  planVideoPackExtractSections,
  VIDEO_PACK_CHUNK_MAX_PARALLEL,
  type VideoPackExtractSection,
} from '@/lib/video-pack-extract-segments';
import type { YouTubeMetadata } from '@/lib/youtube-metadata';

/** Direct Google GenAI SDK model id for visual shard workers (no gateway prefix). */
export const VIDEO_PACK_VIDEO_MODEL = 'gemini-3.8-flash';

/** Maximum tolerated shard-boundary overlap/pad, in seconds. */
export const SHARD_MANIFEST_MAX_PAD_SECONDS = 1;

/**
 * One provider-enforced temporal shard. A visual worker receives ONLY
 * `{ sourceUrl, start_s, end_s }` — never the full video with a
 * "focus on range X–Y" instruction (that pattern is O(shards × full
 * video) and is forbidden).
 */
export interface VideoShard {
  index: number;
  start_s: number;
  end_s: number;
  topic: string;
  model: string;
  reason: string;
}

/**
 * Planner output. Emitted BEFORE any Gemini video call, from metadata only.
 */
export interface ShardManifest {
  videoId: string;
  sourceUrl: string;
  durationSeconds: number;
  shards: VideoShard[];
  /** Bounded parallel workers (never above VIDEO_PACK_CHUNK_MAX_PARALLEL). */
  parallelCap: number;
  model: string;
  /** Sum of assigned shard seconds. Must stay ≤ costBoundUnits. */
  costUnits: number;
  /** Cost bound in shard-seconds. Default: 1× duration (forbids N×full-video fan-out). */
  costBoundUnits: number;
  plannedAt: string;
}

export interface ShardPlanOptions {
  maxWorkers?: number;
  costBoundUnits?: number;
}

/**
 * Optional Jev/planner decisions. Injected, never live-called here:
 * Jev live-eval stays OFF until explicitly authorized (TODO(open-item)).
 * When absent, the deterministic metadata planner below is authoritative.
 */
export interface ShardPlanDecisions {
  maxWorkers?: number;
  costBoundUnits?: number;
}

function sectionToShard(
  section: VideoPackExtractSection,
  model: string,
  fromChapters: boolean,
): VideoShard {
  return {
    index: section.index,
    start_s: section.start_s,
    end_s: section.end_s,
    topic: section.topic,
    model,
    reason: fromChapters
      ? `chapter boundary "${section.topic}"`
      : `fixed ${section.end_s - section.start_s}s window`,
  };
}

/**
 * Plan the shard manifest from metadata only. Deterministic; no model calls.
 * Reuses the existing section planner so chapter/window behavior is unchanged.
 */
export function planShardManifest(
  videoId: string,
  sourceUrl: string,
  metadata: YouTubeMetadata | null,
  durationSeconds: number | null,
  options: ShardPlanOptions = {},
  decisions?: ShardPlanDecisions,
): ShardManifest {
  const duration = durationSeconds && durationSeconds > 0 ? durationSeconds : 0;
  const sections = planVideoPackExtractSections(metadata, durationSeconds);
  const fromChapters = (metadata?.chapters.length ?? 0) >= 2 && sections.length >= 2 &&
    sections.some((s) => s.topic !== 'full' && !s.topic.startsWith('Part '));
  const shards = sections.map((s) => sectionToShard(s, VIDEO_PACK_VIDEO_MODEL, fromChapters));
  const parallelCap = Math.min(
    decisions?.maxWorkers ?? options.maxWorkers ?? VIDEO_PACK_CHUNK_MAX_PARALLEL,
    VIDEO_PACK_CHUNK_MAX_PARALLEL,
  );
  const costUnits = shards.reduce((sum, s) => sum + Math.max(0, s.end_s - s.start_s), 0);
  // Unknown duration (metadata fetch failed): bound to the single planned
  // range so the check stays meaningful instead of failing every degraded
  // extract. Coverage rules below are vacuous at duration 0 by design.
  const costBoundUnits =
    decisions?.costBoundUnits ?? options.costBoundUnits ?? (duration > 0 ? duration : costUnits);
  return {
    videoId,
    sourceUrl,
    durationSeconds: duration,
    shards,
    parallelCap: Math.max(1, parallelCap),
    model: VIDEO_PACK_VIDEO_MODEL,
    costUnits,
    costBoundUnits,
    plannedAt: new Date().toISOString(),
  };
}

export interface ManifestValidation {
  /** Application-owned 0/1. 1 only when every requirement below holds. */
  ok: 0 | 1;
  /** Specific missing/invalid requirements. Empty when ok is 1. */
  failures: string[];
}

/**
 * App 0/1 coverage checkpoint. Pure predicate over the manifest — no models.
 * Downstream stages may only consume manifests that validate to 1.
 */
export function validateShardManifest(manifest: ShardManifest): ManifestValidation {
  const failures: string[] = [];
  const { shards, durationSeconds } = manifest;

  if (shards.length === 0) {
    failures.push('manifest has no shards');
  }

  const ordered = [...shards].sort((a, b) => a.index - b.index);
  for (const [position, shard] of ordered.entries()) {
    if (shard.index !== position) {
      failures.push(`shard index ${shard.index} breaks 0-based ordering at position ${position}`);
    }
    if (!(shard.start_s >= 0)) {
      failures.push(`shard ${shard.index} has negative start_s ${shard.start_s}`);
    }
    if (!(shard.end_s > shard.start_s)) {
      failures.push(`shard ${shard.index} has non-positive range ${shard.start_s}–${shard.end_s}`);
    }
    if (!shard.topic || shard.topic.trim().length === 0) {
      failures.push(`shard ${shard.index} has an empty topic`);
    }
  }

  if (durationSeconds > 0 && ordered.length > 0) {
    const first = ordered[0];
    if (first.start_s > SHARD_MANIFEST_MAX_PAD_SECONDS) {
      failures.push(
        `coverage gap at head: first shard starts at ${first.start_s}s (pad allows ≤${SHARD_MANIFEST_MAX_PAD_SECONDS}s)`,
      );
    }
    const last = ordered[ordered.length - 1];
    if (durationSeconds - last.end_s > SHARD_MANIFEST_MAX_PAD_SECONDS) {
      failures.push(
        `coverage gap at tail: last shard ends at ${last.end_s}s of ${durationSeconds}s (pad allows ≤${SHARD_MANIFEST_MAX_PAD_SECONDS}s)`,
      );
    }
    for (let i = 1; i < ordered.length; i += 1) {
      const prev = ordered[i - 1];
      const cur = ordered[i];
      const gap = cur.start_s - prev.end_s;
      if (gap > SHARD_MANIFEST_MAX_PAD_SECONDS) {
        failures.push(`coverage gap of ${gap}s between shard ${prev.index} and shard ${cur.index}`);
      }
      if (gap < -SHARD_MANIFEST_MAX_PAD_SECONDS) {
        failures.push(
          `overlap of ${-gap}s between shard ${prev.index} and shard ${cur.index} exceeds ${SHARD_MANIFEST_MAX_PAD_SECONDS}s pad`,
        );
      }
    }
  }

  if (manifest.parallelCap < 1 || manifest.parallelCap > VIDEO_PACK_CHUNK_MAX_PARALLEL) {
    failures.push(
      `parallelCap ${manifest.parallelCap} is outside 1..${VIDEO_PACK_CHUNK_MAX_PARALLEL}`,
    );
  }

  if (manifest.costUnits - manifest.costBoundUnits > 0) {
    failures.push(
      `cost ${manifest.costUnits}s exceeds bound ${manifest.costBoundUnits}s (full-video × N fan-out is forbidden)`,
    );
  }

  if (manifest.model !== VIDEO_PACK_VIDEO_MODEL) {
    failures.push(`model ${manifest.model} is not the pinned ${VIDEO_PACK_VIDEO_MODEL}`);
  }

  return { ok: failures.length === 0 ? 1 : 0, failures };
}
