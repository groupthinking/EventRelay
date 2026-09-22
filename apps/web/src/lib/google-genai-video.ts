import 'server-only';

import { GoogleGenAI } from '@google/genai';

/**
 * Direct Google GenAI video path (Gate 1, locked 2026-09-21).
 *
 * Visual shard workers call `client.interactions.create()` with a YouTube
 * URL plus provider-enforced `start_offset` / `end_offset`. Video NEVER
 * goes through the Vercel AI Gateway; the gateway stays for
 * transcript/chat/consolidation only.
 *
 * Fail-closed: an invalid range, a missing key, or an empty model
 * response throws. There is deliberately NO full-video fallback —
 * silently dropping the clip would reintroduce O(shards × full video).
 */

/** Worker contract: narrowed range only, never full-video-by-default. */
export interface ShardVideoCall {
  sourceUrl: string;
  start_s: number;
  end_s: number;
  model: string;
  systemInstruction: string;
  sectionPrompt: string;
  /** Frames/sec sampling density. Defaults to 1 (cost control). */
  fps?: number;
}

export interface ShardVideoResult {
  text: string;
  interactionId: string | null;
}

/** Minimal structural boundary for the Interactions SDK (mocked in tests). */
export interface ShardVideoBlock {
  type: 'video';
  uri: string;
  mime_type: string;
  processing: { type: 'static'; start_offset: string; end_offset: string; fps: number };
}

export interface ShardTextBlock {
  type: 'text';
  text: string;
}

export interface InteractionsClient {
  interactions: {
    create: (params: {
      model: string;
      input: Array<ShardVideoBlock | ShardTextBlock>;
    }) => Promise<{ output_text?: string | undefined; id?: string | undefined }>;
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

function assertValidRange(call: ShardVideoCall): void {
  if (!(call.start_s >= 0) || !(call.end_s > call.start_s)) {
    throw new Error(
      `Invalid shard range ${call.start_s}–${call.end_s}: refusing full-video fallback`,
    );
  }
  if (!call.sourceUrl.startsWith('http')) {
    throw new Error('Shard video call requires an http(s) sourceUrl');
  }
}

export function buildShardInteractionInput(
  call: ShardVideoCall,
): Array<ShardVideoBlock | ShardTextBlock> {
  assertValidRange(call);
  return [
    {
      type: 'video',
      uri: call.sourceUrl,
      mime_type: 'video/mp4',
      processing: {
        type: 'static',
        start_offset: secondsToOffset(call.start_s),
        end_offset: secondsToOffset(call.end_s),
        fps: call.fps ?? 1,
      },
    },
    { type: 'text', text: `${call.systemInstruction}\n\n${call.sectionPrompt}` },
  ];
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
  const interaction = await client.interactions.create({
    model: call.model,
    input: buildShardInteractionInput(call),
  });
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
