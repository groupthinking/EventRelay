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

async function command(args: string[], fetchImpl: typeof fetch): Promise<unknown> {
  const credentials = resolveUpstashRedisCredentials();
  if (!credentials) throw new Error('Durable task storage is unavailable');
  const response = await fetchImpl(credentials.url, {
    method: 'POST', headers: { Authorization: `Bearer ${credentials.token}`, 'Content-Type': 'application/json' },
    body: JSON.stringify(args), cache: 'no-store', signal: AbortSignal.timeout(10000),
  });
  if (!response.ok) throw new Error('Durable task storage is unavailable');
  const body = await response.json();
  if (body.error || !Object.hasOwn(body, 'result')) throw new Error('Durable task storage is unavailable');
  return body.result;
}

function key(owner: string, id: string) { return `er:workflow-task:v1:${hash(owner)}:${id}`; }

export async function readWorkflowTask(owner: string, id: string, fetchImpl = fetch): Promise<WorkflowTask | null> {
  if (!owner || !/^[a-f0-9]{64}$/.test(id)) throw new Error('Invalid task identity');
  const raw = await command(['GET', key(owner, id)], fetchImpl);
  if (raw === null) return null;
  if (typeof raw !== 'string') throw new Error('Invalid task storage receipt');
  const record = JSON.parse(raw) as WorkflowTask;
  if (record.id !== id || !record.jobId || !record.createdAt) throw new Error('Invalid task storage receipt');
  taskInput({ title: record.title, description: record.description, category: record.category, priority: record.priority });
  return record;
}

export async function createWorkflowTaskRecord(input: Record<string, unknown>, owner: string | undefined, jobId: string | undefined, fetchImpl = fetch): Promise<WorkflowTask> {
  if (!owner || !jobId?.trim() || jobId.length > 200) throw new Error('Authenticated owner and run ID are required');
  const fields = taskInput(input);
  const id = hash(JSON.stringify([owner, jobId, fields]));
  const record: WorkflowTask = { id, ...fields, jobId, createdAt: new Date().toISOString(), commitSha: process.env.VERCEL_GIT_COMMIT_SHA || null };
  // SET NX is atomic across processes. No TTL: retries must not recreate expired tasks.
  const result = await command(['SET', key(owner, id), JSON.stringify(record), 'NX'], fetchImpl);
  if (result !== 'OK' && result !== null) throw new Error('Invalid task storage receipt');
  const persisted = await readWorkflowTask(owner, id, fetchImpl);
  if (!persisted || persisted.jobId !== jobId || JSON.stringify(taskInput({ title: persisted.title, description: persisted.description, category: persisted.category, priority: persisted.priority })) !== JSON.stringify(fields)) throw new Error('Task readback failed');
  return persisted;
}
