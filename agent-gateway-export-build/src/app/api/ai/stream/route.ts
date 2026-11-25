import { streamText } from 'ai';
import { decideAiStream, type AiStreamDecision } from '@/lib/ai-stream-guard';

export const runtime = 'edge';

const hitsByToken = new Map<string, number[]>();

function jsonError(decision: Extract<AiStreamDecision, { ok: false }>): Response {
  return Response.json(
    { error: { code: decision.code, message: decision.message } },
    { status: decision.status },
  );
}

export async function POST(request: Request) {
  let body: { prompt?: unknown; model?: unknown };
  try {
    const parsed: unknown = await request.json();
    if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
      return Response.json(
        { error: { code: 'schema_invalid', message: 'Prompt is required.' } },
        { status: 400 },
      );
    }
    body = parsed as { prompt?: unknown; model?: unknown };
  } catch (error) {
    console.error('ai_stream_invalid_json', error);
    return Response.json(
      { error: { code: 'schema_invalid', message: 'Prompt is required.' } },
      { status: 400 },
    );
  }

  const authorizationHeader = request.headers.get('authorization');
  const tokenKey = authorizationHeader ?? '';
  const decision = decideAiStream(
    {
      enabled: process.env.AI_STREAM_ENABLED,
      authToken: process.env.AI_STREAM_AUTH_TOKEN,
      model: process.env.AI_GATEWAY_MODEL,
    },
    {
      authorizationHeader,
      prompt: body.prompt,
      requestedModel: body.model,
      nowMs: Date.now(),
      recentHits: hitsByToken.get(tokenKey) ?? [],
    },
  );
  if (decision.ok || (decision.status !== 401 && decision.status !== 503)) {
    hitsByToken.set(tokenKey, decision.hits);
  }

  if (!decision.ok) {
    return jsonError(decision);
  }

  const result = streamText({
    model: decision.model,
    prompt: decision.prompt,
    maxOutputTokens: decision.maxOutputTokens,
    abortSignal: AbortSignal.timeout(30_000),
  });
  return result.toTextStreamResponse();
}
