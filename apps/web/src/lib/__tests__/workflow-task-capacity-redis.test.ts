import { afterAll, afterEach, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';
import { spawn, spawnSync, type ChildProcess } from 'node:child_process';
import { mkdtemp, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { createClient } from 'redis';
import { createWorkflowTaskRecord, readWorkflowTask, workflowTaskQuotaKey, WorkflowTaskCapacityError } from '../workflow-task-store';
import { executePreparedActions } from '../action-agent';

const fields = (index = 0) => ({ title: `Task ${index}`, description: 'Inspect source', category: 'research', priority: 'high' });

// Opt-in runs the actual production Lua in a disposable Unix-socket server.
// No configured Redis endpoint, real bearer credential, or TCP listener is used.
describe.runIf(process.env.WORKFLOW_TASK_REDIS_TESTS === '1')('atomic workflow task owner capacity (isolated Redis)', () => {
  let server: ChildProcess;
  let directory: string;
  let redis: ReturnType<typeof createClient>;
  const transport: typeof fetch = async (_url, options) => {
    const args = JSON.parse(String(options?.body)) as string[];
    const result = await redis.sendCommand(args);
    return Response.json({ result });
  };

  beforeAll(async () => {
    const binary = [process.env.WORKFLOW_TASK_REDIS_BINARY, 'redis-server', 'redis6-server']
      .find(name => name && spawnSync(name, ['--version']).status === 0);
    if (!binary) throw new Error('Workflow capacity integration tests require a local Redis binary; no external store is used.');
    directory = await mkdtemp(join(tmpdir(), 'workflow-quota-'));
    const socketPath = join(directory, 'redis.sock');
    server = spawn(binary, ['--port', '0', '--unixsocket', socketPath, '--unixsocketperm', '700', '--save', '', '--appendonly', 'no'], {
      cwd: directory, env: { PATH: process.env.PATH, NODE_ENV: 'test' }, stdio: ['ignore', 'pipe', 'pipe'],
    });
    await new Promise<void>((resolve, reject) => {
      let output = '';
      const capture = (data: Buffer) => { output = (output + data.toString()).slice(-4000); };
      server.stdout!.on('data', capture);
      server.stderr!.on('data', capture);
      const timeout = setTimeout(() => reject(new Error(`Isolated Redis readiness timeout: ${output}`)), 5000);
      server.once('error', error => { clearTimeout(timeout); reject(error); });
      server.once('exit', code => { clearTimeout(timeout); reject(new Error(`Isolated Redis exited: ${code}: ${output}`)); });
      server.stdout!.on('data', (data: Buffer) => {
        if (/ready to accept connections/i.test(data.toString())) { clearTimeout(timeout); resolve(); }
      });
    });
    redis = createClient({ socket: { path: socketPath, reconnectStrategy: false } });
    await redis.connect();
  });
  afterAll(async () => {
    if (redis?.isOpen) redis.destroy();
    if (server && server.exitCode === null) await new Promise<void>(resolve => { server.once('exit', () => resolve()); server.kill(); });
    if (directory) await rm(directory, { recursive: true, force: true });
  });
  beforeEach(async () => {
    await redis.flushDb();
    vi.stubEnv('UPSTASH_REDIS_REST_URL', 'https://isolated.invalid');
    vi.stubEnv('UPSTASH_REDIS_REST_TOKEN', 'fixture');
    vi.stubEnv('WORKFLOW_TASKS_PER_OWNER_LIMIT', '3');
  });
  afterEach(() => vi.unstubAllEnvs());

  it('admits at most three new IDs from fifty concurrent writers', async () => {
    await redis.set(workflowTaskQuotaKey('alice'), 'v1:0');
    const results = await Promise.allSettled(Array.from({ length: 50 }, (_, index) => createWorkflowTaskRecord(fields(index), 'alice', 'run', transport)));
    expect(results.filter(result => result.status === 'fulfilled')).toHaveLength(3);
    const rejected = results.filter(result => result.status === 'rejected') as PromiseRejectedResult[];
    expect(rejected).toHaveLength(47);
    expect(rejected.every(result => result.reason instanceof WorkflowTaskCapacityError)).toBe(true);
    expect(await redis.get(workflowTaskQuotaKey('alice'))).toBe('v1:3');
    expect(await redis.keys('er:workflow-task:v1:*')).toHaveLength(3);
    expect(await redis.pTTL(workflowTaskQuotaKey('alice'))).toBe(-1);
  });

  it('charges one slot for concurrent identical retries and keeps records permanent', async () => {
    await redis.set(workflowTaskQuotaKey('alice'), 'v1:0');
    const results = await Promise.all(Array.from({ length: 30 }, () => createWorkflowTaskRecord(fields(), 'alice', 'run', transport)));
    expect(results.every(result => JSON.stringify(result) === JSON.stringify(results[0]))).toBe(true);
    expect(await redis.get(workflowTaskQuotaKey('alice'))).toBe('v1:1');
    const keys = await redis.keys('er:workflow-task:v1:*');
    expect(keys).toHaveLength(1);
    expect(await redis.pTTL(keys[0])).toBe(-1);
  });

  it.each([undefined, '', 'v1:-1', 'v1:1.5', 'v1:01', 'v1:abc', 'v2:0', 'v1:9007199254740992'])('refuses unknown or malformed owner metadata %s without repairing it', async metadata => {
    const key = workflowTaskQuotaKey('alice');
    if (metadata !== undefined) await redis.set(key, metadata);
    await expect(createWorkflowTaskRecord(fields(), 'alice', 'run', transport)).rejects.toBeInstanceOf(WorkflowTaskCapacityError);
    expect(await redis.get(key)).toBe(metadata ?? null);
    expect(await redis.keys('er:workflow-task:v1:*')).toEqual([]);
  });

  it.each(['', '0', '-1', '1.5', 'NaN', 'Infinity', '01', '9007199254740992'])('requires an explicit safe positive integer limit: %s', async limit => {
    vi.stubEnv('WORKFLOW_TASKS_PER_OWNER_LIMIT', limit);
    await redis.set(workflowTaskQuotaKey('alice'), 'v1:0');
    await expect(createWorkflowTaskRecord(fields(), 'alice', 'run', transport)).rejects.toBeInstanceOf(WorkflowTaskCapacityError);
    expect(await redis.get(workflowTaskQuotaKey('alice'))).toBe('v1:0');
    expect(await redis.keys('er:workflow-task:v1:*')).toEqual([]);
  });

  it('refuses expiring or wrong-type quota state', async () => {
    const key = workflowTaskQuotaKey('alice');
    await redis.set(key, 'v1:0', { PX: 60_000 });
    await expect(createWorkflowTaskRecord(fields(), 'alice', 'run', transport)).rejects.toBeInstanceOf(WorkflowTaskCapacityError);
    expect(await redis.pTTL(key)).toBeGreaterThan(0);
    await redis.del(key);
    await redis.sAdd(key, 'unexpected');
    await expect(createWorkflowTaskRecord(fields(), 'alice', 'run', transport)).rejects.toBeInstanceOf(WorkflowTaskCapacityError);
    expect(await redis.sMembers(key)).toEqual(['unexpected']);
  });

  it('preserves old retries and reads when quota is full, missing, invalid or lowered', async () => {
    const key = workflowTaskQuotaKey('alice');
    await redis.set(key, 'v1:0');
    const first = await createWorkflowTaskRecord(fields(), 'alice', 'run', transport);
    const recordKey = (await redis.keys('er:workflow-task:v1:*'))[0];
    const original = await redis.get(recordKey);
    for (const [metadata, limit] of [['v1:3', '3'], ['v1:100', '1'], ['invalid', '3'], [undefined, '3'], ['v1:1', '']] as const) {
      if (metadata === undefined) await redis.del(key); else await redis.set(key, metadata);
      vi.stubEnv('WORKFLOW_TASKS_PER_OWNER_LIMIT', limit);
      expect(await createWorkflowTaskRecord(fields(), 'alice', 'run', transport)).toEqual(first);
      expect(await readWorkflowTask('alice', first.id, transport)).toEqual(first);
      expect(await redis.get(recordKey)).toBe(original);
      expect(await redis.get(key)).toBe(metadata ?? null);
      await expect(createWorkflowTaskRecord(fields(1), 'alice', 'run', transport)).rejects.toBeInstanceOf(WorkflowTaskCapacityError);
    }
  });

  it('counts existing authoritative usage before admitting new records', async () => {
    const key = workflowTaskQuotaKey('alice');
    await redis.set(key, 'v1:2');
    await createWorkflowTaskRecord(fields(), 'alice', 'run', transport);
    await expect(createWorkflowTaskRecord(fields(1), 'alice', 'run', transport)).rejects.toBeInstanceOf(WorkflowTaskCapacityError);
    expect(await redis.get(key)).toBe('v1:3');
    expect(await redis.keys('er:workflow-task:v1:*')).toHaveLength(1);
  });

  it('preserves existing retries with expiring or wrong-type quota metadata', async () => {
    const key = workflowTaskQuotaKey('alice');
    await redis.set(key, 'v1:0');
    const first = await createWorkflowTaskRecord(fields(), 'alice', 'run', transport);
    await redis.set(key, 'v1:1', { PX: 60_000 });
    expect(await createWorkflowTaskRecord(fields(), 'alice', 'run', transport)).toEqual(first);
    expect(await redis.pTTL(key)).toBeGreaterThan(0);
    await redis.del(key);
    await redis.sAdd(key, 'unexpected');
    expect(await createWorkflowTaskRecord(fields(), 'alice', 'run', transport)).toEqual(first);
    expect(await redis.sMembers(key)).toEqual(['unexpected']);
  });

  it('keeps owner capacities independent', async () => {
    vi.stubEnv('WORKFLOW_TASKS_PER_OWNER_LIMIT', '1');
    await redis.set(workflowTaskQuotaKey('alice'), 'v1:0');
    await redis.set(workflowTaskQuotaKey('bob'), 'v1:0');
    await createWorkflowTaskRecord(fields(), 'alice', 'run', transport);
    await expect(createWorkflowTaskRecord(fields(1), 'alice', 'run', transport)).rejects.toBeInstanceOf(WorkflowTaskCapacityError);
    await createWorkflowTaskRecord(fields(), 'bob', 'run', transport);
    expect(await redis.get(workflowTaskQuotaKey('alice'))).toBe('v1:1');
    expect(await redis.get(workflowTaskQuotaKey('bob'))).toBe('v1:1');
  });

  it('does not consume another slot after a committed write loses its acknowledgement', async () => {
    const key = workflowTaskQuotaKey('alice');
    await redis.set(key, 'v1:0');
    await expect(createWorkflowTaskRecord(fields(), 'alice', 'run', async (url, options) => {
      await transport(url, options); throw new Error('Lost fixture response');
    })).rejects.toThrow();
    const original = await redis.get((await redis.keys('er:workflow-task:v1:*'))[0]);
    const retry = await createWorkflowTaskRecord(fields(), 'alice', 'run', transport);
    expect(JSON.stringify(retry)).toBe(original);
    expect(await redis.get(key)).toBe('v1:1');
  });

  it('continues existing retries later in a batch after a new ID hits capacity', async () => {
    vi.stubEnv('WORKFLOW_TASKS_PER_OWNER_LIMIT', '1');
    await redis.set(workflowTaskQuotaKey('alice'), 'v1:0');
    const existing = await createWorkflowTaskRecord(fields(), 'alice', 'run', transport);
    const actions = await executePreparedActions({ ownerId: 'alice', jobId: 'run', fetchImpl: transport,
      actions: [1, 0].map(index => ({ tool: 'create_workflow_task', input: fields(index), status: 'pending' })) });
    expect(actions.map(action => action.status)).toEqual(['failed', 'fulfilled']);
    expect(actions[0].data).toBeUndefined();
    expect(actions[1].data?.id).toBe(existing.id);
  });

  it('preserves exact integer counts at the safe-integer boundary', async () => {
    vi.stubEnv('WORKFLOW_TASKS_PER_OWNER_LIMIT', '9007199254740991');
    await redis.set(workflowTaskQuotaKey('alice'), 'v1:9007199254740990');
    await createWorkflowTaskRecord(fields(), 'alice', 'run', transport);
    expect(await redis.get(workflowTaskQuotaKey('alice'))).toBe('v1:9007199254740991');
    await expect(createWorkflowTaskRecord(fields(1), 'alice', 'run', transport)).rejects.toBeInstanceOf(WorkflowTaskCapacityError);
  });
});
