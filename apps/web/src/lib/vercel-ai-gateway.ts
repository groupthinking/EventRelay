import 'server-only';

/**
 * Vercel AI Gateway — OpenAI-compatible routing to Google/Anthropic/OpenAI models.
 * https://vercel.com/docs/ai-gateway
 */

const GATEWAY_CHAT_URL = 'https://ai-gateway.vercel.sh/v1/chat/completions';

export const VERCEL_AI_GATEWAY_DEFAULT_MODEL =
  process.env.VERCEL_AI_GATEWAY_MODEL?.trim() || 'google/gemini-2.5-flash';

export interface GatewayMessage {
  role: 'system' | 'user' | 'assistant';
  content: string;
}

export interface GatewayChatOptions {
  model?: string;
  messages: GatewayMessage[];
  max_tokens?: number;
  temperature?: number;
  timeoutMs?: number;
}

export interface GatewayChatResult {
  content: string;
  model: string;
  usage?: {
    prompt_tokens?: number;
    completion_tokens?: number;
    total_tokens?: number;
    cost?: number;
  };
}

/**
 * Resolve Vercel AI Gateway API key (vck_…).
 * Checked before direct Gemini/Vertex keys when routing LLM calls.
 */
export function resolveAiGatewayKey(): string {
  return (
    process.env.AI_GATEWAY_API_KEY ||
    process.env.VERCEL_AI_GATEWAY_API_KEY ||
    process.env.VERCEL_AI_GATEWAY_API ||
    process.env.VERCEL_API_KEY ||
    ''
  ).trim();
}

export function hasAiGatewayKey(): boolean {
  return resolveAiGatewayKey().length > 0;
}

/** Prefix bare model ids for gateway provider routing (e.g. gemini-2.5-flash → google/gemini-2.5-flash). */
export function toGatewayModelId(model: string): string {
  const trimmed = model.trim();
  if (!trimmed) return VERCEL_AI_GATEWAY_DEFAULT_MODEL;
  if (trimmed.includes('/')) return trimmed;
  if (trimmed.startsWith('gemini-') || trimmed.startsWith('gemma-')) {
    return `google/${trimmed}`;
  }
  if (trimmed.startsWith('gpt-') || trimmed.startsWith('o1') || trimmed.startsWith('o3')) {
    return `openai/${trimmed}`;
  }
  if (trimmed.startsWith('claude-')) {
    return `anthropic/${trimmed}`;
  }
  return trimmed;
}

export function stripJsonCodeFence(text: string): string {
  const trimmed = text.trim();
  if (!trimmed.startsWith('```')) return trimmed;
  const withoutOpening = trimmed.split('\n', 2)[1] ?? trimmed;
  return withoutOpening.replace(/```\s*$/u, '').trim();
}

/**
 * Chat completion via Vercel AI Gateway (OpenAI-compatible API).
 */
export async function gatewayChat(options: GatewayChatOptions): Promise<GatewayChatResult> {
  const key = resolveAiGatewayKey();
  if (!key) {
    throw new Error('AI Gateway API key is not configured');
  }

  const model = options.model ? toGatewayModelId(options.model) : VERCEL_AI_GATEWAY_DEFAULT_MODEL;
  const timeoutMs = options.timeoutMs ?? 60_000;
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(GATEWAY_CHAT_URL, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${key}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        model,
        messages: options.messages,
        max_tokens: options.max_tokens ?? 4096,
        temperature: options.temperature ?? 0.2,
      }),
      signal: controller.signal,
    });

    const raw = await response.text();
    if (!response.ok) {
      throw new Error(`Vercel AI Gateway HTTP ${response.status}: ${raw.slice(0, 500)}`);
    }

    const data = JSON.parse(raw) as {
      model?: string;
      choices?: Array<{ message?: { content?: string } }>;
      usage?: GatewayChatResult['usage'];
    };

    const content = data.choices?.[0]?.message?.content ?? '';
    if (!content.trim()) {
      throw new Error('Vercel AI Gateway returned empty content');
    }

    return {
      content,
      model: data.model || model,
      usage: data.usage,
    };
  } finally {
    clearTimeout(timeout);
  }
}