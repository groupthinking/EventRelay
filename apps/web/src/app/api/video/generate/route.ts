import { NextResponse } from 'next/server';

export const maxDuration = 300; // 5 minutes — video generation takes time

/** Simple in-memory rate limiter: max 3 requests per IP per 10 minutes */
const rateLimitMap = new Map<string, { count: number; resetAt: number }>();
const RATE_LIMIT_MAX = 3;
const RATE_LIMIT_WINDOW_MS = 10 * 60 * 1000;

function checkRateLimit(ip: string): boolean {
  const now = Date.now();
  const record = rateLimitMap.get(ip);

  if (!record || now > record.resetAt) {
    rateLimitMap.set(ip, { count: 1, resetAt: now + RATE_LIMIT_WINDOW_MS });
    return true;
  }

  if (record.count >= RATE_LIMIT_MAX) {
    return false;
  }

  record.count++;
  return true;
}

export async function POST(request: Request) {
  const apiKey = process.env.AI_GATEWAY_API_KEY;
  if (!apiKey) {
    return NextResponse.json(
      { error: 'AI_GATEWAY_API_KEY is not configured.' },
      { status: 503 }
    );
  }

  // Rate limiting
  const ip =
    request.headers.get('x-forwarded-for')?.split(',')[0]?.trim() ??
    request.headers.get('x-real-ip') ??
    'unknown';

  if (!checkRateLimit(ip)) {
    return NextResponse.json(
      { error: 'Rate limit exceeded. Maximum 3 video generation requests per 10 minutes.' },
      { status: 429 }
    );
  }

  let body: { prompt?: string; aspectRatio?: string; duration?: number };
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: 'Invalid JSON body.' }, { status: 400 });
  }

  const { prompt, aspectRatio = '16:9', duration = 5 } = body;

  if (!prompt || typeof prompt !== 'string' || prompt.trim().length === 0) {
    return NextResponse.json({ error: 'prompt is required.' }, { status: 400 });
  }

  if (prompt.length > 1000) {
    return NextResponse.json({ error: 'prompt must be 1000 characters or fewer.' }, { status: 400 });
  }

  try {
    const gatewayResponse = await fetch('https://ai-gateway.vercel.sh/v1/video/generations', {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${apiKey}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        model: 'google/veo-3.1-generate-001',
        prompt: prompt.trim(),
        aspect_ratio: aspectRatio,
        duration_seconds: duration,
      }),
      signal: AbortSignal.timeout(290_000),
    });

    if (!gatewayResponse.ok) {
      const errorText = await gatewayResponse.text();
      console.error('[video/generate] Gateway error:', gatewayResponse.status, errorText);
      return NextResponse.json(
        { error: 'Video generation failed. The model may be unavailable.' },
        { status: gatewayResponse.status }
      );
    }

    const data = await gatewayResponse.json();

    // AI Gateway returns video as base64 or a signed URL depending on the response
    return NextResponse.json({
      video: data.data?.[0]?.url ?? data.url ?? null,
      videoBase64: data.data?.[0]?.b64_json ?? null,
      model: 'google/veo-3.1-generate-001',
      prompt: prompt.trim(),
    });
  } catch (error) {
    console.error('[video/generate] Error:', error);
    if (error instanceof Error && error.name === 'TimeoutError') {
      return NextResponse.json(
        { error: 'Video generation timed out. Try a shorter duration or simpler prompt.' },
        { status: 504 }
      );
    }
    return NextResponse.json({ error: 'Video generation failed.' }, { status: 500 });
  }
}
