import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { encode } from 'next-auth/jwt';
import { NextRequest } from 'next/server';

import { POST } from '@/app/api/agents/actions/route';
import { issueWorkflowTaskPreview } from '@/lib/workflow-task-preview';
import type { AgentAction } from '@/lib/action-lifecycle';

const endpoint = 'https://uvai.example/api/agents/actions';
const origin = 'https://uvai.example';
const secret = 'isolated-action-origin-test-secret';
const input = { title: 'Review captions', description: 'Check the source', category: 'research', priority: 'high' };
const payload = { mode: 'execute', jobId: 'run-1', actions: [{ tool: 'create_workflow_task', input, status: 'pending' }] };
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

function request(headers: Record<string, string>, body = JSON.stringify(payload)) {
  return new NextRequest(endpoint, { method: 'POST', headers, body });
}

describe('workflow task write origin protection (real session and isolated REST fixture)', () => {
  beforeEach(async () => {
    vi.stubEnv('NODE_ENV', 'test');
    vi.stubEnv('NEXTAUTH_SECRET', secret);
    vi.stubEnv('NEXTAUTH_URL', origin);
    vi.stubEnv('UPSTASH_REDIS_REST_URL', 'https://isolated.invalid');
    vi.stubEnv('UPSTASH_REDIS_REST_TOKEN', 'fixture');
    vi.stubGlobal('fetch', transport);
    records.clear();
    transport.mockClear();
    const token = await encode({ token: { provider: 'github', sub: 'alice' }, secret });
    session = `__Secure-next-auth.session-token=${token}`;
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.unstubAllEnvs();
  });

  it('rejects a same-site sibling text/plain form before any task is written', async () => {
    // A text/plain form can serialize a JSON-shaped field name/value as
    // { ...,"padding":"="}\r\n. request.json() accepts those bytes.
    const response = await POST(request({
      origin: 'https://untrusted.uvai.example',
      'sec-fetch-site': 'same-site',
      'content-type': 'text/plain',
      cookie: session,
    }, `${JSON.stringify({ ...payload, padding: '=' })}\r\n`));
    expect(records.size).toBe(0);
    expect(response.status).toBe(403);
    expect(transport).not.toHaveBeenCalled();
  });

  it.each([
    undefined, '', 'null', 'malformed', 'https://untrusted.uvai.example', 'https://uvai.example.attacker.test',
    'https://uvai.example/path', 'https://uvai.example/', 'http://uvai.example', 'https://uvai.example:444',
    'https://user@uvai.example', 'https://uvai.example https://attacker.example',
  ])('rejects cookie-authenticated writes from origin %s', async (untrustedOrigin) => {
    const headers: Record<string, string> = { 'content-type': 'application/json', cookie: session };
    if (untrustedOrigin !== undefined) headers.origin = untrustedOrigin;
    const response = await POST(request(headers));
    expect(response.status).toBe(403);
    expect(transport).not.toHaveBeenCalled();
  });

  it('rejects cross-site fetch metadata even with a matching Origin', async () => {
    const response = await POST(request({ origin, 'sec-fetch-site': 'cross-site', 'content-type': 'application/json', cookie: session }));
    expect(response.status).toBe(403);
    expect(transport).not.toHaveBeenCalled();
  });

  it('does not trust client-supplied forwarded hosts', async () => {
    const response = await POST(request({
      origin: 'https://attacker.example', 'x-forwarded-host': 'attacker.example',
      'x-forwarded-proto': 'https', 'content-type': 'application/json', cookie: session,
    }));
    expect(response.status).toBe(403);
    expect(transport).not.toHaveBeenCalled();
  });

  it.each(['text/plain', 'application/x-www-form-urlencoded', 'multipart/form-data', 'application/jsonp'])('requires JSON content type instead of %s', async (contentType) => {
    const response = await POST(request({ origin, 'content-type': contentType, cookie: session }));
    expect(response.status).toBe(415);
    expect(transport).not.toHaveBeenCalled();
  });

  it('rejects missing content type', async () => {
    const candidate = request({ origin, cookie: session });
    candidate.headers.delete('content-type');
    expect((await POST(candidate)).status).toBe(415);
    expect(transport).not.toHaveBeenCalled();
  });

  it('accepts same-origin JSON cookie authentication and preserves retry receipts', async () => {
    const headers = { origin, 'sec-fetch-site': 'same-origin', 'content-type': 'Application/JSON; charset=utf-8', cookie: session };
    const confirmed = JSON.stringify({ ...payload, ...issueWorkflowTaskPreview(JSON.stringify(['github', 'alice']), payload.actions as AgentAction[]) });
    const response = await POST(request(headers, confirmed));
    const body = await response.json();
    expect(response.status).toBe(200);
    expect(body.actions[0].status).toBe('fulfilled');
    expect(body.actions[0].data.id).toMatch(/^[a-f0-9]{64}$/);
    const retry = await (await POST(request(headers, confirmed))).json();
    expect(retry.actions[0].data).toEqual(body.actions[0].data);
    expect(records.size).toBe(1);
  });

  it('preserves explicit bearer authentication without cookies or a browser Origin', async () => {
    const token = await encode({ token: { provider: 'github', sub: 'automation' }, secret });
    const confirmed = JSON.stringify({ ...payload, ...issueWorkflowTaskPreview(JSON.stringify(['github', 'automation']), payload.actions as AgentAction[]) });
    const response = await POST(request({ 'content-type': 'application/json', authorization: `Bearer ${token}` }, confirmed));
    expect(response.status).toBe(200);
    expect((await response.json()).actions[0].status).toBe('fulfilled');
    expect(records.size).toBe(1);
  });

  it('still requires a verified bearer identity', async () => {
    const response = await POST(request({ 'content-type': 'application/json', authorization: 'Bearer forged' }));
    expect(response.status).toBe(401);
    expect(transport).not.toHaveBeenCalled();
  });

  it('cannot bypass the missing-Origin cookie check by adding a bearer header', async () => {
    const response = await POST(request({ 'content-type': 'application/json', cookie: session, authorization: 'Bearer forged' }));
    expect(response.status).toBe(403);
    expect(transport).not.toHaveBeenCalled();
  });

  it('does not treat an empty Cookie header as absent for bearer authentication', async () => {
    const token = await encode({ token: { provider: 'github', sub: 'automation' }, secret });
    const response = await POST(request({ 'content-type': 'application/json', cookie: '', authorization: `Bearer ${token}` }));
    expect(response.status).toBe(403);
    expect(transport).not.toHaveBeenCalled();
  });

  it('cannot use bearer authentication to permit an untrusted browser Origin', async () => {
    const token = await encode({ token: { provider: 'github', sub: 'automation' }, secret });
    const response = await POST(request({ origin: 'https://attacker.example', 'content-type': 'application/json', authorization: `Bearer ${token}` }));
    expect(response.status).toBe(403);
    expect(transport).not.toHaveBeenCalled();
  });
});
