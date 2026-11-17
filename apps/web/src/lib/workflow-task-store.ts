import { createHash } from 'node:crypto';
import { resolveUpstashRedisCredentials } from './billing/redis-credentials';
import { getNextAuthJwtFromRequest } from './auth-jwt';

export async function workflowTaskOwner(request: Request): Promise<string | null> {
  if (!process.env.NEXTAUTH_SECRET) return null;
  try {
    const token = await getNextAuthJwtFromRequest(request, process.env.NEXTAUTH_SECRET);
    return typeof token?.sub === 'string' && token.sub &&
      typeof token.provider === 'string' && token.provider
      ? JSON.stringify([token.provider, token.sub]) : null;
  } catch { return null; }
}

const hash = (value: string) => createHash('sha256').update(value).digest('hex');
export type WorkflowTask = {
  id: string; title: string; description: string; category: string; priority: string;
  jobId: string; createdAt: string; commitSha: string | null;
};

export class WorkflowTaskStorageError extends Error {
  constructor(message = 'Durable task storage is unavailable') {
    super(message);
    this.name = 'WorkflowTaskStorageError';
  }
}

export class WorkflowTaskCapacityError extends Error {
  constructor(readonly reason: string) {
    super(reason === 'capacity_full' ? 'Workflow task capacity is full' : 'Workflow task capacity is not configured and initialized');
    this.name = 'WorkflowTaskCapacityError';
  }
}

// No automatic zero initialization: legacy tasks have no authoritative counter.
// Existing retries precede all quota checks. Reserve before SET because Redis
// scripts serialize concurrent callers but do not roll back earlier writes.
export const COMMIT_WORKFLOW_TASK_SCRIPT = `
if redis.call('EXISTS', KEYS[1]) == 1 then return { 'existing' } end
local function integer(value)
  if type(value) ~= 'string' or not string.match(value, '^%d+$') then return nil end
  local number = tonumber(value)
  if not number or number < 0 or number > 9007199254740991 or math.floor(number) ~= number then return nil end
  if string.format('%.0f', number) ~= value then return nil end
  return number
end
local limit = integer(ARGV[2])
if not limit or limit < 1 then return { 'capacity_uninitialized' } end
local metadata = redis.pcall('GET', KEYS[2])
if type(metadata) ~= 'string' or redis.call('PTTL', KEYS[2]) ~= -1 then return { 'capacity_uninitialized' } end
local count = integer(string.match(metadata, '^v1:(%d+)$'))
if not count then return { 'capacity_uninitialized' } end
if count >= limit then return { 'capacity_full' } end
redis.call('SET', KEYS[2], 'v1:' .. string.format('%.0f', count + 1))
redis.call('SET', KEYS[1], ARGV[1], 'NX')
return { 'stored' }
`;

function taskInput(input: Record<string, unknown>) {
  const { title, description, category, priority } = input;
  if (typeof title !== 'string' || !title.trim() || title.length > 300 ||
      typeof description !== 'string' || !description.trim() || description.length > 10000 ||
      typeof category !== 'string' || !['setup','build','deploy','learn','research','configure'].includes(category) ||
      typeof priority !== 'string' || !['high','medium','low'].includes(priority) ||
      Object.keys(input).some(key => !['title','description','category','priority'].includes(key))) {
    throw new Error('Invalid workflow task input');
  }
  return { title, description, category, priority };
}

async function command(args: string[], fetchImpl: typeof fetch, deadlineAt?: number): Promise<unknown> {
  try {
    const credentials = resolveUpstashRedisCredentials();
    if (!credentials) throw new Error('Missing storage configuration');
    const endpoint = new URL(credentials.url);
    if (endpoint.protocol !== 'https:' || endpoint.username || endpoint.password) throw new Error('Unsafe storage endpoint');
    // One deadline spans atomic writes and mandatory readback; each request also has a 10-second ceiling.
    const remainingMs = deadlineAt === undefined ? 10_000 : Math.min(10_000, deadlineAt - Date.now());
    if (remainingMs <= 0) throw new Error('Task storage deadline exceeded');
    const response = await fetchImpl(credentials.url, {
      method: 'POST', headers: { Authorization: `Bearer ${credentials.token}`, 'Content-Type': 'application/json' },
      body: JSON.stringify(args), cache: 'no-store', redirect: 'error', signal: AbortSignal.timeout(remainingMs),
    });
    if (!response.ok) throw new Error('Storage request failed');
    const body = await response.json();
    if (body.error || !Object.hasOwn(body, 'result')) throw new Error('Invalid storage response');
    return body.result;
  } catch { throw new WorkflowTaskStorageError(); }
}

function key(owner: string, id: string) { return `er:workflow-task:v1:${hash(owner)}:${id}`; }
export function workflowTaskQuotaKey(owner: string) { return `er:workflow-task-quota:v1:${hash(owner)}`; }

export async function readWorkflowTask(owner: string, id: string, fetchImpl = fetch, deadlineAt?: number): Promise<WorkflowTask | null> {
  if (!owner || !/^[a-f0-9]{64}$/.test(id)) throw new Error('Invalid task identity');
  const raw = await command(['GET', key(owner, id)], fetchImpl, deadlineAt);
  if (raw === null) return null;
  try {
    if (typeof raw !== 'string') throw new Error('Invalid task storage receipt');
    const record = JSON.parse(raw) as WorkflowTask;
    if (record.id !== id || !record.jobId || !record.createdAt) throw new Error('Invalid task storage receipt');
    taskInput({ title: record.title, description: record.description, category: record.category, priority: record.priority });
    return record;
  } catch { throw new WorkflowTaskStorageError('Invalid task storage receipt'); }
}

export async function createWorkflowTaskRecord(input: Record<string, unknown>, owner: string | undefined, jobId: string | undefined, fetchImpl = fetch, deadlineAt?: number): Promise<WorkflowTask> {
  if (!owner || !jobId?.trim() || jobId.length > 200) throw new Error('Authenticated owner and run ID are required');
  const fields = taskInput(input);
  const id = hash(JSON.stringify([owner, jobId, fields]));
  const record: WorkflowTask = { id, ...fields, jobId, createdAt: new Date().toISOString(), commitSha: process.env.VERCEL_GIT_COMMIT_SHA || null };
  // Quota reservation and SET NX share one atomic server-side operation. No TTL.
  const result = await command(['EVAL', COMMIT_WORKFLOW_TASK_SCRIPT, '2', key(owner, id), workflowTaskQuotaKey(owner), JSON.stringify(record), process.env.WORKFLOW_TASKS_PER_OWNER_LIMIT?.trim() ?? ''], fetchImpl, deadlineAt);
  if (!Array.isArray(result) || result.length !== 1) throw new WorkflowTaskStorageError('Invalid task storage receipt');
  if (result[0] === 'capacity_full' || result[0] === 'capacity_uninitialized') throw new WorkflowTaskCapacityError(result[0]);
  if (result[0] !== 'stored' && result[0] !== 'existing') throw new WorkflowTaskStorageError('Invalid task storage receipt');
  const persisted = await readWorkflowTask(owner, id, fetchImpl, deadlineAt);
  if (!persisted || persisted.jobId !== jobId || JSON.stringify(taskInput({ title: persisted.title, description: persisted.description, category: persisted.category, priority: persisted.priority })) !== JSON.stringify(fields)) throw new WorkflowTaskStorageError('Task readback failed');
  return persisted;
}
