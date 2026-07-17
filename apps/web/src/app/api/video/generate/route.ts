import { NextResponse } from 'next/server';
import { experimental_generateVideo } from 'ai';
import { resolveTrustedBillingEmail } from '@/lib/billing/billing-context';
import { isProSubscriber } from '@/lib/billing/entitlement-store';
import { resolveUpstashRedisCredentials } from '@/lib/billing/redis-credentials';
import { aiGateway, GATEWAY_VIDEO_MODEL } from '@/lib/ai-gateway';

export const runtime = 'nodejs'; // streams/buffers the gateway video bytes through
export const maxDuration = 300; // 5 minutes — video generation takes time

const RATE_LIMIT_MAX = 3;
const RATE_LIMIT_WINDOW_SECONDS = 10 * 60;

const ALLOWED_ASPECT_RATIOS = ['16:9', '9:16', '1:1', '4:3'];
const MIN_DURATION_SECONDS = 1;
const MAX_DURATION_SECONDS = 60;

/**
 * Durable Redis-backed rate limiter using Upstash/KV.
 *
 * Production fails closed when Redis is missing or errors — Veo is the most
 * expensive route; fail-open would re-open denial-of-wallet (audit #4/#7).
 * Set UVAI_RATE_LIMIT_FAIL_OPEN=1 only as an emergency break-glass.
 */
async function checkRateLimit(ip: string): Promise<{ allowed: boolean; reason?: string }> {
  const failOpen =
    process.env.UVAI_RATE_LIMIT_FAIL_OPEN === '1' &&
    process.env.NODE_ENV === 'production';

  const creds = resolveUpstashRedisCredentials();
  if (!creds) {
    if (process.env.NODE_ENV === 'production' && !failOpen) {
      console.error(
        '[video/generate] Redis credentials missing in production — denying video generation (fail-closed).',
      );
      return { allowed: false, reason: 'rate_limit_unavailable' };
    }
    // Local/dev without Redis: allow so engineers can exercise the route.
    return { allowed: true };
  }

  try {
    const { Redis } = await import('@upstash/redis');
    const redis = new Redis({
      url: creds.url,
      token: creds.token,
    });

    const key = `ratelimit:video-generate:${ip}`;
    const count = await redis.incr(key);

    // Refresh expiration on every hit to ensure we don't leak keys if the
    // initial expire call failed.
    await redis.expire(key, RATE_LIMIT_WINDOW_SECONDS);

    return { allowed: count <= RATE_LIMIT_MAX };
  } catch (error) {
    console.error('[video/generate] Redis rate limit error:', error);
    if (process.env.NODE_ENV === 'production' && !failOpen) {
      return { allowed: false, reason: 'rate_limit_error' };
    }
    return { allowed: true };
  }
}

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
  // the request reaches this function.
  const ip =
    request.headers.get('x-forwarded-for')?.split(',')[0]?.trim() ??
    request.headers.get('x-real-ip') ??
    'unknown';

  const rate = await checkRateLimit(ip);
  if (!rate.allowed) {
    if (rate.reason === 'rate_limit_unavailable' || rate.reason === 'rate_limit_error') {
      return NextResponse.json(
        {
          error:
            'Video generation rate limiting is unavailable. Configure Upstash/KV Redis credentials or set UVAI_RATE_LIMIT_FAIL_OPEN=1 only as an emergency override.',
          code: rate.reason,
        },
        { status: 503 },
      );
    }
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

  if (typeof aspectRatio !== 'string' || !ALLOWED_ASPECT_RATIOS.includes(aspectRatio as any)) {
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
    const { video } = await experimental_generateVideo({
      model: aiGateway.videoModel(GATEWAY_VIDEO_MODEL),
      prompt: prompt.trim(),
      aspectRatio: aspectRatio as any,
      duration,
      abortSignal: AbortSignal.timeout(290_000),
    });

    // experimental_generateVideo returns a GeneratedFile which contains the
    // video data and media type. We stream these bytes back to the client.
    const videoData = video.uint8Array;
    const stream = new ReadableStream<Uint8Array>({
      start(controller) {
        controller.enqueue(videoData);
        controller.close();
      },
    });

    return new Response(stream, {
      status: 200,
      headers: {
        'Cache-Control': 'no-store',
        'Content-Type': video.mediaType || 'video/mp4',
        'Content-Length': String(videoData.byteLength),
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
    return NextResponse.json(
      { error: 'Video generation failed. The model may be unavailable or returned an unexpected response.' },
      { status: 500 }
    );
  }
}
