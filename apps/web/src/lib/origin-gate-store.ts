import 'server-only';

import { resolveUpstashRedisCredentials } from '@/lib/billing/redis-credentials';
import { canonicalGateJson, hashCanonical } from '@/lib/gate-transition';
import { evaluateOriginGate, type OriginGateStore } from '@/lib/origin-gate';

export const ORIGIN_GATE_POLICY_KEY = 'er:gate:v2:trusted-policy';
const NON_PASS_RETENTION_SECONDS = 24 * 60 * 60;
const MAX_NON_PASS_RECEIPTS_PER_SUBJECT = 100;

// Only PASS is immutable: re-evaluation of a negative receipt must not bypass replay or policy checks.
export const COMMIT_ORIGIN_GATE_SCRIPT = `
if ARGV[2] == 'PASS' and redis.call('GET', KEYS[#KEYS]) ~= ARGV[4] then
  return { 'policy_changed' }
end
local prior = redis.call('GET', KEYS[1])
if prior and cjson.decode(prior).decision == 'PASS' then return { 'existing', prior } end
if ARGV[2] == 'PASS' then
  for i = 3, #KEYS - 1 do
    if redis.call('EXISTS', KEYS[i]) == 1 then return { 'conflict' } end
  end
  redis.call('ZREM', KEYS[2], KEYS[1])
  for i = 3, #KEYS - 1 do redis.call('SET', KEYS[i], ARGV[3]) end
  redis.call('SET', KEYS[1], ARGV[1])
else
  local time = redis.call('TIME')
  local now = tonumber(time[1]) * 1000 + math.ceil(tonumber(time[2]) / 1000)
  redis.call('ZREMRANGEBYSCORE', KEYS[2], '-inf', now)
  if not redis.call('ZSCORE', KEYS[2], KEYS[1]) and redis.call('ZCARD', KEYS[2]) >= tonumber(ARGV[6]) then
    return { 'quota' }
  end
  redis.call('ZADD', KEYS[2], now + tonumber(ARGV[5]) * 1000, KEYS[1])
  redis.call('EXPIRE', KEYS[2], ARGV[5])
  redis.call('SET', KEYS[1], ARGV[1], 'EX', ARGV[5])
end
return { 'stored' }
`;

export function createOriginGateStore(): OriginGateStore {
  let policySnapshot: string | null = null;
  const command = async (args: Array<string | number>): Promise<unknown> => {
    const credentials = resolveUpstashRedisCredentials();
    if (!credentials || !credentials.url.startsWith('https://')) throw new Error('GATE runtime unavailable');
    const response = await fetch(credentials.url, {
      method: 'POST',
      headers: { authorization: `Bearer ${credentials.token}`, 'content-type': 'application/json' },
      body: JSON.stringify(args),
      cache: 'no-store',
      redirect: 'error',
      signal: AbortSignal.timeout(5000),
    });
    if (!response.ok) throw new Error('GATE runtime unavailable');
    const payload: unknown = await response.json();
    if (!payload || typeof payload !== 'object' || !('result' in payload) || 'error' in payload) throw new Error('Invalid GATE runtime response');
    return payload.result;
  };
  return {
    async readPolicy() {
      const raw = await command(['GET', ORIGIN_GATE_POLICY_KEY]);
      policySnapshot = typeof raw === 'string' ? raw : null;
      return typeof raw === 'string' ? JSON.parse(raw) : raw;
    },
    async commit({ requestHash, transitionKey, nonceKeys, evaluation }) {
      if (evaluation.decision === 'PASS' && !policySnapshot) throw new Error('Missing trusted policy snapshot');
      const subject = evaluation.receipt.authority.claim;
      if (!subject) throw new Error('Missing authenticated receipt subject');
      const keys = [`er:gate:v2:receipt:${requestHash}`, `er:gate:v2:pending:${hashCanonical(subject)}`, `er:gate:v2:transition:${transitionKey}`, ...nonceKeys.map((nonce) => `er:gate:v2:nonce:${nonce}`), ORIGIN_GATE_POLICY_KEY];
      const result = await command(['EVAL', COMMIT_ORIGIN_GATE_SCRIPT, keys.length, ...keys, canonicalGateJson(evaluation), evaluation.decision, requestHash, policySnapshot ?? '', NON_PASS_RETENTION_SECONDS, MAX_NON_PASS_RECEIPTS_PER_SUBJECT]);
      if (!Array.isArray(result)) throw new Error('Invalid GATE commit response');
      if (result[0] === 'stored') return { status: 'stored' };
      if (result[0] === 'conflict') return { status: 'conflict' };
      if (result[0] === 'quota') return { status: 'quota' };
      if (result[0] === 'existing' && typeof result[1] === 'string') return { status: 'existing', evaluation: JSON.parse(result[1]) as unknown };
      throw new Error('Invalid GATE commit response');
    },
  };
}

export function decideOriginGate(input: unknown, subject: string) {
  return evaluateOriginGate(input, { subject, signingSecret: process.env.NEXTAUTH_SECRET ?? '', store: createOriginGateStore() });
}
