import 'server-only';

import { resolveUpstashRedisCredentials } from '@/lib/billing/redis-credentials';
import { canonicalGateJson } from '@/lib/gate-transition';
import { evaluateOriginGate, type OriginGateStore } from '@/lib/origin-gate';

export const ORIGIN_GATE_POLICY_KEY = 'er:gate:v2:trusted-policy';
export const COMMIT_ORIGIN_GATE_SCRIPT = `
if ARGV[2] == 'PASS' and redis.call('GET', KEYS[#KEYS]) ~= ARGV[4] then
  return { 'policy_changed' }
end
local prior = redis.call('GET', KEYS[1])
if prior then return { 'existing', prior } end
if ARGV[2] == 'PASS' then
  for i = 2, #KEYS - 1 do
    if redis.call('EXISTS', KEYS[i]) == 1 then return { 'conflict' } end
  end
  for i = 2, #KEYS - 1 do redis.call('SET', KEYS[i], ARGV[3]) end
end
redis.call('SET', KEYS[1], ARGV[1])
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
      const keys = [`er:gate:v2:receipt:${requestHash}`, `er:gate:v2:transition:${transitionKey}`, ...nonceKeys.map((nonce) => `er:gate:v2:nonce:${nonce}`), ORIGIN_GATE_POLICY_KEY];
      const result = await command(['EVAL', COMMIT_ORIGIN_GATE_SCRIPT, keys.length, ...keys, canonicalGateJson(evaluation), evaluation.decision, requestHash, policySnapshot ?? '']);
      if (!Array.isArray(result)) throw new Error('Invalid GATE commit response');
      if (result[0] === 'stored') return { status: 'stored' };
      if (result[0] === 'conflict') return { status: 'conflict' };
      if (result[0] === 'existing' && typeof result[1] === 'string') return { status: 'existing', evaluation: JSON.parse(result[1]) as unknown };
      throw new Error('Invalid GATE commit response');
    },
  };
}

export function decideOriginGate(input: unknown, subject: string) {
  return evaluateOriginGate(input, { subject, signingSecret: process.env.NEXTAUTH_SECRET ?? '', store: createOriginGateStore() });
}
