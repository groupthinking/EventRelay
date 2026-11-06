import { text } from 'node:stream/consumers';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { getGlobalDispatcher, MockAgent, setGlobalDispatcher } from 'undici';
import { createWorkflowTaskRecord, readWorkflowTask } from '../workflow-task-store';

const input = { title: 'Review source', description: 'Private task fixture', category: 'research', priority: 'high' };
const taskId = 'a'.repeat(64);
// Native fetch may hand the mock an async iterable rather than a string body.
const requestText = (body: unknown) => typeof body === 'string'
  ? Promise.resolve(body) : text(body as AsyncIterable<Uint8Array>);
const records = new Map<string, string>();
const transport = vi.fn(async (_url: unknown, init?: RequestInit) => {
  const command = JSON.parse(String(init?.body));
  const [op] = command;
  const key = command[op === 'EVAL' ? 3 : 1];
  const value = command[5];
  let result: unknown = null;
  // Model initialized owners with sufficient capacity; this fixture does not execute Lua.
  if (op === 'EVAL') {
    result = [records.has(key) ? 'existing' : 'stored'];
    if (!records.has(key)) records.set(key, value);
  }
  if (op === 'GET') result = records.get(key) ?? null;
  return Response.json({ result });
});

describe('workflow task storage transport boundary', () => {
  beforeEach(() => {
    vi.stubEnv('UPSTASH_REDIS_REST_URL', 'https://store.invalid');
    vi.stubEnv('UPSTASH_REDIS_REST_TOKEN', 'isolated-fixture-token');
    vi.stubEnv('KV_REST_API_URL', ''); vi.stubEnv('KV_REST_API_TOKEN', '');
    records.clear(); transport.mockClear();
  });
  afterEach(() => vi.unstubAllEnvs());

  it.each([
    'http://store.invalid', 'ftp://store.invalid', '//store.invalid', 'not a URL',
    'https://', 'https://username:password@store.invalid', 'https://username@store.invalid',
    'https://:password@store.invalid', 'https://%75ser:%70ass@store.invalid',
  ])('rejects unsafe or malformed endpoint %s before exposing credentials or command data', async endpoint => {
    vi.stubEnv('UPSTASH_REDIS_REST_URL', endpoint);
    await expect(createWorkflowTaskRecord(input, 'alice', 'run', transport)).rejects.toThrow('storage is unavailable');
    await expect(readWorkflowTask('alice', taskId, transport)).rejects.toThrow('storage is unavailable');
    expect(transport).not.toHaveBeenCalled();
  });

  it('preserves HTTPS writes, readback, retry and GET with explicit redirect rejection', async () => {
    const first = await createWorkflowTaskRecord(input, 'alice', 'run', transport);
    const retry = await createWorkflowTaskRecord(input, 'alice', 'run', transport);
    expect(retry).toEqual(first);
    expect(await readWorkflowTask('alice', first.id, transport)).toEqual(first);
    expect(records.size).toBe(1);
    for (const [url, init] of transport.mock.calls) {
      expect(url).toBe('https://store.invalid');
      expect(init?.redirect).toBe('error');
      expect(init?.headers).toEqual({ Authorization: 'Bearer isolated-fixture-token', 'Content-Type': 'application/json' });
    }
  });

  it('applies the same transport policy to the supported KV credential pair', async () => {
    vi.stubEnv('UPSTASH_REDIS_REST_URL', ''); vi.stubEnv('UPSTASH_REDIS_REST_TOKEN', '');
    vi.stubEnv('KV_REST_API_URL', 'https://kv.invalid'); vi.stubEnv('KV_REST_API_TOKEN', 'isolated-kv-token');
    expect(await readWorkflowTask('alice', taskId, transport)).toBeNull();
    expect(transport).toHaveBeenCalledWith('https://kv.invalid', expect.objectContaining({ redirect: 'error' }));
    transport.mockClear();
    vi.stubEnv('KV_REST_API_URL', 'http://kv.invalid');
    await expect(readWorkflowTask('alice', taskId, transport)).rejects.toThrow('storage is unavailable');
    expect(transport).not.toHaveBeenCalled();
  });

  it.each(['HTTPS://store.invalid', 'https://store.invalid:8443/rest?region=fixture'])('preserves HTTPS endpoint configuration %s', async endpoint => {
    vi.stubEnv('UPSTASH_REDIS_REST_URL', endpoint);
    expect(await readWorkflowTask('alice', taskId, transport)).toBeNull();
    expect(transport).toHaveBeenCalledWith(endpoint, expect.objectContaining({ redirect: 'error' }));
  });

  it.each([301, 302, 303, 307, 308])('real fetch rejects HTTP %s without contacting its redirect target', async status => {
    const dispatcher = new MockAgent();
    dispatcher.disableNetConnect();
    const forwarded: Array<{ method: string; body: unknown }> = [];
    let saved = '';
    dispatcher.get('https://store.invalid').intercept({ path: '/', method: 'POST' })
      .reply(status, async options => {
        const command = JSON.parse(await requestText(options.body));
        expect(command[0]).toBe('EVAL');
        saved = command[5];
        return '';
      }, {
        headers: { location: 'https://redirect.invalid/collect' },
      });
    dispatcher.get('https://redirect.invalid').intercept({ path: '/collect', method: status === 307 || status === 308 ? 'POST' : 'GET' })
      .reply(200, async options => { forwarded.push({ method: options.method, body: options.body == null ? null : await requestText(options.body) }); return JSON.stringify({ result: ['stored'] }); });
    dispatcher.get('https://store.invalid').intercept({ path: '/', method: 'POST' })
      .reply(200, async options => {
        expect(JSON.parse(await requestText(options.body))[0]).toBe('GET');
        return JSON.stringify({ result: saved });
      });
    const previousDispatcher = getGlobalDispatcher();
    // Undici 8 installs the compatibility adapter required by Node 22's native fetch.
    // Passing its MockAgent directly as a fetch dispatcher bypasses that adapter.
    setGlobalDispatcher(dispatcher);
    try {
      let failure: unknown;
      try { await createWorkflowTaskRecord(input, 'alice', 'run', fetch); } catch (error) { failure = error; }
      expect(JSON.parse(saved)).toMatchObject(input);
      expect(forwarded).toEqual([]);
      expect(failure).toBeInstanceOf(Error);
    } finally {
      setGlobalDispatcher(previousDispatcher);
      await dispatcher.close();
    }
  });

  it.each(['https://store.invalid/other', 'http://redirect.invalid/collect'])('real fetch also rejects read redirects to %s', async target => {
    const dispatcher = new MockAgent();
    dispatcher.disableNetConnect();
    let forwarded = 0;
    let initialRequests = 0;
    dispatcher.get('https://store.invalid').intercept({ path: '/', method: 'POST' })
      .reply(307, async options => {
        expect(JSON.parse(await requestText(options.body))[0]).toBe('GET');
        initialRequests++;
        return '';
      }, { headers: { location: target } });
    const destination = new URL(target);
    dispatcher.get(destination.origin).intercept({ path: destination.pathname, method: 'POST' })
      .reply(200, () => { forwarded++; return JSON.stringify({ result: null }); });
    const previousDispatcher = getGlobalDispatcher();
    // Undici 8 installs the compatibility adapter required by Node 22's native fetch.
    // Passing its MockAgent directly as a fetch dispatcher bypasses that adapter.
    setGlobalDispatcher(dispatcher);
    try {
      await expect(readWorkflowTask('alice', taskId, fetch)).rejects.toThrow();
      expect(initialRequests).toBe(1);
      expect(forwarded).toBe(0);
    } finally {
      setGlobalDispatcher(previousDispatcher);
      await dispatcher.close();
    }
  });
});
