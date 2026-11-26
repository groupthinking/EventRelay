import assert from 'node:assert/strict';
import test from 'node:test';
import { readFileSync } from 'node:fs';
import {
  AI_STREAM_RATE_KEY,
  DEFAULT_AI_STREAM_MODEL,
  MAX_PROMPT_CHARS,
  STREAM_RATE_LIMIT,
  decideAiStream,
} from '../src/lib/ai-stream-guard.ts';

const TOKEN = 'stream-token-0123456789';

function env(overrides = {}) {
  return {
    enabled: '1',
    authToken: TOKEN,
    model: DEFAULT_AI_STREAM_MODEL,
    ...overrides,
  };
}

function request(overrides = {}) {
  return {
    authorizationHeader: `Bearer ${TOKEN}`,
    prompt: 'Summarize the selected agent export.',
    requestedModel: undefined,
    nowMs: 1_000_000,
    recentHits: [],
    ...overrides,
  };
}

test('stays disabled until the operator enables it and sets a token', () => {
  const disabled = decideAiStream(env({ enabled: undefined }), request());
  assert.equal(disabled.ok, false);
  if (!disabled.ok) assert.equal(disabled.status, 503);

  const missingToken = decideAiStream(env({ authToken: 'short' }), request());
  assert.equal(missingToken.ok, false);
  if (!missingToken.ok) assert.equal(missingToken.status, 503);
});

test('rejects anonymous and wrong-bearer callers before any model call', () => {
  const anonymous = decideAiStream(env(), request({ authorizationHeader: null }));
  assert.equal(anonymous.ok, false);
  if (!anonymous.ok) assert.equal(anonymous.status, 401);

  const wrong = decideAiStream(env(), request({ authorizationHeader: 'Bearer not-the-token' }));
  assert.equal(wrong.ok, false);
  if (!wrong.ok) assert.equal(wrong.status, 401);
});

test('rejects a caller-selected model and uses the server allowlist', () => {
  const rejected = decideAiStream(env(), request({ requestedModel: 'openai/gpt-4o' }));
  assert.equal(rejected.ok, false);
  if (!rejected.ok) assert.equal(rejected.status, 400);

  const allowed = decideAiStream(env(), request());
  assert.equal(allowed.ok, true);
  if (allowed.ok) assert.equal(allowed.model, DEFAULT_AI_STREAM_MODEL);
});

test('accepted credentials share one budget and padded headers are rejected', () => {
  const now = 1_000_000;
  const almostFull = Array.from({ length: STREAM_RATE_LIMIT - 1 }, () => now);
  const canonical = decideAiStream(env(), request({ nowMs: now, recentHits: almostFull }));
  assert.equal(canonical.ok, true);
  if (canonical.ok) assert.equal(canonical.rateLimitKey, AI_STREAM_RATE_KEY);

  const schemeVariant = decideAiStream(
    env(),
    request({
      authorizationHeader: `bearer ${TOKEN}`,
      nowMs: now,
      recentHits: canonical.hits,
    }),
  );
  assert.equal(schemeVariant.ok, false);
  if (!schemeVariant.ok) {
    assert.equal(schemeVariant.status, 429);
    assert.equal(schemeVariant.rateLimitKey, AI_STREAM_RATE_KEY);
  }

  for (const authorizationHeader of [
    `Bearer\u00A0${TOKEN}`,
    `\u00A0Bearer ${TOKEN}`,
    `Bearer ${TOKEN}\u00A0`,
    `Bearer  ${TOKEN}`,
  ]) {
    const padded = decideAiStream(env(), request({ authorizationHeader, nowMs: now, recentHits: [] }));
    assert.equal(padded.ok, false);
    if (!padded.ok) {
      assert.equal(padded.status, 401);
      assert.equal(padded.rateLimitKey, null);
    }
  }
});

test('route stores the budget on the canonical identity', () => {
  const source = readFileSync(new URL('../src/app/api/ai/stream/route.ts', import.meta.url), 'utf8');
  assert.match(source, /hitsByIdentity\.get\(AI_STREAM_RATE_KEY\)/);
  assert.match(source, /hitsByIdentity\.set\(decision\.rateLimitKey, decision\.hits\)/);
  assert.doesNotMatch(source, /authorizationHeader \?\?/);
});

test('caps prompt size and request rate', () => {
  const huge = decideAiStream(env(), request({ prompt: 'a'.repeat(MAX_PROMPT_CHARS + 1) }));
  assert.equal(huge.ok, false);
  if (!huge.ok) assert.equal(huge.status, 413);

  const saturated = decideAiStream(
    env(),
    request({
      recentHits: Array.from({ length: STREAM_RATE_LIMIT }, () => 1_000_000),
    }),
  );
  assert.equal(saturated.ok, false);
  if (!saturated.ok) assert.equal(saturated.status, 429);
});
