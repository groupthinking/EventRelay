import 'server-only';

import { hasAiGatewayKey, stripJsonCodeFence } from '@/lib/vercel-ai-gateway';
import {
  parseArchitecture,
  parseArtifacts,
  parseStack,
  truncatePackText,
  type VideoPackArchitecture,
  type VideoPackArtifact,
  type VideoPackStack,
  type VideoPackStackTool,
} from '@/lib/video-pack-types';

/** Verified Vercel AI Gateway id — do not substitute gemini-2.5-flash. */
export const VIDEO_PACK_EXTRACTOR_MODEL = 'google/gemini-3.8-flash';

export class VideoPackExtractError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'VideoPackExtractError';
  }
}

export interface ExtractedTranscriptSegment {
  idx: number;
  start_s: number;
  end_s: number;
  text: string;
}

export interface ExtractedKeyframe {
  t_s: number;
  image_path?: string | null;
  desc?: string | null;
}

export interface ExtractedRequirement {
  id: string;
  title: string;
  detail?: string | null;
  priority?: string | null;
  tags?: string[];
}

export interface ExtractedCodeSnippet {
  path_hint?: string | null;
  lang?: string | null;
  content: string;
}

export type ExtractedArchitecture = VideoPackArchitecture;
export type ExtractedArtifact = VideoPackArtifact;
export type ExtractedStack = VideoPackStack;
export type ExtractedStackTool = VideoPackStackTool;

export interface ExtractedVisualElement {
  timestamp: number;
  element_type: string;
  content: string;
  confidence?: number;
  frame_path?: string | null;
}

export interface ExtractedVisualContext {
  visual_elements: ExtractedVisualElement[];
  summary?: string | null;
  frame_analysis_count?: number;
  processing_timestamp?: string | null;
}

export interface ExtractedVideoPackSpec {
  transcript: {
    language: string | null;
    full_text: string;
    segments: ExtractedTranscriptSegment[];
  };
  keyframes: ExtractedKeyframe[];
  concepts: string[];
  requirements: ExtractedRequirement[];
  code_snippets: ExtractedCodeSnippet[];
  visual_context: ExtractedVisualContext | null;
  architecture?: ExtractedArchitecture | null;
  artifacts?: ExtractedArtifact[];
  stack?: ExtractedStack;
}

export interface VideoPackGenerateTextArgs {
  model: string;
  messages: Array<{
    role: 'user';
    content: Array<
      | { type: 'text'; text: string }
      | { type: 'file'; data: URL; mediaType: string }
    >;
  }>;
  abortSignal?: AbortSignal;
}

export type VideoPackGenerateText = (
  args: VideoPackGenerateTextArgs,
) => Promise<{ text: string }>;

const GATEWAY_MISSING_ERROR =
  'Video pack spec extract requires AI Gateway (AI_GATEWAY_API_KEY or VERCEL_AI_GATEWAY_API_KEY) and model google/gemini-3.8-flash.';

const EMPTY_SPEC_ERROR =
  'Gemini 3.8 Flash returned no extracted spec content.';

function buildExtractPrompt(sourceUrl: string, videoId: string): string {
  return [
    'You are extracting a Video Pack v0 spec from this YouTube video.',
    `source_url: ${sourceUrl}`,
    `video_id: ${videoId}`,
    'Use the attached video (frames + spoken audio). Do not invent a second pack format.',
    'Do not return cite:youtube as full_text. Extract real spoken/on-screen content.',
    'Return ONLY a JSON object with keys:',
    'transcript: { language: string|null, full_text: string, segments: [{idx, start_s, end_s, text}] }',
    'keyframes: [{ t_s, desc }]',
    'concepts: string[]',
    'requirements: [{ id, title, detail, priority, tags }]',
    'code_snippets: [{ path_hint, lang, content }] — signatures only, never a full source dump',
    'architecture: { summary, stages: [{ id, name, description }], mermaid } — pipeline/graph grounded in the video (decode → multimodal temporal Q/A → agentic build/verify → monetization rails when those appear)',
    'artifacts: [{ path_hint, purpose, interface, signatures?, stubs? }] — buildable shapes, not chat code dumps',
    'stack: { tools: [{ name, kind, evidence, docs_url, check }] } — named tools/frameworks actually grounded in spoken or on-screen evidence',
    'visual_context: { visual_elements: [{ timestamp, element_type, content, confidence }], summary, frame_analysis_count } | null',
    'Do not invent Shopify, Vercel, GitHub, or any other stack that the video does not name.',
    'If the video is Cloudflare / x402 / MCP, stack.tools must name those rails — not a storefront CLI.',
  ].join('\n');
}

function asRecord(value: unknown): Record<string, unknown> | null {
  return value !== null && typeof value === 'object' ? (value as Record<string, unknown>) : null;
}

function asString(value: unknown): string {
  return typeof value === 'string' ? value : '';
}

function asNumber(value: unknown, fallback = 0): number {
  return typeof value === 'number' && Number.isFinite(value) ? value : fallback;
}

function asStringArray(value: unknown): string[] {
  if (!Array.isArray(value)) return [];
  return value.filter((item): item is string => typeof item === 'string' && item.trim().length > 0);
}

function parseSpecJson(raw: string): ExtractedVideoPackSpec {
  const cleaned = stripJsonCodeFence(raw);
  let parsed: unknown;
  try {
    parsed = JSON.parse(cleaned);
  } catch {
    const start = cleaned.indexOf('{');
    const end = cleaned.lastIndexOf('}');
    if (start === -1 || end <= start) {
      throw new VideoPackExtractError('Gemini 3.8 Flash returned unparseable spec JSON.');
    }
    parsed = JSON.parse(cleaned.slice(start, end + 1));
  }

  const root = asRecord(parsed);
  if (!root) {
    throw new VideoPackExtractError('Gemini 3.8 Flash returned unparseable spec JSON.');
  }

  const transcript = asRecord(root.transcript) ?? {};
  const segmentsRaw = Array.isArray(transcript.segments) ? transcript.segments : [];
  const keyframesRaw = Array.isArray(root.keyframes) ? root.keyframes : [];
  const requirementsRaw = Array.isArray(root.requirements) ? root.requirements : [];
  const snippetsRaw = Array.isArray(root.code_snippets) ? root.code_snippets : [];
  const visual = asRecord(root.visual_context);
  const visualElementsRaw = Array.isArray(visual?.visual_elements) ? visual.visual_elements : [];

  return {
    transcript: {
      language: typeof transcript.language === 'string' ? transcript.language : null,
      full_text: asString(transcript.full_text).trim(),
      segments: segmentsRaw.flatMap((item, index) => {
        const row = asRecord(item);
        if (!row) return [];
        const text = asString(row.text).trim();
        if (!text) return [];
        return [
          {
            idx: asNumber(row.idx, index),
            start_s: asNumber(row.start_s),
            end_s: asNumber(row.end_s, asNumber(row.start_s)),
            text,
          },
        ];
      }),
    },
    keyframes: keyframesRaw.flatMap((item) => {
      const row = asRecord(item);
      if (!row) return [];
      const desc = asString(row.desc).trim();
      if (!desc && !asString(row.image_path).trim()) return [];
      return [
        {
          t_s: asNumber(row.t_s),
          image_path: typeof row.image_path === 'string' ? row.image_path : null,
          desc: desc || null,
        },
      ];
    }),
    concepts: asStringArray(root.concepts),
    requirements: requirementsRaw.flatMap((item, index) => {
      const row = asRecord(item);
      if (!row) return [];
      const title = asString(row.title).trim();
      if (!title) return [];
      return [
        {
          id: asString(row.id).trim() || `req-${index + 1}`,
          title,
          detail: typeof row.detail === 'string' ? row.detail : null,
          priority: typeof row.priority === 'string' ? row.priority : 'normal',
          tags: asStringArray(row.tags),
        },
      ];
    }),
    code_snippets: snippetsRaw.flatMap((item) => {
      const row = asRecord(item);
      if (!row) return [];
      const content = asString(row.content).trim();
      if (!content) return [];
      return [
        {
          path_hint: typeof row.path_hint === 'string' ? row.path_hint : null,
          lang: typeof row.lang === 'string' ? row.lang : null,
          content: truncatePackText(content),
        },
      ];
    }),
    architecture: parseArchitecture(root.architecture),
    artifacts: parseArtifacts(root.artifacts),
    stack: parseStack(root.stack),
    visual_context: visual
      ? {
          visual_elements: visualElementsRaw.flatMap((item) => {
            const row = asRecord(item);
            if (!row) return [];
            const content = asString(row.content).trim();
            if (!content) return [];
            return [
              {
                timestamp: asNumber(row.timestamp),
                element_type: asString(row.element_type).trim() || 'scene',
                content,
                confidence: typeof row.confidence === 'number' ? row.confidence : undefined,
                frame_path: typeof row.frame_path === 'string' ? row.frame_path : null,
              },
            ];
          }),
          summary: typeof visual.summary === 'string' ? visual.summary : null,
          frame_analysis_count: asNumber(visual.frame_analysis_count),
        }
      : null,
  };
}

function isIdentityOnlySpec(spec: ExtractedVideoPackSpec, videoId: string): boolean {
  const cite = `cite:youtube:${videoId}`;
  const text = spec.transcript.full_text.trim();
  const hasSpeech = text.length > 0 && text !== cite;
  const hasSpec =
    spec.concepts.length > 0 ||
    spec.requirements.length > 0 ||
    spec.keyframes.length > 0 ||
    spec.transcript.segments.length > 0 ||
    (spec.visual_context?.visual_elements.length ?? 0) > 0 ||
    (spec.architecture?.stages.length ?? 0) > 0 ||
    (spec.artifacts?.length ?? 0) > 0 ||
    (spec.stack?.tools.length ?? 0) > 0;
  return !hasSpeech && !hasSpec;
}

async function defaultGenerateText(args: VideoPackGenerateTextArgs): Promise<{ text: string }> {
  const { generateText } = await import('ai');
  const result = await generateText({
    model: args.model,
    messages: args.messages,
    abortSignal: args.abortSignal,
  });
  if (!result.text.trim()) {
    throw new VideoPackExtractError('Vercel AI Gateway returned empty content');
  }
  return { text: result.text };
}

export async function extractVideoPackSpec(
  input: { sourceUrl: string; videoId: string },
  deps: {
    generateText?: VideoPackGenerateText;
    hasGatewayKey?: () => boolean;
  } = {},
): Promise<ExtractedVideoPackSpec> {
  const hasKey = deps.hasGatewayKey ?? hasAiGatewayKey;
  if (!hasKey()) {
    throw new VideoPackExtractError(GATEWAY_MISSING_ERROR);
  }

  const generateText = deps.generateText ?? defaultGenerateText;
  const result = await generateText({
    model: VIDEO_PACK_EXTRACTOR_MODEL,
    abortSignal: AbortSignal.timeout(110_000),
    messages: [
      {
        role: 'user',
        content: [
          {
            type: 'file',
            data: new URL(input.sourceUrl),
            mediaType: 'video/mp4',
          },
          {
            type: 'text',
            text: buildExtractPrompt(input.sourceUrl, input.videoId),
          },
        ],
      },
    ],
  });

  let spec: ExtractedVideoPackSpec;
  try {
    spec = parseSpecJson(result.text);
  } catch (error) {
    if (error instanceof VideoPackExtractError) throw error;
    const message = error instanceof Error ? error.message : String(error);
    throw new VideoPackExtractError(`Gemini 3.8 Flash returned unparseable spec JSON: ${message}`);
  }

  if (isIdentityOnlySpec(spec, input.videoId)) {
    throw new VideoPackExtractError(EMPTY_SPEC_ERROR);
  }

  return spec;
}
