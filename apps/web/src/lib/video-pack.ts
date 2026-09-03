import { createHash } from 'node:crypto';
import { NextResponse } from 'next/server';
import { resolveVideoUrl } from '@/lib/video-url-request';
import {
  VIDEO_PACK_EXTRACTOR_MODEL,
  VideoPackExtractError,
  extractVideoPackSpec,
  type ExtractedVideoPackSpec,
} from '@/lib/video-pack-extractor';

export const IDENTITY_VERSION = 'v0' as const;

export const GOLDEN_IDENTITY_HASHES = {
  'auJzb1D-fag': '2778c5fc08a1b7f19fe0a83bca959e24ecf20040c3cc1a3b6edd244d68c5e4ea',
  'jNQXAC9IVRw': '97150a5c21eef3d12a4543ce2108ca28fd6f829db1da120d7e75655ab471f97d',
} as const;

export interface VideoPackProvenance {
  created_at: string;
  tool_versions: Record<string, string>;
  source_hash: string;
  notes: string;
}

export interface VideoPackTranscriptSegment {
  idx: number;
  start_s: number;
  end_s: number;
  text: string;
}

export interface VideoPackKeyframe {
  t_s: number;
  image_path?: string | null;
  desc?: string | null;
}

export interface VideoPackRequirement {
  id: string;
  title: string;
  detail?: string | null;
  priority?: string | null;
  tags?: string[];
}

export interface VideoPackCodeSnippet {
  path_hint?: string | null;
  lang?: string | null;
  content: string;
}

export interface VideoPackVisualElement {
  timestamp: number;
  element_type: string;
  content: string;
  confidence?: number;
  frame_path?: string | null;
}

export interface VideoPackVisualContext {
  visual_elements: VideoPackVisualElement[];
  summary?: string | null;
  frame_analysis_count?: number;
  processing_timestamp?: string | null;
}

export interface VideoPackV0Json {
  version: typeof IDENTITY_VERSION;
  id: string;
  video_id: string;
  source_url: string;
  transcript: {
    language: string | null;
    full_text: string;
    segments: VideoPackTranscriptSegment[];
  };
  keyframes: VideoPackKeyframe[];
  concepts: string[];
  requirements: VideoPackRequirement[];
  code_snippets: VideoPackCodeSnippet[];
  artifacts: Array<Record<string, unknown>>;
  visual_context: VideoPackVisualContext | null;
  metrics: Record<string, number | string>;
  provenance: VideoPackProvenance;
}

export function identityPayload(videoId: string, version: string = IDENTITY_VERSION) {
  return { version, video_id: videoId };
}

export function canonicalIdentityJson(videoId: string, version: string = IDENTITY_VERSION): string {
  const payload = identityPayload(videoId, version);
  const sorted: Record<string, string> = {};
  for (const key of Object.keys(payload).sort()) {
    sorted[key] = payload[key as keyof typeof payload];
  }
  return JSON.stringify(sorted);
}

export function identityHash(videoId: string, version: string = IDENTITY_VERSION): string {
  return createHash('sha256').update(canonicalIdentityJson(videoId, version)).digest('hex');
}

export function resolveYouTubeVideoId(urlOrId: string): string | null {
  const trimmed = urlOrId.trim();
  if (/^[A-Za-z0-9_-]{11}$/.test(trimmed)) {
    return trimmed;
  }
  const patterns = [
    /(?:youtube\.com\/watch\?v=)([A-Za-z0-9_-]{11})/,
    /(?:youtu\.be\/)([A-Za-z0-9_-]{11})/,
    /(?:youtube\.com\/embed\/)([A-Za-z0-9_-]{11})/,
    /(?:youtube\.com\/shorts\/)([A-Za-z0-9_-]{11})/,
    /(?:youtube\.com\/v\/)([A-Za-z0-9_-]{11})/,
  ];
  for (const pattern of patterns) {
    const match = trimmed.match(pattern);
    if (match) {
      return match[1];
    }
  }
  return null;
}

export function buildIdentityPack(videoId: string, sourceUrl?: string, createdAt?: string): VideoPackV0Json {
  const source_url =
    sourceUrl && sourceUrl.startsWith('http')
      ? sourceUrl
      : `https://www.youtube.com/watch?v=${videoId}`;
  return {
    version: IDENTITY_VERSION,
    id: `vp:${IDENTITY_VERSION}:${videoId}`,
    video_id: videoId,
    source_url,
    transcript: { language: null, full_text: `cite:youtube:${videoId}`, segments: [] },
    keyframes: [],
    concepts: [],
    requirements: [],
    code_snippets: [],
    artifacts: [],
    visual_context: null,
    metrics: {},
    provenance: {
      created_at: createdAt ?? new Date().toISOString(),
      tool_versions: { videopack: IDENTITY_VERSION },
      source_hash: identityHash(videoId),
      notes: 'Identity pack. Content extract is a later step.',
    },
  };
}

export function applyExtractedSpec(
  identity: VideoPackV0Json,
  spec: ExtractedVideoPackSpec,
): VideoPackV0Json {
  return {
    ...identity,
    transcript: spec.transcript,
    keyframes: spec.keyframes,
    concepts: spec.concepts,
    requirements: spec.requirements,
    code_snippets: spec.code_snippets,
    visual_context: spec.visual_context,
    provenance: {
      ...identity.provenance,
      tool_versions: {
        ...identity.provenance.tool_versions,
        extractor: VIDEO_PACK_EXTRACTOR_MODEL,
      },
      notes: 'Identity pack plus Gemini 3.8 Flash spec extract via AI Gateway.',
    },
  };
}

export function isIdentityOnlyPack(pack: VideoPackV0Json): boolean {
  return pack.transcript.full_text === `cite:youtube:${pack.video_id}`;
}

const packs = new Map<string, VideoPackV0Json>();

function getCachedSpecPack(videoId: string): VideoPackV0Json | undefined {
  const existing = packs.get(videoId);
  if (existing && !isIdentityOnlyPack(existing)) {
    return existing;
  }
  return undefined;
}

export async function handleIdentityPackPost(request: Request): Promise<Response> {
  let body: Record<string, unknown> | null = null;
  try {
    const parsed: unknown = await request.json();
    body = parsed !== null && typeof parsed === 'object' ? (parsed as Record<string, unknown>) : null;
  } catch {
    return NextResponse.json({ status: 'error', error: 'Invalid request body' }, { status: 400 });
  }

  const url = resolveVideoUrl(body);
  const rawId = body?.video_id ?? body?.videoId;
  const fromField = typeof rawId === 'string' ? resolveYouTubeVideoId(rawId) : null;
  const videoId = fromField || (url ? resolveYouTubeVideoId(url) : null);

  if (!videoId) {
    return NextResponse.json(
      { status: 'error', error: 'A YouTube URL or video id is required' },
      { status: 400 },
    );
  }

  const identity = buildIdentityPack(videoId, url || undefined);
  if (!identity.source_url.startsWith('http') || !identity.provenance.source_hash) {
    return NextResponse.json(
      {
        status: 'error',
        error: 'Video pack verification failed: source_url and source_hash are required.',
      },
      { status: 500 },
    );
  }

  const cached = getCachedSpecPack(videoId);
  if (cached) {
    return NextResponse.json({ status: 'success', data: cached });
  }

  let spec: ExtractedVideoPackSpec;
  try {
    spec = await extractVideoPackSpec({
      sourceUrl: identity.source_url,
      videoId,
    });
  } catch (error) {
    const message =
      error instanceof VideoPackExtractError
        ? error.message
        : error instanceof Error
          ? error.message
          : 'Video pack spec extract failed.';
    console.error('[video-pack] spec extract failed:', message);
    return NextResponse.json({ status: 'error', error: message }, { status: 503 });
  }

  const pack = applyExtractedSpec(identity, spec);
  packs.set(videoId, pack);
  return NextResponse.json({ status: 'success', data: pack });
}
