import { createHash } from 'node:crypto';
import { reasonEnvelope, reasonEnvelopeJson } from '@/lib/api-reason-envelope';
import { canonicalReviewContent, invalidGroundedSpec, parseGroundedSpec, sourceForGroundedSpec, type GroundedSpecRecord } from '@/lib/grounded-build-spec';
import { start } from 'workflow/api';
import { NextResponse } from 'next/server';
import { resolveVideoUrl } from '@/lib/video-url-request';
import { withWorldVercelFetch } from '@/lib/world-vercel-fetch';
import { videoPackExtractionWorkflow } from '@/workflows/video-pack-extraction';
import {
  VIDEO_PACK_EXTRACT_PIPELINE_VERSION,
  hostedExtractReasonFromDetail,
} from '@/lib/video-pack-extract-reason';
import {
  emptyPackFormation,
  type VideoPackActionItem,
  type VideoPackArchitecture,
  type VideoPackArtifact,
  type VideoPackChapter,
  type VideoPackStack,
} from '@/lib/video-pack-types';
import {
  claimPackProcessing,
  getPackRecord,
  isProcessingStale,
  putPackRecord,
  type VideoPackRecord,
} from '@/lib/video-pack-store';
import { applyKeyframeImageHonesty } from '@/lib/keyframe-image-path';
import { hydrateKeyframeImages } from '@/lib/keyframe-frame-capture';
import {
  VideoPackExtractError,
  extractVideoPackSpec,
  type ExtractedVideoPackSpec,
} from '@/lib/video-pack-extractor';
import { VIDEO_PACK_VIDEO_MODEL } from '@/lib/video-pack-shard-planner';

export {
  VIDEO_PACK_EXTRACT_PIPELINE_VERSION,
} from '@/lib/video-pack-extract-reason';

export const IDENTITY_VERSION = 'v0' as const;

/** Bump when stored packs must re-extract (e.g. Cut B1 chapters + action_items). */
export const VIDEO_PACK_STRUCTURE_SCHEMA_VERSION = 'b1-structured-v1' as const;

export {
  KEYFRAME_IMAGES_OK,
  KEYFRAME_IMAGES_OK_NOTE,
  KEYFRAME_IMAGES_OK_STILLS_NOTE,
  KEYFRAME_IMAGES_OK_STORYBOARD_NOTE,
  KEYFRAME_IMAGES_PARTIAL,
  KEYFRAME_IMAGES_PARTIAL_NOTE,
  applyKeyframeImageHonesty,
  applyKeyframeImageSourceNotes,
  sanitizeKeyframeImagePath,
} from '@/lib/keyframe-image-path';

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
  grounded_spec?: GroundedSpecRecord;
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
  architecture: VideoPackArchitecture | null;
  artifacts: VideoPackArtifact[];
  stack: VideoPackStack;
  chapters: VideoPackChapter[];
  action_items: VideoPackActionItem[];
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
    architecture: null,
    artifacts: [],
    stack: { tools: [] },
    chapters: [],
    action_items: [],
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

const SPEC_JSON_SALVAGE_NOTE =
  'Gemini spec JSON was truncated; salvage kept the verified prefix only (no invented tail fields).';

export function applyExtractedSpec(
  identity: VideoPackV0Json,
  spec: ExtractedVideoPackSpec,
): VideoPackV0Json {
  const salvaged = spec.spec_json_salvaged === true;
  const pack = applyKeyframeImageHonesty({
    ...identity,
    ...(salvaged
      ? {
          metrics: { ...identity.metrics, spec_json_salvaged: 1 },
        }
      : {}),
    transcript: spec.transcript,
    keyframes: spec.keyframes,
    concepts: spec.concepts,
    requirements: spec.requirements,
    code_snippets: spec.code_snippets,
    architecture: spec.architecture ?? emptyPackFormation().architecture,
    artifacts: spec.artifacts ?? emptyPackFormation().artifacts,
    stack: spec.stack ?? emptyPackFormation().stack,
    chapters: spec.chapters ?? emptyPackFormation().chapters,
    action_items: spec.action_items ?? emptyPackFormation().action_items,
    visual_context: spec.visual_context,
    provenance: {
      ...identity.provenance,
      tool_versions: {
        ...identity.provenance.tool_versions,
        extractor: VIDEO_PACK_VIDEO_MODEL,
        pack_structure: VIDEO_PACK_STRUCTURE_SCHEMA_VERSION,
        extract_pipeline: VIDEO_PACK_EXTRACT_PIPELINE_VERSION,
      },
      notes: salvaged
        ? `Identity pack plus Gemini 3.8 Flash spec extract via direct Interactions shards. ${SPEC_JSON_SALVAGE_NOTE}`
        : 'Identity pack plus Gemini 3.8 Flash spec extract via direct Interactions shards.',
    },
  });
  if (!spec.grounded_spec) return pack;
  if (spec.grounded_spec.status !== 'available') return { ...pack, grounded_spec: spec.grounded_spec };
  const source = sourceForGroundedSpec(pack);
  const checked = parseGroundedSpec(spec.grounded_spec.spec, pack, pack.video_id);
  if (!source || !checked || checked.status !== 'available') return {
    ...pack, grounded_spec: checked && checked.status !== 'available' ? checked : invalidGroundedSpec('Source identity is not valid for this specification.'),
  };
  const bound = { ...checked.spec, source };
  return { ...pack, grounded_spec: {
    status: 'available', spec: bound,
    contentHash: createHash('sha256').update(canonicalReviewContent(bound, pack)).digest('hex'),
  } };
}

export function isIdentityOnlyPack(pack: VideoPackV0Json): boolean {
  return pack.transcript.full_text === `cite:youtube:${pack.video_id}`;
}

/** True when a ready extracted pack predates the current structured schema (pre-B1 cache). */
export function packNeedsStructuredRefresh(pack: VideoPackV0Json): boolean {
  if (isIdentityOnlyPack(pack)) return false;
  const marked = pack.provenance.tool_versions?.pack_structure;
  return marked !== VIDEO_PACK_STRUCTURE_SCHEMA_VERSION;
}

/** True when a ready pack predates the current Gateway retry/salvage pipeline (C1). */
export function packNeedsExtractPipelineRefresh(pack: VideoPackV0Json): boolean {
  if (isIdentityOnlyPack(pack)) return false;
  const marked = pack.provenance.tool_versions?.extract_pipeline;
  return marked !== VIDEO_PACK_EXTRACT_PIPELINE_VERSION;
}

export function packNeedsReextractOnPost(pack: VideoPackV0Json): boolean {
  return packNeedsStructuredRefresh(pack) || packNeedsExtractPipelineRefresh(pack);
}

const SOURCE_HASH = /^[a-f0-9]{64}$/;

type StartVideoPackExtraction = (identity: VideoPackV0Json) => Promise<void>;

async function startDurableVideoPackExtraction(identity: VideoPackV0Json): Promise<void> {
  await withWorldVercelFetch(async () => {
    await start(videoPackExtractionWorkflow, [identity]);
  });
}

let startVideoPackExtraction: StartVideoPackExtraction = startDurableVideoPackExtraction;

export function setVideoPackWorkflowStarterForTests(
  starter: StartVideoPackExtraction | null,
): void {
  startVideoPackExtraction = starter ?? startDurableVideoPackExtraction;
}

/** @deprecated Use setVideoPackWorkflowStarterForTests in new tests. */
export function setVideoPackSchedulerForTests(schedule: ((work: Promise<unknown>) => void) | null): void {
  setVideoPackWorkflowStarterForTests(
    schedule
      ? async (identity) => { schedule(persistVideoPackExtraction(identity)); }
      : null,
  );
}

function missingIdentityResponse(gaps: readonly string[]): NextResponse {
  const listed = gaps.join(', ');
  const verb = gaps.length === 1 ? 'is' : 'are';
  return NextResponse.json(
    {
      status: 'error',
      error: `Video pack verification failed: ${listed} ${verb} required.`,
    },
    { status: 500 },
  );
}

function processingEnvelope(identity: {
  id: string;
  video_id: string;
  source_url: string;
  source_hash: string;
}) {
  return {
    status: 'processing' as const,
    data: {
      version: IDENTITY_VERSION,
      id: identity.id,
      video_id: identity.video_id,
      source_url: identity.source_url,
      provenance: { source_hash: identity.source_hash },
    },
  };
}

async function recordToResponse(record: VideoPackRecord): Promise<NextResponse> {
  switch (record.state) {
    case 'ready':
      if (isIdentityOnlyPack(record.pack)) {
        return NextResponse.json(
          { status: 'error', error: 'Gemini 3.8 Flash returned no extracted spec content.' },
          { status: 503 },
        );
      }
      const hydrated = await hydrateKeyframeImages(record.pack);
      if (JSON.stringify(hydrated.keyframes) !== JSON.stringify(record.pack.keyframes)) {
        await putPackRecord({ state: 'ready', pack: hydrated });
      }
      return NextResponse.json({ status: 'success', data: applyKeyframeImageHonesty(hydrated) });
    case 'processing':
      return NextResponse.json(
        processingEnvelope({
          id: record.id,
          video_id: record.video_id,
          source_url: record.source_url,
          source_hash: record.source_hash,
        }),
        { status: 202 },
      );
    case 'error': {
      const reason_code = hostedExtractReasonFromDetail(record.error);
      return NextResponse.json(
        reasonEnvelopeJson(reasonEnvelope(false, reason_code, record.error), {
          status: 'error',
        }),
        { status: 200 },
      );
    }
    default: {
      const _exhaustive: never = record;
      return NextResponse.json(
        { status: 'error', error: `Unhandled pack state: ${JSON.stringify(_exhaustive)}` },
        { status: 500 },
      );
    }
  }
}

function resolveIdentityFromFields(
  rawId: unknown,
  url: string,
): { identity: VideoPackV0Json } | NextResponse {
  const fromField = typeof rawId === 'string' ? resolveYouTubeVideoId(rawId) : null;
  const videoId = fromField || (url ? resolveYouTubeVideoId(url) : null);
  if (!videoId) {
    return NextResponse.json(
      { status: 'error', error: 'A YouTube URL or video id is required' },
      { status: 400 },
    );
  }
  const identity = buildIdentityPack(videoId, url || undefined);
  const gaps: string[] = [];
  if (!identity.source_url.startsWith('http')) gaps.push('source_url');
  if (!identity.provenance.source_hash) gaps.push('source_hash');
  if (gaps.length > 0) {
    return missingIdentityResponse(gaps);
  }
  return { identity };
}

export async function persistVideoPackExtraction(identity: VideoPackV0Json): Promise<{ state: 'ready' | 'error' }> {
  try {
    const spec = await extractVideoPackSpec({
      sourceUrl: identity.source_url,
      videoId: identity.video_id,
    });
    const pack = await hydrateKeyframeImages(applyExtractedSpec(identity, spec));
    if (isIdentityOnlyPack(pack)) {
      await putPackRecord({
        state: 'error',
        video_id: identity.video_id,
        source_url: identity.source_url,
        source_hash: identity.provenance.source_hash,
        id: identity.id,
        error: 'Gemini 3.8 Flash returned no extracted spec content.',
        failed_at: new Date().toISOString(),
      });
      return { state: 'error' };
    }
    await putPackRecord({ state: 'ready', pack });
    return { state: 'ready' };
  } catch (error) {
    const message =
      error instanceof VideoPackExtractError
        ? error.message
        : error instanceof Error
          ? error.message
          : 'Video pack spec extract failed.';
    console.error('[video-pack] spec extract failed:', message);
    await putPackRecord({
      state: 'error',
      video_id: identity.video_id,
      source_url: identity.source_url,
      source_hash: identity.provenance.source_hash,
      id: identity.id,
      error: message,
      failed_at: new Date().toISOString(),
    });
    return { state: 'error' };
  }
}

export async function handleIdentityPackPost(request: Request): Promise<Response> {
  let body: Record<string, unknown> | null = null;
  try {
    const parsed: unknown = await request.json();
    body = parsed !== null && typeof parsed === 'object' ? (parsed as Record<string, unknown>) : null;
  } catch {
    return NextResponse.json({ status: 'error', error: 'Invalid request body' }, { status: 400 });
  }

  const resolved = resolveIdentityFromFields(body?.video_id ?? body?.videoId, resolveVideoUrl(body));
  if (resolved instanceof NextResponse) {
    return resolved;
  }
  const { identity } = resolved;
  const sourceHash = identity.provenance.source_hash;

  const existing = await getPackRecord(sourceHash);
  const reclaimReady =
    existing?.state === 'ready' && packNeedsReextractOnPost(existing.pack);
  if (existing?.state === 'ready' && !isIdentityOnlyPack(existing.pack) && !reclaimReady) {
    return recordToResponse(existing);
  }
  if (existing?.state === 'processing' && !isProcessingStale(existing)) {
    return recordToResponse(existing);
  }
  if (existing?.state === 'error') {
    // A new POST retries after a visible failure; GET keeps serving the error.
  }

  let claimed: Awaited<ReturnType<typeof claimPackProcessing>>;
  try {
    claimed = await claimPackProcessing(
      {
        video_id: identity.video_id,
        source_url: identity.source_url,
        source_hash: sourceHash,
        id: identity.id,
      },
      new Date(),
      { reclaimReady: reclaimReady },
    );
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Video pack claim failed.';
    return NextResponse.json({ status: 'error', error: message }, { status: 503 });
  }
  if (claimed !== 'claimed') {
    return recordToResponse(claimed);
  }

  try {
    await startVideoPackExtraction(identity);
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Unable to start Video Pack extraction.';
    console.error('[video-pack] durable workflow start failed:', message);
    await putPackRecord({
      state: 'error',
      video_id: identity.video_id,
      source_url: identity.source_url,
      source_hash: sourceHash,
      id: identity.id,
      error: message,
      failed_at: new Date().toISOString(),
    });
    return NextResponse.json({ status: 'error', error: message }, { status: 503 });
  }

  return NextResponse.json(
    processingEnvelope({
      id: identity.id,
      video_id: identity.video_id,
      source_url: identity.source_url,
      source_hash: sourceHash,
    }),
    { status: 202 },
  );
}

export async function handleIdentityPackGet(request: Request): Promise<Response> {
  const url = new URL(request.url);
  const sourceHash = url.searchParams.get('source_hash')?.trim() ?? '';
  const rawId = url.searchParams.get('video_id') ?? url.searchParams.get('videoId');
  const rawUrl =
    url.searchParams.get('url') ??
    url.searchParams.get('youtubeUrl') ??
    url.searchParams.get('video_url') ??
    url.searchParams.get('videoUrl') ??
    '';

  if (sourceHash) {
    if (!SOURCE_HASH.test(sourceHash)) {
      return NextResponse.json(
        { status: 'error', error: 'source_hash must be a 64-character hex digest' },
        { status: 400 },
      );
    }
    const record = await getPackRecord(sourceHash);
    if (!record) {
      return NextResponse.json({ status: 'error', error: 'Video pack not found' }, { status: 404 });
    }
    return recordToResponse(record);
  }

  const resolved = resolveIdentityFromFields(rawId, rawUrl);
  if (resolved instanceof NextResponse) {
    return resolved;
  }
  const record = await getPackRecord(resolved.identity.provenance.source_hash);
  if (!record) {
    return NextResponse.json({ status: 'error', error: 'Video pack not found' }, { status: 404 });
  }
  return recordToResponse(record);
}
