import { GROK_BILLING_LEAD_MODEL } from './grok-lead';
import { kaizenObserve } from './kaizen-trace';

export type GrokChatResult = {
  answer: string;
  model: string;
  provider: 'xai';
};

export function getXaiApiKey(): string | undefined {
  return (
    process.env.XAI_API_KEY ||
    process.env.GROK_XAI_API_KEY ||
    process.env.GROK_API_KEY
  );
}

export async function grokChatCompletion(
  query: string,
  model: string = GROK_BILLING_LEAD_MODEL,
): Promise<GrokChatResult> {
  const apiKey = getXaiApiKey();
  if (!apiKey) {
    throw new Error('XAI_API_KEY missing');
  }

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
            'You are the EventRelay Pro lead agent (Grok/Composer). Answer concisely for video intelligence users.',
        },
        { role: 'user', content: query },
      ],
      max_tokens: 512,
    }),
    signal: AbortSignal.timeout(30_000),
  });

  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`xai_http_${res.status}:${detail.slice(0, 200)}`);
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