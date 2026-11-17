import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { encode } from 'next-auth/jwt';
import { NextRequest } from 'next/server';

vi.mock('@/lib/action-agent', async (importOriginal) => ({
  ...await importOriginal<typeof import('@/lib/action-agent')>(),
  runActionAgent: vi.fn(),
}));

import { POST } from '@/app/api/agents/actions/route';
import { runActionAgent } from '@/lib/action-agent';
import type { AgentAction } from '@/lib/action-lifecycle';

const origin = 'https://uvai.example';
const secret = 'isolated-preview-receipt-test-secret';
const action: AgentAction = { tool: 'create_workflow_task', input: {
  title: 'Review captions', description: 'Check the source', category: 'research', priority: 'high',
}, status: 'pending' };
const records = new Map<string, string>();
const transport = vi.fn(async (_url: unknown, init?: RequestInit) => {
  const command = JSON.parse(String(init?.body));
  const [operation] = command;
  const key = command[operation === 'EVAL' ? 3 : 1];
  const value = command[5];
  let result: unknown = null;
  // Model initialized owners with sufficient capacity; this fixture does not execute Lua.
  if (operation === 'EVAL') {
    result = [records.has(key) ? 'existing' : 'stored'];
    if (!records.has(key)) records.set(key, value);
  }
  if (operation === 'GET') result = records.get(key) ?? null;
  return Response.json({ result });
});
let session: string;

async function cookie(subject: string) {
  return `__Secure-next-auth.session-token=${await encode({ token: { provider: 'github', sub: subject }, secret })}`;
}
function request(body: unknown, identity = session) {
  return new NextRequest(`${origin}/api/agents/actions`, { method: 'POST',
    headers: { origin, 'content-type': 'application/json', ...(identity ? { cookie: identity } : {}) },
    body: JSON.stringify(body),
  });
}
async function preview(actions = [action]) {
  vi.mocked(runActionAgent).mockResolvedValue({ provider: 'gemini', actions });
  const response = await POST(request({ mode: 'preview', transcript: 'A sufficiently long source transcript.', jobId: 'untrusted-client-run' }));
  expect(response.status).toBe(200);
  return response.json();
}

describe('server-issued owner-scoped task preview receipt', () => {
  beforeEach(async () => {
    vi.stubEnv('NODE_ENV', 'test'); vi.stubEnv('NEXTAUTH_SECRET', secret); vi.stubEnv('NEXTAUTH_URL', origin);
    vi.stubEnv('UPSTASH_REDIS_REST_URL', 'https://isolated.invalid'); vi.stubEnv('UPSTASH_REDIS_REST_TOKEN', 'fixture');
    vi.stubGlobal('fetch', transport);
    records.clear(); transport.mockClear(); vi.mocked(runActionAgent).mockReset();
    session = await cookie('alice');
  });
  afterEach(() => { vi.unstubAllEnvs(); vi.unstubAllGlobals(); vi.useRealTimers(); });

  it('rejects a fabricated run and arbitrary task without ever storing it', async () => {
    const response = await POST(request({ mode: 'execute', jobId: 'fabricated-run', actions: [action] }));
    expect(records.size).toBe(0);
    expect(response.status).toBe(409);
    expect(transport).not.toHaveBeenCalled();
  });

  it('issues a read-only preview receipt with a server run ID and confirms idempotently', async () => {
    const plan = await preview();
    expect(plan.confirmationToken).toEqual(expect.any(String));
    expect(plan.jobId).toMatch(/^preview_[a-f0-9-]{36}$/);
    expect(plan.jobId).not.toBe('untrusted-client-run');
    expect(transport).not.toHaveBeenCalled();
    const first = await (await POST(request({ mode: 'execute', ...plan }))).json();
    expect(first.actions[0].status).toBe('fulfilled');
    const retries = await Promise.all(Array.from({ length: 3 }, async () => (await POST(request({ mode: 'execute', ...plan }))).json()));
    expect(retries.map(r => r.actions[0].data)).toEqual([first.actions[0].data, first.actions[0].data, first.actions[0].data]);
    expect(records.size).toBe(1);
  });

  it.each(['owner', 'job', 'input', 'tool', 'insert', 'remove', 'order', 'signature'])('rejects %s tampering before any storage', async (tamper) => {
    const second = { ...action, input: { ...action.input, title: 'Review another section' } };
    const plan = await preview([action, second]);
    let identity = session;
    if (tamper === 'owner') identity = await cookie('bob');
    if (tamper === 'job') plan.jobId = 'fabricated-run';
    if (tamper === 'input') plan.actions[0].input.title = 'Injected task';
    if (tamper === 'tool') plan.actions[0].tool = 'save_resource';
    if (tamper === 'insert') plan.actions.push({ ...action, input: { ...action.input, title: 'Inserted task' } });
    if (tamper === 'remove') plan.actions.pop();
    if (tamper === 'order') plan.actions.reverse();
    if (tamper === 'signature') plan.confirmationToken = 'forged';
    const response = await POST(request({ mode: 'execute', ...plan }, identity));
    expect(response.status).toBe(409);
    expect(transport).not.toHaveBeenCalled();
  });

  it('accepts equivalent input key order without changing task identity', async () => {
    const plan = await preview();
    plan.actions[0].input = Object.fromEntries(Object.entries(plan.actions[0].input).reverse());
    const response = await POST(request({ mode: 'execute', ...plan }));
    expect(response.status).toBe(200);
    expect((await response.json()).actions[0].status).toBe('fulfilled');
  });

  it('preserves the same proof and task identity for delayed retries', async () => {
    const plan = await preview();
    const first = await (await POST(request({ mode: 'execute', ...plan }))).json();
    vi.useFakeTimers({ toFake: ['Date'] });
    vi.setSystemTime(Date.now() + 24 * 60 * 60 * 1000);
    session = await cookie('alice');
    const retry = await (await POST(request({ mode: 'execute', ...plan }))).json();
    expect(retry.actions[0].data).toEqual(first.actions[0].data);
    expect(records.size).toBe(1);
  });

  it('keeps anonymous preview read-only without an executable receipt', async () => {
    vi.mocked(runActionAgent).mockResolvedValue({ provider: 'gemini', actions: [action] });
    const response = await POST(request({ transcript: 'A sufficiently long source transcript.' }, ''));
    expect(response.status).toBe(200);
    expect((await response.json()).confirmationToken).toBeUndefined();
    expect(transport).not.toHaveBeenCalled();
  });

  it.each([null, [], 'text', 1, true])('rejects non-object request bodies %#', async body => {
    expect((await POST(request(body))).status).toBe(400);
    expect(runActionAgent).not.toHaveBeenCalled();
    expect(transport).not.toHaveBeenCalled();
  });

  it('returns a client error for deeply nested JSON instead of throwing during deduplication', async () => {
    const input = '{"nested":'.repeat(8000) + '0' + '}'.repeat(8000);
    const body = `{"mode":"execute","jobId":"fabricated-run","actions":[{"tool":"create_workflow_task","status":"pending","input":${input}}]}`;
    const candidate = new NextRequest(`${origin}/api/agents/actions`, { method: 'POST',
      headers: { origin, 'content-type': 'application/json', cookie: session }, body });
    expect((await POST(candidate)).status).toBe(400);
    expect(transport).not.toHaveBeenCalled();
  });

  it.each([
    { actions: [action, { ...action, tool: 'unknown-tool' }] },
    { actions: [action, { ...action, input: { title: 'Failed' }, status: 'failed' }] },
    { actions: [action, action] },
  ])('does not issue executable receipts for invalid model plans %#', async ({ actions }) => {
    vi.mocked(runActionAgent).mockResolvedValue({ provider: 'gemini', actions: actions as AgentAction[] });
    const response = await POST(request({ transcript: 'A sufficiently long source transcript.' }));
    expect(response.status).toBe(502);
    expect((await response.json()).confirmationToken).toBeUndefined();
    expect(transport).not.toHaveBeenCalled();
  });
});
