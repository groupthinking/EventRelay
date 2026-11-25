import { NextResponse } from 'next/server';
import {
  KEYFRAME_JPEG_CONTENT_TYPE,
  loadCapturedFrameJpeg,
} from '@/lib/keyframe-frame-capture';
import { resolveYouTubeVideoId } from '@/lib/video-pack';

export const runtime = 'nodejs';
export const maxDuration = 30;

const FRAME_T = /^(?:0|[1-9]\d*)(?:\.\d+)?$/;

export async function GET(
  _request: Request,
  context: { params: Promise<{ videoId: string; t: string }> },
): Promise<Response> {
  const params = await context.params;
  const videoId = resolveYouTubeVideoId(params.videoId ?? '');
  const tRaw = (params.t ?? '').trim();
  if (!videoId || !FRAME_T.test(tRaw)) {
    return NextResponse.json({ status: 'error', error: 'A video id and keyframe t_s are required.' }, { status: 400 });
  }
  const t_s = Number(tRaw);
  try {
    const bytes = await loadCapturedFrameJpeg(videoId, t_s);
    if (!bytes) {
      return NextResponse.json(
        { status: 'error', error: 'No captured frame at that timestamp.' },
        { status: 404 },
      );
    }
    return new NextResponse(Buffer.from(bytes), {
      status: 200,
      headers: {
        'Content-Type': KEYFRAME_JPEG_CONTENT_TYPE,
        'Cache-Control': 'public, max-age=86400',
      },
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Frame capture failed.';
    console.error('[video-pack-frames] serve failed:', message);
    return NextResponse.json({ status: 'error', error: message }, { status: 503 });
  }
}
