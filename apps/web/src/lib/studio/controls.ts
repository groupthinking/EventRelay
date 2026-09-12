import 'server-only';

import { createHash, randomUUID } from 'node:crypto';
import { Redis } from '@upstash/redis';
import { z } from 'zod';
import { resolveUpstashRedisCredentials } from '@/lib/billing/redis-credentials';
import { StudioError } from './errors';
import type { StudioOwner } from './security';

const RATE_SCRIPT = `
local used = redis.call('INCR', KEYS[1])
if used == 1 then redis.call('EXPIRE', KEYS[1], 60) end
return used
`;
const RELEASE_SCRIPT = `
if redis.call('GET', KEYS[1]) == ARGV[1] then return redis.call('DEL', KEYS[1]) end
return 0
`;
const RESERVE_SCRIPT = `
local previous = redis.call('GET', KEYS[1])
if previous then return { 'existing', previous } end
redis.call('SET', KEYS[1], ARGV[1], 'EX', 86400)
return { 'new', '' }
`;
const COMPLETE_SCRIPT = `
local raw = redis.call('GET', KEYS[1])
if not raw then return 0 end
local current = cjson.decode(raw)
if current.hash ~= ARGV[1] then return 0 end
redis.call('SET', KEYS[1], ARGV[2], 'KEEPTTL')
return 1
`;
const receiptSchema = z.object({ hash: z.string().regex(/^[a-f0-9]{64}$/), messageId: z.string().min(1).max(256).nullable() }).strict();

function unavailable() {
  return new StudioError(503, 'controls_unavailable', 'Studio request controls are unavailable. Try again later.');
}

export function studioRedis(): Redis {
  const credentials = resolveUpstashRedisCredentials();
  if (!credentials) throw unavailable();
  try {
    const url = new URL(credentials.url);
    if (url.protocol !== 'https:' || url.username || url.password) throw unavailable();
    // This SDK treats retry:false as one retry; an explicit zero avoids double-counting.
    return new Redis({
      ...credentials,
      retry: { retries: 0 },
      responseEncoding: 'utf-8',
      automaticDeserialization: false,
      enableAutoPipelining: false,
      signal: () => AbortSignal.timeout(5_000),
    });
  } catch { throw unavailable(); }
}

function ownerKey(owner: StudioOwner): string {
  if (!owner.subject?.trim() || owner.subject.length > 512) throw new StudioError(401, 'authentication_required', 'Sign in to use the app builder.');
  return createHash('sha256').update(owner.subject).digest('hex');
}
function requestKey(owner: StudioOwner, chatId: string, requestId: string): string {
  if (!z.uuid().safeParse(chatId).success || !z.uuid().safeParse(requestId).success) {
    throw new StudioError(400, 'invalid_request', 'Invalid Studio request identifier.');
  }
  return `uvai:studio:request:${ownerKey(owner)}:${chatId}:${requestId}`;
}
async function controlled<T>(operation: () => Promise<T>): Promise<T> {
  try { return await operation(); } catch (error) {
    if (error instanceof StudioError) throw error;
    throw unavailable();
  }
}

export async function checkStudioRate(owner: StudioOwner, kind: 'read' | 'mutation'): Promise<void> {
  const used = await controlled(() => studioRedis().eval<number>(RATE_SCRIPT, [`uvai:studio:rate:${kind}:${ownerKey(owner)}`], []));
  if (!Number.isInteger(used) || used < 1) throw unavailable();
  if (used > (kind === 'read' ? 120 : 10)) throw new StudioError(429, 'rate_limited', 'Too many Studio requests. Wait a minute and try again.');
}

export type StudioLock = Readonly<{ key: string; token: string }>;
export async function acquireStudioLock(owner: StudioOwner, chatId: string): Promise<StudioLock> {
  if (!z.uuid().safeParse(chatId).success) throw new StudioError(400, 'invalid_chat_id', 'Invalid Studio chat identifier.');
  const lock = { key: `uvai:studio:lock:${ownerKey(owner)}:${chatId}`, token: randomUUID() };
  const result = await controlled(() => studioRedis().set(lock.key, lock.token, { nx: true, ex: 90 }));
  if (result === null) throw new StudioError(409, 'chat_busy', 'Another Studio request is in progress. Reload this chat.');
  if (result !== 'OK') throw unavailable();
  return lock;
}
export async function releaseStudioLock(lock: StudioLock): Promise<void> {
  await controlled(() => studioRedis().eval(RELEASE_SCRIPT, [lock.key], [lock.token]));
}

export async function reserveStudioRequest(owner: StudioOwner, chatId: string, requestId: string, hash: string): Promise<string | null> {
  if (!receiptSchema.shape.hash.safeParse(hash).success) throw new StudioError(400, 'invalid_request', 'Invalid request fingerprint.');
  const result = await controlled(() => studioRedis().eval<unknown>(RESERVE_SCRIPT, [requestKey(owner, chatId, requestId)], [JSON.stringify({ hash, messageId: null })]));
  if (!Array.isArray(result) || result.length !== 2) throw unavailable();
  if (result[0] === 'new' && result[1] === '') return null;
  if (result[0] !== 'existing' || typeof result[1] !== 'string') throw unavailable();
  let data: unknown;
  try { data = JSON.parse(result[1]); } catch { throw unavailable(); }
  const parsed = receiptSchema.safeParse(data);
  if (!parsed.success) throw unavailable();
  if (parsed.data.hash !== hash) throw new StudioError(409, 'request_conflict', 'This request identifier belongs to different content.');
  if (!parsed.data.messageId) throw new StudioError(409, 'request_pending', 'The earlier request has an unknown outcome. Reload the chat; do not resubmit it.');
  return parsed.data.messageId;
}

export async function completeStudioRequest(owner: StudioOwner, chatId: string, requestId: string, hash: string, messageId: string): Promise<void> {
  const receipt = receiptSchema.safeParse({ hash, messageId });
  if (!receipt.success) throw unavailable();
  const saved = await controlled(() => studioRedis().eval<number>(COMPLETE_SCRIPT, [requestKey(owner, chatId, requestId)], [hash, JSON.stringify(receipt.data)]));
  if (saved !== 1) throw unavailable();
}
