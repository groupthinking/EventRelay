import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { executePreparedActions } from '../action-agent';
import type { AgentAction } from '../action-lifecycle';

function task(index: number): AgentAction {
  return { tool: 'create_workflow_task', status: 'pending', input: {
    title: `Task ${index}`, description: 'Inspect source evidence', category: 'research', priority: 'high',
  } };
}
const options = { ownerId: 'alice', jobId: 'original-confirmed-run' };

describe('confirmed task batch storage outage', () => {
  beforeEach(() => {
    vi.stubEnv('UPSTASH_REDIS_REST_URL', 'https://store.invalid');
    vi.stubEnv('UPSTASH_REDIS_REST_TOKEN', 'fixture');
  });
  afterEach(() => { vi.restoreAllMocks(); vi.useRealTimers(); vi.unstubAllEnvs(); });

  it('spends one 10-second EVAL timeout rather than 50 serial timeouts', async () => {
    vi.useFakeTimers();
    vi.spyOn(AbortSignal, 'timeout').mockImplementation(milliseconds => {
      const controller = new AbortController();
      setTimeout(() => controller.abort(new DOMException('Fixture timeout', 'TimeoutError')), milliseconds);
      return controller.signal;
    });
    const transport = vi.fn(async (_url: unknown, init?: RequestInit) => new Promise<Response>((_resolve, reject) => {
      init?.signal?.addEventListener('abort', () => reject(init.signal?.reason), { once: true });
    }));
    const start = Date.now();
    const result = executePreparedActions({ ...options, actions: Array.from({ length: 50 }, (_, i) => task(i)), fetchImpl: transport });
    await vi.runAllTimersAsync();
    const actions = await result;
    expect(Date.now() - start).toBe(10_000);
    expect(transport).toHaveBeenCalledTimes(1);
    expect(actions).toHaveLength(50);
    expect(actions.every(action => action.status === 'failed' && action.data === undefined)).toBe(true);
    expect(actions[1].result).toMatch(/not attempted/i);
  });

  it('stops new task writes immediately after a 503', async () => {
    const transport = vi.fn(async () => new Response('unavailable', { status: 503 }));
    const actions = await executePreparedActions({ ...options, actions: [task(1), task(2), task(3)], fetchImpl: transport });
    expect(transport).toHaveBeenCalledTimes(1);
    expect(actions.map(action => action.status)).toEqual(['failed', 'failed', 'failed']);
    expect(actions[0].result).toMatch(/not confirmed saved/i);
    expect(actions[1].result).toMatch(/not attempted/i);
  });

  it('retains earlier receipts, stops after uncertain readback, and recovers with the same run', async () => {
    const records = new Map<string, string>();
    let failedReadKey: string | undefined;
    let outage = true;
    const transport = vi.fn(async (_url: unknown, init?: RequestInit) => {
      const command = JSON.parse(String(init?.body));
      const [operation] = command;
      const key = command[operation === 'EVAL' ? 3 : 1];
      const value = command[5];
      let result: unknown = null;
      if (operation === 'EVAL') {
        result = [records.has(key) ? 'existing' : 'stored'];
        if (!records.has(key)) {
          records.set(key, value);
          if (records.size === 2) failedReadKey = key;
        }
      }
      if (operation === 'GET') {
        if (outage && key === failedReadKey) return new Response('unavailable', { status: 503 });
        result = records.get(key) ?? null;
      }
      return Response.json({ result });
    });
    const confirmed = [task(1), task(2), task(3)];
    const first = await executePreparedActions({ ...options, actions: confirmed, fetchImpl: transport });
    expect(records.size).toBe(2);
    expect(first.map(action => action.status)).toEqual(['fulfilled', 'failed', 'failed']);
    expect(first[0].data?.id).toMatch(/^[a-f0-9]{64}$/);
    expect(first[1].data).toBeUndefined();
    expect(first[2].result).toMatch(/not attempted/i);
    const storedBeforeRetry = [...records.values()].map(value => JSON.parse(value).id);
    outage = false;
    const retry = await executePreparedActions({ ...options, actions: confirmed, fetchImpl: transport });
    expect(retry.every(action => action.status === 'fulfilled')).toBe(true);
    expect(retry[0].data).toEqual(first[0].data);
    expect(retry.slice(0, 2).map(action => action.data?.id)).toEqual(storedBeforeRetry);
    expect(records.size).toBe(3);
  });

  it('does not misclassify invalid task inputs as a storage outage', async () => {
    const records = new Map<string, string>();
    const transport = vi.fn(async (_url: unknown, init?: RequestInit) => {
      const command = JSON.parse(String(init?.body));
      const [operation] = command;
      const key = command[operation === 'EVAL' ? 3 : 1];
      const value = command[5];
      if (operation === 'EVAL') { records.set(key, value); return Response.json({ result: ['stored'] }); }
      return Response.json({ result: records.get(key) ?? null });
    });
    const invalid = { ...task(1), input: { title: '' } };
    const actions = await executePreparedActions({ ...options, actions: [invalid, task(2)], fetchImpl: transport });
    expect(actions.map(action => action.status)).toEqual(['failed', 'fulfilled']);
    expect(records.size).toBe(1);
    expect(transport).toHaveBeenCalledTimes(2);
  });

  it('keeps unrelated non-task actions in their existing order after a task outage', async () => {
    const transport = vi.fn(async () => new Response('unavailable', { status: 503 }));
    const resource: AgentAction = { tool: 'save_resource', status: 'pending', input: { name: 'Source', kind: 'article', reason: 'Review' } };
    const actions = await executePreparedActions({ ...options, actions: [task(1), resource, task(2)], fetchImpl: transport });
    expect(actions.map(action => action.tool)).toEqual(['create_workflow_task', 'save_resource', 'create_workflow_task']);
    expect(actions.map(action => action.status)).toEqual(['failed', 'fulfilled', 'failed']);
    expect(transport).toHaveBeenCalledTimes(1);
  });

  it.each(['invalid-json', 'null-body', 'missing-result', 'redis-error', 'invalid-eval-result',
    'invalid-stored-json', 'null-record', 'invalid-stored-fields', 'missing-readback', 'mismatched-run', 'mismatched-fields'])('stops task writes on %s', async failure => {
    let saved: Record<string, unknown> = {};
    const transport = vi.fn(async (_url: unknown, init?: RequestInit) => {
      const [operation, , , , , value] = JSON.parse(String(init?.body));
      if (operation === 'EVAL') {
        saved = JSON.parse(value);
        if (failure === 'invalid-json') return new Response('not JSON');
        if (failure === 'null-body') return Response.json(null);
        if (failure === 'missing-result') return Response.json({});
        if (failure === 'redis-error') return Response.json({ error: 'fixture failure', result: null });
        if (failure === 'invalid-eval-result') return Response.json({ result: false });
        return Response.json({ result: ['stored'] });
      }
      if (failure === 'invalid-stored-json') return Response.json({ result: 'not JSON' });
      if (failure === 'null-record') return Response.json({ result: 'null' });
      if (failure === 'missing-readback') return Response.json({ result: null });
      if (failure === 'invalid-stored-fields') saved.title = '';
      if (failure === 'mismatched-run') saved.jobId = 'another-run';
      if (failure === 'mismatched-fields') saved.title = 'Different valid title';
      return Response.json({ result: JSON.stringify(saved) });
    });
    const actions = await executePreparedActions({ ...options, actions: [task(1), task(2)], fetchImpl: transport });
    expect(actions.map(action => action.status)).toEqual(['failed', 'failed']);
    expect(actions[1].result).toMatch(/not attempted/i);
    const writeFailures = ['invalid-json', 'null-body', 'missing-result', 'redis-error', 'invalid-eval-result'];
    expect(transport).toHaveBeenCalledTimes(writeFailures.includes(failure) ? 1 : 2);
    expect(JSON.parse(String(transport.mock.calls[0][1]?.body))[0]).toBe('EVAL');
    if (!writeFailures.includes(failure)) {
      expect(JSON.parse(String(transport.mock.calls[1][1]?.body))[0]).toBe('GET');
    }
    expect(actions.every(action => action.data === undefined)).toBe(true);
  });

  it('stops after unavailable storage configuration without exposing internal flags or stale receipts', async () => {
    for (const name of ['UPSTASH_REDIS_REST_URL', 'UPSTASH_REDIS_REST_TOKEN', 'KV_REST_API_URL', 'KV_REST_API_TOKEN']) vi.stubEnv(name, '');
    const transport = vi.fn();
    const actions = await executePreparedActions({ ...options, actions: [task(1), { ...task(2), data: { id: 'stale' } }], fetchImpl: transport });
    expect(actions[1].result).toMatch(/not attempted/i);
    expect(transport).not.toHaveBeenCalled();
    expect(JSON.stringify(actions)).not.toContain('storageUnavailable');
    expect(actions.every(action => action.data === undefined)).toBe(true);
  });

  it('bounds a sequence of slow successful writes, preserves readback receipts and permits exact-run retries', async () => {
    let now = 1_000;
    let operationLatency = 6_000;
    vi.spyOn(Date, 'now').mockImplementation(() => now);
    const records = new Map<string, string>();
    const transport = vi.fn(async (_url: unknown, init?: RequestInit) => {
      const args = JSON.parse(String(init?.body));
      const [operation] = args;
      const key = args[operation === 'EVAL' ? 3 : 1];
      now += operationLatency;
      if (operation === 'EVAL') {
        const existed = records.has(key);
        if (!existed) records.set(key, args[5]);
        return Response.json({ result: [existed ? 'existing' : 'stored'] });
      }
      return Response.json({ result: records.get(key) ?? null });
    });
    const plan = [task(1), task(2), task(3), task(4)];
    const first = await executePreparedActions({ ...options, actions: plan, fetchImpl: transport });
    expect(first.map(action => action.status)).toEqual(['fulfilled', 'fulfilled', 'failed', 'failed']);
    expect(first[0].data?.id).toMatch(/^[a-f0-9]{64}$/);
    expect(first[1].data?.id).toMatch(/^[a-f0-9]{64}$/);
    expect(first[2].data).toBeUndefined(); // EVAL may have committed, but GET missed the deadline.
    expect(first[3].result).toMatch(/not attempted/i);
    expect(transport).toHaveBeenCalledTimes(5); // 2 readbacks + 3 EVALs, no further I/O.
    expect(records.size).toBe(3);

    operationLatency = 0;
    const retry = await executePreparedActions({ ...options, actions: plan, fetchImpl: transport });
    expect(retry.every(action => action.status === 'fulfilled')).toBe(true);
    expect(retry.slice(0, 2).map(action => action.data)).toEqual(first.slice(0, 2).map(action => action.data));
    expect(records.size).toBe(4);
  });
});
