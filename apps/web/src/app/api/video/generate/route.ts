import { NextResponse } from 'next/server';

export const runtime = 'nodejs'; // streams/buffers the gateway video bytes through
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
    const inlineBase64: string | null = data?.data?.[0]?.b64_json ?? null;

    if (!remoteUrl && !inlineBase64) {
      console.error(
        '[video/generate] Unexpected gateway response shape:',
        JSON.stringify(data)?.slice(0, 500)
      );
      return NextResponse.json(
        { error: 'Video generation returned an unexpected response with no video.' },
        { status: 502 }
      );
    }

    // Return the raw video bytes as the response body (never base64-in-JSON): a
    // realistically-sized Veo clip base64-encoded inside NextResponse.json would
    // exceed Vercel's ~4.5 MB serverless response limit and fail with
    // FUNCTION_PAYLOAD_TOO_LARGE. The client wraps the bytes in a `blob:` URL,
    // which the app's `media-src 'self' blob: data:` CSP permits.
    const baseHeaders: Record<string, string> = {
      'Cache-Control': 'no-store',
      'X-Video-Model': 'google/veo-3.1-generate-001',
    };

    // Case 1: gateway already returned the bytes inline as base64. Decode, then
    // stream them back. A buffered `Response(buf)` — like base64-in-JSON — is
    // still subject to Vercel's ~4.5 MB response-body limit and would fail with
    // FUNCTION_PAYLOAD_TOO_LARGE for large clips; only STREAMED responses bypass
    // that limit, so wrap the buffer in a ReadableStream and return that.
    if (inlineBase64) {
      const buf = Buffer.from(inlineBase64, 'base64');
      const stream = new ReadableStream<Uint8Array>({
        start(controller) {
          controller.enqueue(new Uint8Array(buf));
          controller.close();
        },
      });
      return new Response(stream, {
        status: 200,
        headers: {
          ...baseHeaders,
          'Content-Type': 'video/mp4',
          'Content-Length': String(buf.byteLength),
        },
      });
    }

    // Case 2: gateway returned a signed URL. The URL comes from the trusted
    // gateway response (NOT client input — no SSRF), so we fetch it server-side
    // and STREAM the body straight through to the client. Streaming means we
    // never buffer the whole file in memory (no OOM on large clips) and never
    // hit the buffered-response size limit.
    let videoResp: Response;
    try {
      videoResp = await fetch(remoteUrl as string, { signal: AbortSignal.timeout(120_000) });
    } catch (fetchErr) {
      console.error('[video/generate] Error fetching signed video URL:', fetchErr);
      return NextResponse.json(
        { error: 'Video was generated but could not be retrieved for playback.' },
        { status: 502 }
      );
    }

    if (!videoResp.ok || !videoResp.body) {
      console.error('[video/generate] Failed to fetch signed video URL:', videoResp.status);
      return NextResponse.json(
        { error: 'Video was generated but could not be retrieved for playback.' },
        { status: 502 }
      );
    }

    const upstreamLength = videoResp.headers.get('content-length');
    return new Response(videoResp.body, {
      status: 200,
      headers: {
        ...baseHeaders,
        'Content-Type': videoResp.headers.get('content-type') ?? 'video/mp4',
        ...(upstreamLength ? { 'Content-Length': upstreamLength } : {}),
      },
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
