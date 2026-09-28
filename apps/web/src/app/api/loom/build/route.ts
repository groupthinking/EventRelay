import { NextResponse } from 'next/server';
import { resolveTrustedBillingEmail } from '@/lib/billing/billing-context';
import { isProSubscriber } from '@/lib/billing/entitlement-store';
import { isChatPaywallBypassed } from '@/lib/billing/paywall-bypass';
import { resolvePaidTierRouting } from '@/lib/billing/paid-tier-model';
import { LoomAudioError } from '@/lib/loom-audio';
import { buildFromLoomShare, LoomBuildError } from '@/lib/loom-pro-build';
import { parseLoomShareInput } from '@/lib/loom-share';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';
export const maxDuration = 300;

/**
 * POST /api/loom/build
 *
 * Pro session (stored entitlement or paywall bypass) only.
 * Body: `{ "url": "https://www.loom.com/share/<32-hex>" }`
 * Success: `{ transcript, duration, answer, provider: "xai", model, sttModel }`
 */
export async function POST(request: Request) {
  let body: unknown;
  try {
    body = await request.json();
  } catch (err) {
    console.error('loom build JSON parse failed', err);
    return NextResponse.json(
      { ok: false, error: 'Invalid JSON in request body', code: 'invalid_json' },
      { status: 400 },
    );
  }

  const url = body && typeof body === 'object' && 'url' in body ? (body as { url?: unknown }).url : undefined;
  if (typeof url !== 'string' || !parseLoomShareInput(url)) {
    return NextResponse.json(
      {
        ok: false,
        error: 'Need a public Loom share URL (https://www.loom.com/share/<id> or /embed/<id>).',
        code: 'loom_url_invalid',
      },
      { status: 400 },
    );
  }

  const billingEmail = await resolveTrustedBillingEmail(request);
  const storedPro = await isProSubscriber(billingEmail);
  const paywallBypass = !storedPro && isChatPaywallBypassed(billingEmail);
  const isPro = storedPro || paywallBypass;
  if (!isPro) {
    return NextResponse.json(
      {
        ok: false,
        error: 'Loom transcription and the in-session Grok build require a Pro session.',
        code: 'pro_required',
      },
      { status: 402 },
    );
  }

  const routing = resolvePaidTierRouting(true);
  try {
    const built = await buildFromLoomShare(url, routing.model);
    return NextResponse.json({
      ok: true,
      loomId: built.loomId,
      shareUrl: built.shareUrl,
      transcript: built.transcript,
      duration: built.duration,
      answer: built.answer,
      provider: built.provider,
      model: built.model,
      sttModel: built.sttModel,
      audioSource: built.audioSource,
      plan: routing.plan,
    });
  } catch (err) {
    if (err instanceof LoomAudioError || err instanceof LoomBuildError) {
      console.error('loom build failed', err.code, err.message);
      return NextResponse.json(
        { ok: false, error: err.message, code: err.code },
        { status: err.status },
      );
    }
    console.error('loom build failed', err);
    return NextResponse.json(
      { ok: false, error: 'Loom build failed.', code: 'loom_build_failed' },
      { status: 500 },
    );
  }
}
