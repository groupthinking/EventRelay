import { NextResponse } from 'next/server';
import { sandboxFromVideoPack } from '@/lib/emit-app-builder-sandbox';
import { resolveVideoUrl } from '@/lib/video-url-request';
import {
  buildIdentityPack,
  isIdentityOnlyPack,
  resolveYouTubeVideoId,
  type VideoPackV0Json,
} from '@/lib/video-pack';
import { getPackRecord, type VideoPackRecord } from '@/lib/video-pack-store';

const SOURCE_HASH = /^[a-f0-9]{64}$/;

const MISSING_PACK =
  'Video pack not found. POST /api/video/pack with the same YouTube URL first, then materialize this sandbox.';

function processingEnvelope(identity: {
  id: string;
  video_id: string;
  source_url: string;
  source_hash: string;
}) {
  return {
    status: 'processing' as const,
    data: {
      id: identity.id,
      video_id: identity.video_id,
      source_url: identity.source_url,
      provenance: { source_hash: identity.source_hash },
    },
  };
}

function recordToResponse(record: VideoPackRecord): NextResponse {
  switch (record.state) {
    case 'ready':
      if (isIdentityOnlyPack(record.pack)) {
        return NextResponse.json(
          { status: 'error', error: 'Gemini 3.8 Flash returned no extracted spec content.' },
          { status: 503 },
        );
      }
      return NextResponse.json({ status: 'success', data: sandboxFromVideoPack(record.pack) });
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
    case 'error':
      return NextResponse.json({ status: 'error', error: record.error }, { status: 503 });
    default: {
      const unexpected: never = record;
      return NextResponse.json(
        { status: 'error', error: `Unhandled pack state: ${JSON.stringify(unexpected)}` },
        { status: 500 },
      );
    }
  }
}

async function sandboxFromIdentity(identity: VideoPackV0Json): Promise<NextResponse> {
  const record = await getPackRecord(identity.provenance.source_hash);
  if (!record) {
    return NextResponse.json({ status: 'error', error: MISSING_PACK }, { status: 404 });
  }
  return recordToResponse(record);
}

function resolveIdentity(
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
  return { identity: buildIdentityPack(videoId, url || undefined) };
}

export async function handleAppBuilderSandboxGet(request: Request): Promise<Response> {
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
      return NextResponse.json({ status: 'error', error: MISSING_PACK }, { status: 404 });
    }
    return recordToResponse(record);
  }

  const resolved = resolveIdentity(rawId, rawUrl);
  if (resolved instanceof NextResponse) {
    return resolved;
  }
  return sandboxFromIdentity(resolved.identity);
}

export async function handleAppBuilderSandboxPost(request: Request): Promise<Response> {
  let body: Record<string, unknown> | null = null;
  try {
    const parsed: unknown = await request.json();
    body = parsed !== null && typeof parsed === 'object' ? (parsed as Record<string, unknown>) : null;
  } catch {
    return NextResponse.json({ status: 'error', error: 'Invalid request body' }, { status: 400 });
  }

  const sourceHash =
    typeof body?.source_hash === 'string' ? body.source_hash.trim() : '';
  if (sourceHash) {
    if (!SOURCE_HASH.test(sourceHash)) {
      return NextResponse.json(
        { status: 'error', error: 'source_hash must be a 64-character hex digest' },
        { status: 400 },
      );
    }
    const record = await getPackRecord(sourceHash);
    if (!record) {
      return NextResponse.json({ status: 'error', error: MISSING_PACK }, { status: 404 });
    }
    return recordToResponse(record);
  }

  const resolved = resolveIdentity(body?.video_id ?? body?.videoId, resolveVideoUrl(body));
  if (resolved instanceof NextResponse) {
    return resolved;
  }
  return sandboxFromIdentity(resolved.identity);
}
