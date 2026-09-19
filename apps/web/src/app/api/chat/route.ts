import { NextResponse } from 'next/server';
import { generateText } from 'ai';
import { resolveTrustedBillingEmail } from '@/lib/billing/billing-context';
import { isProSubscriber } from '@/lib/billing/entitlement-store';
import { checkFreeChatQuota } from '@/lib/billing/chat-quota';
import { grokChatCompletion } from '@/lib/billing/grok-client';
import { FREE_CHAT_DAILY_LIMIT, resolvePaidTierRouting } from '@/lib/billing/paid-tier-model';
import { kaizenObserve } from '@/lib/billing/kaizen-trace';
import { aiGateway, GATEWAY_CHAT_MODEL } from '@/lib/ai-gateway';
import { hasAiGatewayKey } from '@/lib/vercel-ai-gateway';
import {
  parseChatPackBinding,
  resolveChatPackGrounding,
} from '@/lib/chat-pack-grounding';
type ChatHistoryMessage = { role: 'user' | 'assistant'; content: string };

const rawBackendUrl = process.env.BACKEND_URL || '';
const BACKEND_URL = rawBackendUrl.startsWith('http') ? rawBackendUrl : 'http://localhost:8000';
const BACKEND_AVAILABLE = rawBackendUrl.startsWith('http');

function isValidChatHistoryMessage(message: unknown): message is ChatHistoryMessage {
  if (!message || typeof message !== 'object') {
    return false;
  }

  const candidate = message as { role?: unknown; content?: unknown };
  return (
    (candidate.role === 'user' || candidate.role === 'assistant')
    && typeof candidate.content === 'string'
  );
}

type GatewayMessage = { role: 'system' | 'user' | 'assistant'; content: string };

const BACKEND_SOFT_ERROR_RE =
  /publisher model|was not found|not found for API version|model unavailable|vertex/i;

export function looksLikeBackendProviderSoftError(answer: string): boolean {
  const text = answer.trim();
  if (!text) return true;
  return BACKEND_SOFT_ERROR_RE.test(text);
}

function buildModelMessages(
  systemPrompt: string | undefined,
  history: ChatHistoryMessage[],
  query: string,
): GatewayMessage[] {
  const messages: GatewayMessage[] = [];
  if (systemPrompt) {
    messages.push({ role: 'system', content: systemPrompt });
  }
  for (const entry of history) {
    messages.push({ role: entry.role, content: entry.content });
  }
  messages.push({ role: 'user', content: query });
  return messages;
}

async function generateGatewayChatAnswer(
  packSystemPrompt: string | undefined,
  history: ChatHistoryMessage[],
  query: string,
): Promise<string> {
  if (!hasAiGatewayKey()) {
    throw new Error('gateway_not_configured');
  }
  const { text } = await generateText({
    model: aiGateway(GATEWAY_CHAT_MODEL),
    messages: buildModelMessages(packSystemPrompt, history, query),
  });
  return text;
}

export async function POST(request: Request) {
  let routing = resolvePaidTierRouting(false);
  try {
    const body = await request.json();
    const billingEmail = await resolveTrustedBillingEmail(request);
    const quotaSubject = billingEmail ?? 'anonymous';
    const isPro = await isProSubscriber(billingEmail);
    routing = resolvePaidTierRouting(isPro);

    let packSystemPrompt: string | undefined;
    const packBinding = parseChatPackBinding(body);
    if (
      (typeof body.video_id === 'string' && body.video_id.trim())
      || (typeof body.pack_id === 'string' && body.pack_id.trim())
    ) {
      if (!packBinding) {
        return NextResponse.json(
          {
            answer:
              'Pack binding failed: video_id and pack_id must refer to the same hosted Video Pack.',
            code: 'pack_binding_invalid',
          },
          { status: 400 },
        );
      }
      const grounded = await resolveChatPackGrounding(packBinding);
      if (!grounded.ok) {
        return NextResponse.json(
          { answer: grounded.answer, code: grounded.code },
          { status: grounded.status },
        );
      }
      packSystemPrompt = grounded.systemPrompt;
    }

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

    const history = Array.isArray(body.history)
      ? body.history.filter(isValidChatHistoryMessage)
      : [];
    const query = body.query || body.message || '';

    if (isPro) {
      try {
        const grok = await grokChatCompletion(query, routing.model, {
          systemPrompt: packSystemPrompt,
          history,
        });
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

    const usePackGateway = Boolean(packSystemPrompt);

    if (usePackGateway) {
      try {
        const answer = await generateGatewayChatAnswer(packSystemPrompt, history, query);
        return NextResponse.json({
          answer,
          routing,
          plan: routing.plan,
          provider: 'vercel-ai-gateway',
        });
      } catch (gatewayErr) {
        const msg = gatewayErr instanceof Error ? gatewayErr.message : 'gateway_failed';
        console.error('Pack-grounded gateway chat error:', gatewayErr);
        return NextResponse.json(
          {
            answer:
              msg === 'gateway_not_configured'
                ? 'Pack-grounded chat requires AI_GATEWAY_API_KEY to be configured.'
                : 'The AI assistant is temporarily unavailable. Please try again.',
            routing,
            plan: routing.plan,
            provider: 'vercel-ai-gateway',
          },
          { status: msg === 'gateway_not_configured' ? 503 : 502 },
        );
      }
    }

    if (BACKEND_AVAILABLE) {
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
          message: query,
          video_url: body.video_url || '',
          video_id: body.video_id || '',
          pack_system_context: packSystemPrompt ?? '',
          conversation_history: history,
          model: routing.model,
          lead_runtime: routing.runtime,
        }),
        signal: AbortSignal.timeout(30_000),
      });

      if (!response.ok) {
        const errorText = await response.text();
        console.error('Chat API error:', response.status, errorText);
        if (hasAiGatewayKey()) {
          try {
            const answer = await generateGatewayChatAnswer(packSystemPrompt, history, query);
            return NextResponse.json({
              answer,
              routing,
              plan: routing.plan,
              provider: 'vercel-ai-gateway',
            });
          } catch (gatewayErr) {
            console.error('Gateway fallback after backend HTTP error:', gatewayErr);
          }
        }
        return NextResponse.json(
          { answer: 'The AI assistant is temporarily unavailable. Please try again.', routing },
          { status: response.status },
        );
      }

      const data = await response.json();
      const backendAnswer =
        data.response || data.answer || data.message || 'No response generated.';
      if (looksLikeBackendProviderSoftError(String(backendAnswer)) && hasAiGatewayKey()) {
        try {
          const answer = await generateGatewayChatAnswer(packSystemPrompt, history, query);
          return NextResponse.json({
            answer,
            routing,
            plan: routing.plan,
            provider: 'vercel-ai-gateway',
          });
        } catch (gatewayErr) {
          console.error('Gateway fallback after backend soft error:', gatewayErr);
        }
      }

      return NextResponse.json({
        answer: backendAnswer,
        routing,
        plan: routing.plan,
      });
    }

    if (!hasAiGatewayKey()) {
      return NextResponse.json(
        {
          answer: 'Chat requires either BACKEND_URL or AI_GATEWAY_API_KEY to be configured.',
          routing,
          plan: routing.plan,
        },
        { status: 503 },
      );
    }

    const answer = await generateGatewayChatAnswer(packSystemPrompt, history, query);

    return NextResponse.json({
      answer,
      routing,
      plan: routing.plan,
      provider: 'vercel-ai-gateway',
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
