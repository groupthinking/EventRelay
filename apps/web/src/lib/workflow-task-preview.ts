import 'server-only';

import { createHash, createHmac, randomUUID, timingSafeEqual } from 'node:crypto';
import type { AgentAction } from './action-lifecycle';

const DOMAIN = 'eventrelay.workflow-task-preview.v1\n';
const MAX_PLAN_BYTES = 512 * 1024;
const hash = (value: string) => createHash('sha256').update(value).digest('hex');

function canonicalJson(value: unknown, depth = 0): string {
  if (depth > 16) throw new Error('Preview input is too deeply nested');
  if (value === null || typeof value === 'string' || typeof value === 'boolean') return JSON.stringify(value);
  if (typeof value === 'number' && Number.isFinite(value)) return JSON.stringify(value);
  if (Array.isArray(value)) return `[${Array.from(value, entry => canonicalJson(entry, depth + 1)).join(',')}]`;
  if (value && typeof value === 'object' &&
      (Object.getPrototypeOf(value) === Object.prototype || Object.getPrototypeOf(value) === null)) {
    return `{${Object.keys(value).sort().map(key => `${JSON.stringify(key)}:${canonicalJson((value as Record<string, unknown>)[key], depth + 1)}`).join(',')}}`;
  }
  throw new Error('Preview input must contain JSON values');
}

function planHash(actions: AgentAction[]): string {
  if (!Array.isArray(actions) || actions.length < 1 || actions.length > 50 ||
      !actions.some(action => action?.tool === 'create_workflow_task')) throw new Error('Invalid task preview');
  const calls = actions.map(action => {
    if (!action || typeof action.tool !== 'string' || !action.tool || action.status !== 'pending' ||
        (action.isError !== undefined && action.isError !== false) ||
        !action.input || typeof action.input !== 'object' || Array.isArray(action.input) ||
        (action.result !== undefined && typeof action.result !== 'string') ||
        Object.keys(action).some(key => !['tool', 'input', 'status', 'result', 'isError'].includes(key))) {
      throw new Error('Only pending error-free actions can be confirmed');
    }
    return canonicalJson({ tool: action.tool, input: action.input });
  });
  if (new Set(calls).size !== calls.length) throw new Error('Duplicate preview actions');
  const plan = `[${calls.join(',')}]`;
  if (Buffer.byteLength(plan) > MAX_PLAN_BYTES) throw new Error('Preview plan is too large');
  return hash(plan);
}

function signingSecret(): string {
  const secret = process.env.NEXTAUTH_SECRET;
  if (!secret?.trim()) throw new Error('Preview signing is unavailable');
  return secret;
}

/** Immutable proof of server preview, not authentication or one-time approval. */
export function issueWorkflowTaskPreview(owner: string, actions: AgentAction[]) {
  if (!owner) throw new Error('Authenticated preview owner is required');
  const jobId = `preview_${randomUUID()}`;
  const payload = Buffer.from(JSON.stringify([1, hash(owner), jobId, planHash(actions), Date.now()])).toString('base64url');
  const signature = createHmac('sha256', signingSecret()).update(DOMAIN + payload).digest('hex');
  return { jobId, confirmationToken: `${payload}.${signature}` };
}

export function verifyWorkflowTaskPreview(token: unknown, owner: string, jobId: string, actions: AgentAction[]): boolean {
  try {
    if (!owner || typeof token !== 'string' || token.length > 1024) return false;
    const match = /^([A-Za-z0-9_-]+)\.([a-f0-9]{64})$/.exec(token);
    if (!match) return false;
    const [, encoded, signature] = match;
    const expected = createHmac('sha256', signingSecret()).update(DOMAIN + encoded).digest();
    if (!timingSafeEqual(Buffer.from(signature, 'hex'), expected)) return false;
    const bytes = Buffer.from(encoded, 'base64url');
    if (bytes.toString('base64url') !== encoded) return false;
    const payload: unknown = JSON.parse(bytes.toString('utf8'));
    return Array.isArray(payload) && payload.length === 5 && payload[0] === 1 &&
      payload[1] === hash(owner) && payload[2] === jobId && /^preview_[a-f0-9-]{36}$/.test(jobId) &&
      payload[3] === planHash(actions) && Number.isSafeInteger(payload[4]) && payload[4] > 0;
  } catch { return false; }
}
