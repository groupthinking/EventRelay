import { NextResponse } from 'next/server';
import { experimental_generateVideo } from 'ai';
import { aiGateway, GATEWAY_VIDEO_MODEL } from '@/lib/ai-gateway';
import { resolveTrustedBillingEmail } from '@/lib/billing/billing-context';
import { isProSubscriber } from '@/lib/billing/entitlement-store';
import { resolveUpstashRedisCredentials } from '@/lib/billing/redis-credentials';

export const runtime = 'nodejs'; // streams/buffers the gateway video bytes through
export const maxDuration = 300; // 5 minutes — video generation takes time

const RATE_LIMIT_MAX = 3;
const RATE_LIMIT_WINDOW_MS = 10 * 60 * 1000; // 10 minutes

/**
 * In-memory fallback rate limiter — only used when Upstash is not configured.
 * Per-instance and reset on cold start: NOT a production-grade control.
 * The primary paywall is the Pro entitlement check above; this is secondary.
 */
const rateLimitMap = new Map<string, { count: number; resetAt: number }>();

function checkRateLimitInMemory(ip: string): boolean {
  const now = Date.now();
  for (const [key, record] of rateLimitMap) {
    if (now > record.resetAt) rateLimitMap.delete(key);
  }
  const record = rateLimitMap.get(ip);
  if (!record || now > record.resetAt) {
    rateLimitMap.set(ip, { count: 1, resetAt: now + RATE_LIMIT_WINDOW_MS });
    return true;
  }
  if (record.count >= RATE_LIMIT_MAX) return false;
  record.count++;
  return true;
}

/**
 * Durable rate limiter backed by Upstash Redis REST API (atomic INCR).
 * Falls back to in-memory when Upstash credentials are not configured.
 */
async function checkRateLimit(ip: string): Promise<boolean> {
  const creds = resolveUpstashRedisCredentials();
  if (creds) {
    try {
      const key = `er:ratelimit:video:${ip}`;
      const windowSecs = Math.ceil(RATE_LIMIT_WINDOW_MS / 1000);
      // Atomic INCR + conditional EXPIRE via REST pipeline
      const pipelineRes = await fetch(`${creds.url}/pipeline`, {
        method: 'POST',
        headers: {
          Authorization: 'Bearer ' + creds.token,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify([
          ['INCR', key],
          ['EXPIRE', key, windowSecs, 'NX'],
        ]),
        signal: AbortSignal.timeout(5_000),
      });
      if (pipelineRes.ok) {
        const results = await pipelineRes.json();
        const count: number = results?.[0]?.result ?? 1;
        return count <= RATE_LIMIT_MAX;
      }
    } catch (err) {
      console.error('[video/generate] Upstash rate-limit error, falling back to in-memory:', err);
    }
  }
  return checkRateLimitInMemory(ip);
}

const ALLOWED_ASPECT_RATIOS = ['16:9', '9:16', '1:1', '4:3'];
const MIN_DURATION_SECONDS = 1;
const MAX_DURATION_SECONDS = 60;

export async function POST(request: Request) {
  // Veo-3.1 is the most expensive AI operation in the app. Gate it behind the
  // Pro entitlement like the other paid routes (agents/dispatch), so an
  // unauthenticated caller cannot run up video-generation spend.
  const billingEmail = await resolveTrustedBillingEmail(request);
  const isPro = await isProSubscriber(billingEmail);
  if (!isPro) {
    return NextResponse.json(
      {
        error: 'Video generation is a Pro feature. Upgrade at /pricing.',
        upgradeRequired: true,
        plan: 'free',
      },
      { status: 402 }
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

  if (!(await checkRateLimit(ip))) {
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
    const result = await experimental_generateVideo({
      model: aiGateway.videoModel(GATEWAY_VIDEO_MODEL),
      prompt: prompt.trim(),
      providerOptions: {
        gateway: {
          aspectRatio,
          durationSeconds: duration,
        },
      },
      abortSignal: AbortSignal.timeout(290_000),
    });

    const videoBytes = result.video.uint8Array;
    const stream = new ReadableStream<Uint8Array>({
      start(controller) {
        controller.enqueue(videoBytes);
        controller.close();
      },
    });

    return new Response(stream, {
      status: 200,
      headers: {
        'Content-Type': result.video.mimeType ?? 'video/mp4',
        'Content-Length': String(videoBytes.byteLength),
        'Cache-Control': 'no-store',
        'X-Video-Model': GATEWAY_VIDEO_MODEL,
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
