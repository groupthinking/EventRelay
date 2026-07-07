import { NextResponse } from 'next/server';
import { experimental_generateVideo as generateVideo } from 'ai';
import { getGateway, hasAiGatewayKey, GATEWAY_MODELS } from '@/lib/ai-gateway';

export const maxDuration = 300;

export async function POST(request: Request) {
  if (!hasAiGatewayKey()) {
    return NextResponse.json(
      { error: 'AI_GATEWAY_API_KEY is not configured. Video generation requires the Vercel AI Gateway.' },
      { status: 503 },
    );
  }

  let body: { prompt?: string; aspectRatio?: `${number}:${number}`; duration?: number };
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: 'Invalid JSON body' }, { status: 400 });
  }

  const prompt = body.prompt?.trim();
  if (!prompt) {
    return NextResponse.json(
      { error: 'Missing required field: prompt' },
      { status: 400 },
    );
  }

  if (prompt.length > 1000) {
    return NextResponse.json(
      { error: 'Prompt must be 1000 characters or fewer' },
      { status: 400 },
    );
  }

  try {
    const gw = getGateway();
    const result = await generateVideo({
      model: gw.videoModel(GATEWAY_MODELS.video),
      prompt,
      ...(body.aspectRatio ? { aspectRatio: body.aspectRatio } : {}),
      ...(body.duration ? { duration: body.duration } : {}),
    });

    const video = result.video;
    return NextResponse.json({
      base64: video.base64,
      mediaType: video.mediaType,
    });
  } catch (err) {
    const message = err instanceof Error ? err.message : 'Video generation failed';
    console.error('Video generation error:', message);
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
