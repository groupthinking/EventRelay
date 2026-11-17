import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { createWorkflowTaskRecord } from '../workflow-task-store';

const input = { title: 'Review source', description: 'Inspect evidence', category: 'research', priority: 'high' };
const records = new Map<string, string>();
const transport = vi.fn(async (_url: unknown, init?: RequestInit) => {
  const [operation, key, value] = JSON.parse(String(init?.body));
  let result: unknown = null;
  if (operation === 'SET' && !records.has(key)) { records.set(key, value); result = 'OK'; }
  if (operation === 'GET') result = records.get(key) ?? null;
  if (operation === 'EVAL') result = ['capacity_uninitialized'];
  return Response.json({ result });
});

describe('workflow task capacity fails closed before owner initialization', () => {
  beforeEach(() => {
    vi.stubEnv('UPSTASH_REDIS_REST_URL', 'https://isolated.invalid');
    vi.stubEnv('UPSTASH_REDIS_REST_TOKEN', 'fixture');
    vi.stubEnv('WORKFLOW_TASKS_PER_OWNER_LIMIT', '2');
    records.clear(); transport.mockClear();
  });
  afterEach(() => vi.unstubAllEnvs());

  it('does not invent a zero owner count when legacy capacity is unknown', async () => {
    await expect(createWorkflowTaskRecord(input, 'alice', 'run', transport)).rejects.toThrow(/capacity/i);
    expect(records.size).toBe(0);
  });
});
