import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { encode } from 'next-auth/jwt';
import { createWorkflowTaskRecord, readWorkflowTask, workflowTaskOwner } from '../workflow-task-store';
import { executePreparedActions } from '../action-agent';

const input = { title: 'Install pnpm', description: 'Set up the toolchain', category: 'setup', priority: 'high' };
const records = new Map<string, string>();
const transport = vi.fn(async (_url: unknown, init?: RequestInit) => {
  const [op, key, value] = JSON.parse(String(init?.body));
  let result: unknown = null;
  if (op === 'SET' && !records.has(key)) { records.set(key, value); result = 'OK'; }
  if (op === 'GET') result = records.get(key) ?? null;
  return Response.json({ result });
}) as unknown as typeof fetch;

describe('durable workflow task contract (isolated REST fixture)', () => {
  beforeEach(() => {
    records.clear(); vi.clearAllMocks();
    vi.stubEnv('UPSTASH_REDIS_REST_URL', 'https://isolated.invalid');
    vi.stubEnv('UPSTASH_REDIS_REST_TOKEN', 'fixture');
  });
  afterEach(() => vi.unstubAllEnvs());
  it('confirms one record and returns the same receipt for three concurrent retries', async () => {
    const first = await createWorkflowTaskRecord(input, 'alice', 'run-1', transport);
    const retries = await Promise.all(Array.from({ length: 3 }, () => createWorkflowTaskRecord(input, 'alice', 'run-1', transport)));
    expect(records.size).toBe(1);
    expect(retries).toEqual([first, first, first]);
    expect(await readWorkflowTask('alice', first.id, transport)).toEqual(first);
    expect(await readWorkflowTask('bob', first.id, transport)).toBeNull();
  });
  it('scopes identical actions to owner and run', async () => {
    const a = await createWorkflowTaskRecord(input, 'alice', 'run-1', transport);
    const b = await createWorkflowTaskRecord(input, 'bob', 'run-1', transport);
    const c = await createWorkflowTaskRecord(input, 'alice', 'run-2', transport);
    expect(new Set([a.id, b.id, c.id]).size).toBe(3);
  });
  it('rejects invalid inputs and missing identity before storage', async () => {
    for (const args of [[{}, 'alice', 'run'], [input, undefined, 'run'], [input, 'alice', undefined]] as const) {
      await expect(createWorkflowTaskRecord(args[0], args[1], args[2], transport)).rejects.toThrow();
    }
    expect(transport).not.toHaveBeenCalled();
  });
  it('never returns fulfilled on storage failure', async () => {
    const actions = await executePreparedActions({ actions: [{ tool: 'create_workflow_task', input, status: 'pending' }], ownerId: 'alice', jobId: 'run', fetchImpl: async () => new Response('unavailable', { status: 503 }) });
    expect(actions[0].status).toBe('failed'); expect(actions[0].data).toBeUndefined();
  });
  it('requires readback after a successful write acknowledgement', async () => {
    let call = 0;
    await expect(createWorkflowTaskRecord(input, 'alice', 'run', async () => Response.json({ result: ++call === 1 ? 'OK' : null }))).rejects.toThrow('readback');
  });
  it('preserves the durable ID through action execution', async () => {
    const actions = await executePreparedActions({ actions: [{ tool: 'create_workflow_task', input, status: 'pending' }], ownerId: 'alice', jobId: 'run', fetchImpl: transport });
    expect(actions[0].status).toBe('fulfilled');
    expect(actions[0].data?.id).toMatch(/^[a-f0-9]{64}$/);
  });
  it('accepts signed session identity and rejects client identity and forged cookies', async () => {
    vi.stubEnv('NEXTAUTH_SECRET', 'isolated-test-secret');
    vi.stubEnv('NODE_ENV', 'test');
    vi.stubEnv('NEXTAUTH_URL', 'http://localhost');
    const token = await encode({ token: { sub: 'alice', provider: 'github' }, secret: 'isolated-test-secret' });
    expect(await workflowTaskOwner(new Request('http://localhost', { headers: { cookie: `next-auth.session-token=${token}` } }))).toBe(JSON.stringify(['github', 'alice']));
    expect(await workflowTaskOwner(new Request('http://localhost', { headers: { 'x-user-id': 'alice', cookie: 'next-auth.session-token=forged' } }))).toBeNull();
  });

});
