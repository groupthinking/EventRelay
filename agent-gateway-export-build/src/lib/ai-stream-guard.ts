/**
 * Fail-closed gate for the scaffold AI stream route.
 * Gateway credentials authenticate this app to the provider. They do not
 * authorize callers. The route stays disabled until an operator explicitly
 * enables it and sets a bearer token.
 */

export const DEFAULT_AI_STREAM_MODEL = 'openai/gpt-5.5';
export const MAX_PROMPT_CHARS = 4_000;
export const MAX_OUTPUT_TOKENS = 1_024;
export const STREAM_RATE_LIMIT = 6;
export const STREAM_RATE_WINDOW_MS = 60_000;
const MIN_AUTH_TOKEN_CHARS = 16;

export interface AiStreamEnv {
  enabled: string | undefined;
  authToken: string | undefined;
  model: string | undefined;
}

export interface AiStreamRequest {
  authorizationHeader: string | null;
  prompt: unknown;
  requestedModel: unknown;
  nowMs: number;
  recentHits: readonly number[];
}

export type AiStreamDenial = {
  ok: false;
  status: 400 | 401 | 413 | 429 | 503;
  code: 'auth' | 'schema_invalid' | 'rate_limited' | 'disabled';
  message: string;
  hits: number[];
};

export type AiStreamAllowance = {
  ok: true;
  model: string;
  prompt: string;
  maxOutputTokens: number;
  hits: number[];
};

export type AiStreamDecision = AiStreamDenial | AiStreamAllowance;

function denial(
  status: AiStreamDenial['status'],
  code: AiStreamDenial['code'],
  message: string,
  hits: number[],
): AiStreamDenial {
  return { ok: false, status, code, message, hits };
}

function tokenMatches(expected: string, provided: string): boolean {
  const encoder = new TextEncoder();
  const expectedBytes = encoder.encode(expected);
  const providedBytes = encoder.encode(provided);
  const length = Math.max(expectedBytes.length, providedBytes.length);
  let diff = expectedBytes.length ^ providedBytes.length;
  for (let index = 0; index < length; index += 1) {
    diff |= (expectedBytes[index] ?? 0) ^ (providedBytes[index] ?? 0);
  }
  return diff === 0;
}

export function consumeStreamRateLimit(
  hits: readonly number[],
  nowMs: number,
): { allowed: boolean; hits: number[] } {
  const fresh = hits.filter((timestamp) => nowMs - timestamp < STREAM_RATE_WINDOW_MS);
  if (fresh.length >= STREAM_RATE_LIMIT) {
    return { allowed: false, hits: fresh };
  }
  fresh.push(nowMs);
  return { allowed: true, hits: fresh };
}

export function decideAiStream(env: AiStreamEnv, request: AiStreamRequest): AiStreamDecision {
  const hits = request.recentHits.filter(
    (timestamp) => request.nowMs - timestamp < STREAM_RATE_WINDOW_MS,
  );
  const authToken = env.authToken?.trim() ?? '';
  const model = (env.model?.trim() || DEFAULT_AI_STREAM_MODEL);
  if (env.enabled !== '1' || authToken.length < MIN_AUTH_TOKEN_CHARS || !model || /\s/.test(model)) {
    return denial(
      503,
      'disabled',
      'AI stream is disabled until AI_STREAM_ENABLED=1 and AI_STREAM_AUTH_TOKEN are configured.',
      hits,
    );
  }

  const header = request.authorizationHeader?.trim() ?? '';
  const prefix = 'Bearer ';
  const presented = header.startsWith(prefix) ? header.slice(prefix.length) : '';
  if (!presented || !tokenMatches(authToken, presented)) {
    return denial(401, 'auth', 'Authentication required.', hits);
  }

  if (request.requestedModel !== undefined && request.requestedModel !== model) {
    return denial(400, 'schema_invalid', 'Model is fixed by the server allowlist.', hits);
  }

  if (typeof request.prompt !== 'string' || request.prompt.trim().length === 0) {
    return denial(400, 'schema_invalid', 'Prompt is required.', hits);
  }

  const prompt = request.prompt.trim();
  if (prompt.length > MAX_PROMPT_CHARS) {
    return denial(413, 'schema_invalid', `Prompt must be ${MAX_PROMPT_CHARS} characters or fewer.`, hits);
  }

  const rate = consumeStreamRateLimit(hits, request.nowMs);
  if (!rate.allowed) {
    return denial(429, 'rate_limited', 'AI stream rate limit exceeded.', rate.hits);
  }

  return {
    ok: true,
    model,
    prompt,
    maxOutputTokens: MAX_OUTPUT_TOKENS,
    hits: rate.hits,
  };
}
