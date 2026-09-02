import { NextResponse } from 'next/server';
import { resolveVideoUrl } from '@/lib/video-url-request';
import { buildIdentityPack, resolveYouTubeVideoId, type VideoPackV0Json } from '@/lib/video-pack';

export const runtime = 'nodejs';

const packs = new Map<string, VideoPackV0Json>();

function getOrCreatePack(videoId: string, sourceUrl?: string): VideoPackV0Json {
  const existing = packs.get(videoId);
  if (existing) {
    return existing;
  }
  const pack = buildIdentityPack(videoId, sourceUrl);
  packs.set(videoId, pack);
  return pack;
}

export async function POST(request: Request) {
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

  const pack = getOrCreatePack(videoId, url || undefined);
  return NextResponse.json({ status: 'success', data: pack });
}
