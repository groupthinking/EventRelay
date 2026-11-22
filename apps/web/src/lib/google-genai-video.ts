import 'server-only';

import { GoogleGenAI } from '@google/genai';
import { canonicalYouTubeSource, resolveYouTubeSourceId } from '@/lib/video-source-identity';

/**
 * Direct Google GenAI video path (Gate 1, locked 2026-09-21).
 *
 * Short clips call `client.interactions.create()` with a YouTube URL plus
 * provider-enforced `start_offset` / `end_offset`. A long video is one
 * Interactions call with `processing: "agentic"` and
 * `generation_config.thinking_level: "high"` on the same model. Video NEVER
 * goes through the Vercel AI Gateway; the gateway stays for
 * transcript/chat/consolidation only.
 *
 * Fail-closed: an invalid range, a missing key, an empty model response,
 * or an SDK rejection of agentic processing throws. There is deliberately
 * NO static full-video fallback — that ingest is the cost agentic mode
 * exists to avoid.
 */

/** High is the thinking tier for the agentic long-video call. Not a second model id. */
export const AGENTIC_VIDEO_THINKING_LEVEL = 'high' as const;

export type ShardVideoProcessing = 'static' | 'agentic';

/** Worker contract. Static calls are a narrowed range. Agentic calls span the full URL. */
export interface ShardVideoCall {
  sourceUrl: string;
  start_s: number;
  end_s: number;
  model: string;
  systemInstruction: string;
  sectionPrompt: string;
  /**
   * Omitted or `static`: clipped frames. `agentic`: one full-URL call, no offsets and no fps.
   */
  processing?: ShardVideoProcessing;
  /** Frames/sec sampling density for static calls. Defaults to 1 (cost control). Ignored when agentic. */
  fps?: number;
}

export interface ShardVideoResult {
  text: string;
  interactionId: string | null;
}

/** Minimal structural boundary for the Interactions SDK (mocked in tests). */
export interface StaticShardVideoBlock {
  type: 'video';
  uri: string;
  mime_type: string;
  processing: { type: 'static'; start_offset: string; end_offset: string; fps: number };
}

export interface AgenticShardVideoBlock {
  type: 'video';
  uri: string;
  mime_type: 'video/mp4';
  processing: 'agentic';
}

export type ShardVideoBlock = StaticShardVideoBlock | AgenticShardVideoBlock;

export interface ShardTextBlock {
  type: 'text';
  text: string;
}

export interface ShardInteractionCreateParams {
  model: string;
  input: Array<ShardVideoBlock | ShardTextBlock>;
  generation_config?: { thinking_level: typeof AGENTIC_VIDEO_THINKING_LEVEL };
}

export interface InteractionsClient {
  interactions: {
    create: (
      params: ShardInteractionCreateParams,
    ) => Promise<{ output_text?: string | undefined; id?: string | undefined }>;
  };
}

export type ShardVideoInteractionRunner = (call: ShardVideoCall) => Promise<ShardVideoResult>;

/** Direct Google key only. Never the gateway key, never Vertex here. */
export function resolveDirectGoogleKey(): string {
  return process.env.GEMINI_API_KEY || process.env.GOOGLE_API_KEY || '';
}

export function hasDirectGoogleKey(): boolean {
  return resolveDirectGoogleKey().length > 0;
}

/** `10.5` → `"10.5s"`. Offsets are decimal seconds + `s` suffix. */
export function secondsToOffset(seconds: number): string {
  if (!Number.isFinite(seconds) || seconds < 0) {
    throw new Error(`Invalid shard offset seconds: ${seconds}`);
  }
  return `${seconds}s`;
}

function resolveVideoProcessing(
  processing: ShardVideoCall['processing'],
): ShardVideoProcessing {
  switch (processing) {
    case 'agentic':
      return 'agentic';
    case 'static':
    case undefined:
      return 'static';
    default: {
      const unexpected: never = processing;
      throw new Error(`Unexpected video processing ${String(unexpected)}`);
    }
  }
}

function assertValidRange(call: ShardVideoCall): void {
  if (!(call.start_s >= 0) || !(call.end_s > call.start_s)) {
    throw new Error(
      `Invalid shard range ${call.start_s}–${call.end_s}: refusing full-video fallback`,
    );
  }
  // #2214: the provider sink accepts only the canonical YouTube watch URL,
  // never a caller-preserved input URL, whatever the upstream path did.
  const videoId = resolveYouTubeSourceId(call.sourceUrl);
  if (!videoId || call.sourceUrl !== canonicalYouTubeSource(videoId)) {
    throw new Error('Shard video call requires a canonical YouTube watch sourceUrl');
  }
  if (resolveVideoProcessing(call.processing) === 'static') {
    resolveShardFps(call.fps);
  }
}

/** Max frames/sec a shard may request; Gemini's default sampling is 1. */
export const SHARD_VIDEO_MAX_FPS = 5;

/** `undefined` → 1. Rejects NaN, ±Infinity, ≤0 and anything above the cap. */
export function resolveShardFps(fps: number | undefined): number {
  if (fps === undefined) return 1;
  if (typeof fps !== 'number' || !Number.isFinite(fps) || fps <= 0 || fps > SHARD_VIDEO_MAX_FPS) {
    throw new Error(`Invalid shard fps ${String(fps)}: must be finite, > 0 and ≤ ${SHARD_VIDEO_MAX_FPS}`);
  }
  return fps;
}

export function buildShardInteractionInput(
  call: ShardVideoCall,
): Array<ShardVideoBlock | ShardTextBlock> {
  assertValidRange(call);
  const text: ShardTextBlock = {
    type: 'text',
    text: `${call.systemInstruction}\n\n${call.sectionPrompt}`,
  };
  const processing = resolveVideoProcessing(call.processing);
  const video: ShardVideoBlock =
    processing === 'agentic'
      ? {
          type: 'video',
          uri: call.sourceUrl,
          mime_type: 'video/mp4',
          processing: 'agentic',
        }
      : {
          type: 'video',
          uri: call.sourceUrl,
          mime_type: 'video/mp4',
          processing: {
            type: 'static',
            start_offset: secondsToOffset(call.start_s),
            end_offset: secondsToOffset(call.end_s),
            fps: resolveShardFps(call.fps),
          },
        };
  return [video, text];
}

/** Model, input, and — for the agentic call only — thinking level high. */
export function buildShardInteractionCreateParams(
  call: ShardVideoCall,
): ShardInteractionCreateParams {
  const input = buildShardInteractionInput(call);
  if (resolveVideoProcessing(call.processing) === 'agentic') {
    return {
      model: call.model,
      input,
      generation_config: { thinking_level: AGENTIC_VIDEO_THINKING_LEVEL },
    };
  }
  return { model: call.model, input };
}

let memoizedClient: GoogleGenAI | null = null;

function defaultClient(apiKey: string): InteractionsClient {
  if (!memoizedClient) {
    memoizedClient = new GoogleGenAI({ apiKey });
  }
  const sdk = memoizedClient;
  return {
    interactions: {
      create: async (params) => {
        const interaction = await sdk.interactions.create({
          model: params.model,
          input: params.input,
          ...(params.generation_config
            ? { generation_config: params.generation_config }
            : {}),
          stream: false,
        });
        return { output_text: interaction.output_text, id: interaction.id };
      },
    },
  };
}

/**
 * Run one clipped shard interaction. `deps.client` injects a stub in tests;
 * production always constructs the direct GoogleGenAI client (never gateway).
 */
export async function runShardVideoInteraction(
  call: ShardVideoCall,
  deps: { client?: InteractionsClient; apiKey?: string } = {},
): Promise<ShardVideoResult> {
  assertValidRange(call);
  const client = deps.client ?? defaultClient(resolveDirectGoogleKey());
  const interaction = await client.interactions.create(buildShardInteractionCreateParams(call));
  const text = typeof interaction.output_text === 'string' ? interaction.output_text : '';
  if (text.trim().length === 0) {
    throw new Error(
      `Empty interaction output for shard ${call.start_s}–${call.end_s}: refusing to continue without evidence`,
    );
  }
  return {
    text,
    interactionId: typeof interaction.id === 'string' ? interaction.id : null,
  };
}
