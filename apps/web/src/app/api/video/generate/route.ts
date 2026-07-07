import { NextResponse } from 'next/server';
import { experimental_generateVideo as generateVideo } from 'ai';
import { aiGateway, GATEWAY_VIDEO_MODEL } from '@/lib/ai-gateway';

export const runtime = 'nodejs';
export const maxDuration = 300;

const RATE_LIMIT_WINDOW_MS = 10 * 60 * 1000;
const RATE_LIMIT_MAX = 3;
const rateLimitMap = new Map<string, { count: number; resetAt: number }>();

function readClientIp(request: Request): string {
  return request.headers.get('x-forwarded-for')?.split(',')[0]?.trim()
    || request.headers.get('x-real-ip')
    || 'unknown';
}

function isRateLimited(ip: string): boolean {
  const now = Date.now();
  const current = rateLimitMap.get(ip);

  if (!current || now > current.resetAt) {
    rateLimitMap.set(ip, { count: 1, resetAt: now + RATE_LIMIT_WINDOW_MS });
    return false;
  }

  if (current.count >= RATE_LIMIT_MAX) {
    return true;
  }

  current.count += 1;
  return false;
}

export async function POST(request: Request) {
  if (!process.env.AI_GATEWAY_API_KEY && !process.env.VERCEL_AI_GATEWAY_API_KEY && !process.env.VERCEL_API_KEY) {
    return NextResponse.json(
      { error: 'AI_GATEWAY_API_KEY is not configured.' },
      { status: 503 },
    );
  }

  const ip = readClientIp(request);
  if (isRateLimited(ip)) {
    return NextResponse.json(
      { error: 'Rate limit exceeded. Maximum 3 video generation requests per 10 minutes.' },
      { status: 429 },
    );
  }

  let body: { prompt?: string; aspectRatio?: `${number}:${number}`; duration?: number };
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: 'Invalid JSON body.' }, { status: 400 });
  }

  const prompt = body.prompt?.trim() || '';
  const aspectRatio = body.aspectRatio || '16:9';
  const duration = body.duration ?? 5;

  if (!prompt) {
    return NextResponse.json({ error: 'prompt is required.' }, { status: 400 });
  }

  if (prompt.length > 1000) {
    return NextResponse.json(
      { error: 'prompt must be 1000 characters or fewer.' },
      { status: 400 },
    );
  }

  if (!Number.isFinite(duration) || duration <= 0 || duration > 10) {
    return NextResponse.json(
      { error: 'duration must be between 1 and 10 seconds.' },
      { status: 400 },
    );
  }

  try {
    const { videos } = await generateVideo({
      model: aiGateway.video(GATEWAY_VIDEO_MODEL),
      prompt,
      aspectRatio,
      duration,
    });

    const video = videos[0];
    if (!video) {
      return NextResponse.json({ error: 'Video generation returned no output.' }, { status: 502 });
    }

    if (video.base64.length > 2_000_000) {
      return NextResponse.json(
        { error: 'Generated video is too large to return inline. Use a shorter prompt or duration.' },
        { status: 413 },
      );
    }

    return NextResponse.json({
      model: GATEWAY_VIDEO_MODEL,
      prompt,
      videoBase64: video.base64,
      videoUrl: null,
    });
  } catch (error) {
    console.error('[video/generate] generation failed', error);
    return NextResponse.json(
      { error: 'Video generation failed upstream. Please try again.' },
      { status: 502 },
    );
  }
}
