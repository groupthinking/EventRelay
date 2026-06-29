import { NextResponse } from 'next/server';
import { resolveTrustedBillingEmail } from '@/lib/billing/billing-context';
import { isProSubscriber } from '@/lib/billing/entitlement-store';
import { checkFreeChatQuota } from '@/lib/billing/chat-quota';
import { grokChatCompletion } from '@/lib/billing/grok-client';
import { FREE_CHAT_DAILY_LIMIT, resolvePaidTierRouting } from '@/lib/billing/paid-tier-model';
import { kaizenObserve } from '@/lib/billing/kaizen-trace';

const rawBackendUrl = process.env.BACKEND_URL || '';
const BACKEND_URL = rawBackendUrl.startsWith('http') ? rawBackendUrl : 'http://localhost:8000';
const BACKEND_AVAILABLE = rawBackendUrl.startsWith('http');

export async function POST(request: Request) {
  let routing = resolvePaidTierRouting(false);
  try {
    const body = await request.json();
    const billingEmail = await resolveTrustedBillingEmail(request);
    const quotaSubject = billingEmail ?? 'anonymous';
    const isPro = await isProSubscriber(billingEmail);
    routing = resolvePaidTierRouting(isPro);

    if (!isPro) {
      const quota = await checkFreeChatQuota(quotaSubject, FREE_CHAT_DAILY_LIMIT);
      if (!quota.allowed) {
        kaizenObserve('billing', 'chat_quota_exceeded', `Free tier limit for ${quotaSubject}`, {
          decision: `used=${quota.used} limit=${quota.limit}`,
          fix: 'upgrade_to_pro',
        });
        return NextResponse.json(
          {
            answer: 'Free plan includes 5 AI chat messages per day. Upgrade to Pro for unlimited chat.',
            upgradeRequired: true,
            plan: 'free',
            quota,
          },
          { status: 402 },
        );
      }
    }

    kaizenObserve('billing', 'chat_routed', `Chat for ${quotaSubject}`, {
      decision: `model=${routing.model} runtime=${routing.runtime} plan=${routing.plan}`,
    });

    if (isPro) {
      try {
        const grok = await grokChatCompletion(body.query ?? '', routing.model);
        return NextResponse.json({
          answer: grok.answer,
          routing,
          plan: routing.plan,
          provider: grok.provider,
        });
      } catch (grokErr) {
        const msg = grokErr instanceof Error ? grokErr.message : 'grok_failed';
        kaizenObserve('billing', 'grok_error', msg, { fix: 'verify_xai_api_key' });
        return NextResponse.json(
          {
            answer: `Pro Grok unavailable: ${msg}`,
            routing,
            plan: routing.plan,
            provider: 'xai',
          },
          { status: 503 },
        );
      }
    }

    if (!BACKEND_AVAILABLE) {
      return NextResponse.json(
        {
          answer: 'Chat requires a backend connection. Configure BACKEND_URL to enable the AI assistant.',
          routing,
          plan: routing.plan,
        },
        { status: 503 },
      );
    }

    const response = await fetch(`${BACKEND_URL}/api/v1/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(process.env.EVENTRELAY_API_KEY ? { 'X-API-Key': process.env.EVENTRELAY_API_KEY } : {}),
        'X-Billing-Plan': routing.plan,
        'X-Lead-Model': routing.model,
        'X-Lead-Runtime': routing.runtime,
      },
      body: JSON.stringify({
        message: body.query,
        video_url: body.video_url || '',
        video_id: body.video_id || '',
        conversation_history: body.history || [],
        model: routing.model,
        lead_runtime: routing.runtime,
      }),
      signal: AbortSignal.timeout(30_000),
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error('Chat API error:', response.status, errorText);
      return NextResponse.json(
        { answer: 'The AI assistant is temporarily unavailable. Please try again.', routing },
        { status: response.status },
      );
    }

    const data = await response.json();

    return NextResponse.json({
      answer: data.response || data.answer || data.message || 'No response generated.',
      routing,
      plan: routing.plan,
    });
  } catch (error) {
    console.error('Chat proxy error:', error);
    return NextResponse.json(
      {
        answer: 'Failed to connect to the AI assistant.',
        routing,
        plan: routing.plan,
      },
      { status: 502 },
    );
  }
}