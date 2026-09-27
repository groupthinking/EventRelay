import { GROK_BILLING_LEAD_MODEL } from './grok-lead';
import { kaizenObserve } from './kaizen-trace';

export type GrokChatResult = {
  answer: string;
  model: string;
  provider: 'xai';
};

/**
 * Production Grok key first. A stale XAI_API_KEY must not win over
 * GROK_XAI_API_KEY (live Pro chat 503 / xai_http_400 on uvai.io).
 */
export const XAI_KEY_ENV_NAMES = [
  'GROK_XAI_API_KEY',
  'XAI_API_KEY',
  'GROK_API_KEY',
] as const;

export type XaiKeyEnvName = (typeof XAI_KEY_ENV_NAMES)[number];

export type XaiApiKeySelection = {
  apiKey: string;
  fromEnv: XaiKeyEnvName;
};

export function selectXaiApiKey(
  env: { readonly [key: string]: string | undefined } = process.env,
): XaiApiKeySelection | undefined {
  for (const fromEnv of XAI_KEY_ENV_NAMES) {
    const apiKey = env[fromEnv];
    if (apiKey) {
      return { apiKey, fromEnv };
    }
  }
  return undefined;
}

export function getXaiApiKey(): string | undefined {
  return selectXaiApiKey()?.apiKey;
}

function xaiErrorDetail(detail: string, apiKey: string): string {
  const redacted = apiKey ? detail.split(apiKey).join('[redacted]') : detail;
  return redacted.slice(0, 200);
}

type GrokChatContext = {
  systemPrompt?: string;
  history?: Array<{ role: 'user' | 'assistant'; content: string }>;
};

export async function grokChatCompletion(
  query: string,
  model: string = GROK_BILLING_LEAD_MODEL,
  context: GrokChatContext = {},
): Promise<GrokChatResult> {
  const selected = selectXaiApiKey();
  if (!selected) {
    throw new Error('XAI_API_KEY missing fromEnv:none');
  }
  const { apiKey, fromEnv } = selected;

  const res = await fetch('https://api.x.ai/v1/chat/completions', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${apiKey}`,
    },
    body: JSON.stringify({
      model,
      messages: [
        {
          role: 'system',
          content:
            context.systemPrompt
            ?? 'You are the UVAI Workflow Pro lead agent (Grok/Composer). Answer concisely for video intelligence users.',
        },
        ...(context.history ?? []).map((entry) => ({
          role: entry.role,
          content: entry.content,
        })),
        { role: 'user', content: query },
      ],
      max_tokens: 512,
    }),
    signal: AbortSignal.timeout(30_000),
  });

  if (!res.ok) {
    const detail = await res.text();
    throw new Error(
      `xai_http_${res.status} fromEnv:${fromEnv}:${xaiErrorDetail(detail, apiKey)}`,
    );
  }

  const data = (await res.json()) as {
    choices?: Array<{ message?: { content?: string } }>;
  };
  const answer = data.choices?.[0]?.message?.content?.trim() || 'No response from Grok.';

  kaizenObserve('billing', 'grok_completion', 'Pro chat served via xAI Grok API', {
    decision: `model=${model}`,
  });

  return { answer, model, provider: 'xai' };
}
