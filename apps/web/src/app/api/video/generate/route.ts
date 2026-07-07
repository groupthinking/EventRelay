import { NextResponse } from 'next/server';

export const runtime = 'nodejs'; // needs Buffer to inline the signed video URL
export const maxDuration = 300; // 5 minutes — video generation takes time

/** Simple in-memory rate limiter: max 3 requests per IP per 10 minutes */
const rateLimitMap = new Map<string, { count: number; resetAt: number }>();
const RATE_LIMIT_MAX = 3;
const RATE_LIMIT_WINDOW_MS = 10 * 60 * 1000;

const ALLOWED_ASPECT_RATIOS = ['16:9', '9:16', '1:1', '4:3'];
const MIN_DURATION_SECONDS = 1;
const MAX_DURATION_SECONDS = 60;

/**
 * Evict expired rate-limit records so the map does not grow unbounded in a
 * long-lived server runtime, then apply the limit for the given IP.
 */
function checkRateLimit(ip: string): boolean {
  const now = Date.now();

  for (const [key, record] of rateLimitMap) {
    if (now > record.resetAt) {
      rateLimitMap.delete(key);
    }
  }

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

  // Rate limiting. The x-forwarded-for / x-real-ip headers are only trustworthy
  // because Vercel's edge network overwrites them with the real client IP before
  // the request reaches this function; do not rely on them in environments where
  // an untrusted proxy sits in front of the app.
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
  } catch (error) {
    console.error('[video/generate] Failed to parse JSON body:', error);
    return NextResponse.json({ error: 'Invalid JSON body.' }, { status: 400 });
  }

  const { prompt, aspectRatio = '16:9', duration = 5 } = body;

  if (!prompt || typeof prompt !== 'string' || prompt.trim().length === 0) {
    return NextResponse.json({ error: 'prompt is required.' }, { status: 400 });
  }

  if (prompt.length > 1000) {
    return NextResponse.json({ error: 'prompt must be 1000 characters or fewer.' }, { status: 400 });
  }

  if (typeof aspectRatio !== 'string' || !ALLOWED_ASPECT_RATIOS.includes(aspectRatio)) {
    return NextResponse.json(
      { error: `aspectRatio must be one of: ${ALLOWED_ASPECT_RATIOS.join(', ')}.` },
      { status: 400 }
    );
  }

  if (
    typeof duration !== 'number' ||
    !Number.isFinite(duration) ||
    duration < MIN_DURATION_SECONDS ||
    duration > MAX_DURATION_SECONDS
  ) {
    return NextResponse.json(
      { error: `duration must be a number between ${MIN_DURATION_SECONDS} and ${MAX_DURATION_SECONDS} seconds.` },
      { status: 400 }
    );
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

    // AI Gateway returns video as a signed URL or base64 depending on the response.
    // Validate the shape so we never send a 200 with no usable video payload.
    const remoteUrl: string | null = data?.data?.[0]?.url ?? data?.url ?? null;
    let videoBase64: string | null = data?.data?.[0]?.b64_json ?? null;

    if (!remoteUrl && !videoBase64) {
      console.error(
        '[video/generate] Unexpected gateway response shape:',
        JSON.stringify(data)?.slice(0, 500)
      );
      return NextResponse.json(
        { error: 'Video generation returned an unexpected response with no video.' },
        { status: 502 }
      );
    }

    // The app's CSP is `media-src 'self' blob: data:`, so a cross-origin signed
    // URL would be blocked by the browser and the <video> would never load. The
    // URL here comes from the trusted gateway response (NOT client input), so we
    // can safely fetch it server-side and inline it as base64 — a `data:` source
    // the CSP permits — without exposing a client-controllable proxy (no SSRF).
    if (!videoBase64 && remoteUrl) {
      try {
        const videoResp = await fetch(remoteUrl, { signal: AbortSignal.timeout(45_000) });
        if (videoResp.ok) {
          const buf = Buffer.from(await videoResp.arrayBuffer());
          videoBase64 = buf.toString('base64');
        } else {
          console.error('[video/generate] Failed to fetch signed video URL:', videoResp.status);
        }
      } catch (fetchErr) {
        console.error('[video/generate] Error inlining signed video URL:', fetchErr);
      }
    }

    if (!videoBase64) {
      return NextResponse.json(
        { error: 'Video was generated but could not be retrieved for playback.' },
        { status: 502 }
      );
    }

    return NextResponse.json({
      // `video` is intentionally null: the client renders the base64 `data:` URL,
      // which is the only cross-origin-safe source under the app's media-src CSP.
      video: null,
      videoBase64,
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
