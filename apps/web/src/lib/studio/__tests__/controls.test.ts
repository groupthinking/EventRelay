import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { acquireStudioLock, checkStudioRate, completeStudioRequest, reserveStudioRequest, releaseStudioLock } from '../controls';
import * as controls from '../controls';

const fetchMock = vi.fn<typeof fetch>();
const owner = { subject: 'verified-owner' };
const chatId = '0b0b55ec-81f8-4cbf-91b3-75f67796b9c1';
const requestId = 'a77dc8f2-eaca-4ac5-910b-c5cb01234ced';
const requestHash = 'a'.repeat(64);

beforeEach(() => {
  vi.stubEnv('UPSTASH_REDIS_REST_URL', '');
  vi.stubEnv('UPSTASH_REDIS_REST_TOKEN', '');
  vi.stubEnv('KV_REST_API_URL', 'https://studio-kv.example');
  vi.stubEnv('KV_REST_API_TOKEN', 'offline-test-token');
  vi.stubGlobal('fetch', fetchMock);
  fetchMock.mockReset();
});
afterEach(() => { vi.unstubAllEnvs(); vi.unstubAllGlobals(); });
function reply(result: unknown) {
  return new Response(JSON.stringify({ result }), { headers: { 'content-type': 'application/json' } });
}
function command(index = 0): (string | number)[] {
  return JSON.parse(String(fetchMock.mock.calls[index][1]?.body));
}

describe('distributed Studio abuse and generation controls', () => {
  it('fails closed without REST storage rather than using Redis TCP or process memory', async () => {
    vi.stubEnv('KV_REST_API_URL', '');
    vi.stubEnv('REDIS_URL', 'redis://unrelated.example');
    await expect(checkStudioRate(owner, 'read')).rejects.toMatchObject({ status: 503 });
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it('uses one atomic expiring quota counter with a hashed subject in a separate namespace', async () => {
    fetchMock.mockResolvedValueOnce(reply(1));
    await expect(checkStudioRate(owner, 'mutation')).resolves.toBeUndefined();
    const sent = command();
    expect(sent[0]).toBe('eval');
    expect(String(sent[1])).toContain('INCR');
    expect(String(sent[1])).toContain('EXPIRE');
    expect(String(sent[3])).toMatch(/^uvai:studio:rate:mutation:[a-f0-9]{64}$/);
    expect(JSON.stringify(sent)).not.toContain(owner.subject);
  });

  it('returns a rate limit rather than permitting excess requests', async () => {
    fetchMock.mockResolvedValueOnce(reply(999));
    await expect(checkStudioRate(owner, 'mutation')).rejects.toMatchObject({ status: 429, code: 'rate_limited' });
  });

  it('does not fail open when the REST service times out', async () => {
    fetchMock.mockRejectedValueOnce(new Error('private-provider-detail'));
    await expect(checkStudioRate(owner, 'read')).rejects.toMatchObject({ status: 503, code: 'controls_unavailable' });
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it('uses NX and an expiry to arbitrate simultaneous chat mutations', async () => {
    fetchMock.mockResolvedValueOnce(reply('OK'));
    const lock = await acquireStudioLock(owner, chatId);
    expect(lock.token).toMatch(/^[a-f0-9-]{36}$/);
    expect(command()).toEqual(['set', expect.stringContaining('uvai:studio:lock:'), lock.token, 'nx', 'ex', 90]);
  });

  it('rejects a concurrent mutation without contacting the builder', async () => {
    fetchMock.mockResolvedValueOnce(reply(null));
    await expect(acquireStudioLock(owner, chatId)).rejects.toMatchObject({ status: 409, code: 'chat_busy' });
  });

  it('only releases a lock if its random token still matches', async () => {
    fetchMock.mockResolvedValueOnce(reply('OK')).mockResolvedValueOnce(reply(1));
    const lock = await acquireStudioLock(owner, chatId);
    await releaseStudioLock(lock);
    expect(command(1)[0]).toBe('eval');
    expect(String(command(1)[1])).toContain("redis.call('GET', KEYS[1]) == ARGV[1]");
    expect(command(1).slice(3)).toEqual([lock.key, lock.token]);
  });

  it('atomically reserves a follow-up request before sending it upstream', async () => {
    fetchMock.mockResolvedValueOnce(reply(['new', '']));
    await expect(reserveStudioRequest(owner, chatId, requestId, requestHash)).resolves.toBeNull();
    expect(command()[0]).toBe('eval');
    expect(String(command()[3])).toContain('uvai:studio:request:');
  });

  it('replays a matching receipt without generating twice', async () => {
    fetchMock.mockResolvedValueOnce(reply(['existing', JSON.stringify({ hash: requestHash, messageId: 'message-1' })]));
    await expect(reserveStudioRequest(owner, chatId, requestId, requestHash)).resolves.toBe('message-1');
  });

  it('does not retry a request with an unknown upstream outcome', async () => {
    fetchMock.mockResolvedValueOnce(reply(['existing', JSON.stringify({ hash: requestHash, messageId: null })]));
    await expect(reserveStudioRequest(owner, chatId, requestId, requestHash)).rejects.toMatchObject({ status: 409, code: 'request_pending' });
  });

  it('rejects reuse of an idempotency key for different content', async () => {
    fetchMock.mockResolvedValueOnce(reply(['existing', JSON.stringify({ hash: 'b'.repeat(64), messageId: 'message-1' })]));
    await expect(reserveStudioRequest(owner, chatId, requestId, requestHash)).rejects.toMatchObject({ status: 409, code: 'request_conflict' });
  });

  it('reads a retry receipt without reserving a new request prematurely', async () => {
    expect(controls.readStudioRequest).toBeTypeOf('function');
    fetchMock.mockResolvedValueOnce(reply(null));
    expect(await controls.readStudioRequest(owner, chatId, requestId, requestHash)).toBeNull();
    expect(command()[0]).toBe('get');
  });

  it('retains a chat-bound unknown outcome beyond the short mutation lock', async () => {
    expect(controls.rememberStudioTurn).toBeTypeOf('function');
    fetchMock.mockResolvedValueOnce(reply('OK'));
    const turn = { requestId, previousMessageId: 'previous', messageId: null };
    await controls.rememberStudioTurn(owner, chatId, turn);
    expect(command()).toEqual(['set', expect.stringContaining('uvai:studio:turn:'), JSON.stringify(turn)]);
  });

  it('fails closed on a corrupted persistent generation marker', async () => {
    expect(controls.getStudioTurn).toBeTypeOf('function');
    fetchMock.mockResolvedValueOnce(reply('{"messageId":1}'));
    await expect(controls.getStudioTurn(owner, chatId)).rejects.toMatchObject({ status: 503 });
  });

  it('only forgets a generation marker for the matching request', async () => {
    expect(controls.forgetStudioTurn).toBeTypeOf('function');
    fetchMock.mockResolvedValueOnce(reply(1));
    await controls.forgetStudioTurn(owner, chatId, requestId);
    expect(command()[0]).toBe('eval');
    expect(String(command()[1])).toContain('requestId');
    expect(command().at(-1)).toBe(requestId);
  });

  it('atomically checks the lease before a generation can be marked for submission', async () => {
    fetchMock.mockResolvedValueOnce(reply(1));
    const turn = { requestId, previousMessageId: 'previous', messageId: null };
    await controls.rememberStudioTurn(owner, chatId, turn, { key: 'lock-key', token: 'lease-token' });
    expect(command()[0]).toBe('eval');
    expect(String(command()[1])).toContain("redis.call('GET', KEYS[2]) ~= ARGV[2]");
    expect(command()).toContain('lease-token');
  });

  it('rejects an expired lease instead of submitting after another request took over', async () => {
    fetchMock.mockResolvedValueOnce(reply(0));
    await expect(controls.rememberStudioTurn(owner, chatId, { requestId, previousMessageId: 'previous', messageId: null }, { key: 'lock-key', token: 'expired' })).rejects.toMatchObject({ status: 409, code: 'chat_busy' });
  });

  it('records only the upstream message receipt, never prompts or credentials', async () => {
    fetchMock.mockResolvedValueOnce(reply(1));
    await completeStudioRequest(owner, chatId, requestId, requestHash, 'message-1');
    expect(command()[0]).toBe('eval');
    expect(command().at(-1)).toBe(JSON.stringify({ hash: requestHash, messageId: 'message-1' }));
  });
});
