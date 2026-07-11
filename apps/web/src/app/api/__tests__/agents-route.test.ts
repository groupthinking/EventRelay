import { describe, it, expect, afterEach, beforeEach, vi } from 'vitest';
import { GET as dispatchGET, POST as dispatchPOST } from '@/app/api/agents/dispatch/route';
import { GET as statusGET } from '@/app/api/agents/status/route';
import { saveEntitlement, resetEntitlementStoreForTests } from '@/lib/billing/entitlement-store';
import { signBillingEmail } from '@/lib/billing/billing-cookie';

const ORIGINAL_BACKEND = process.env.BACKEND_URL;

function setBackend(url: string) {
  process.env.BACKEND_URL = url;
}

function jsonResponse(data: unknown, ok = true, status = 200): Response {
  return {
    ok,
    status,
    json: async () => data,
    text: async () => JSON.stringify(data),
  } as unknown as Response;
}

function dispatchReq(body: unknown, email = 'pro@example.com') {
  return new Request('http://localhost/api/agents/dispatch', {
    method: 'POST',
    headers: {
      'content-type': 'application/json',
      cookie: `er_billing_email=${encodeURIComponent(signBillingEmail(email) as string)}`,
    },
    body: JSON.stringify(body),
  });
}

beforeEach(() => {
  resetEntitlementStoreForTests();
});

afterEach(() => {
  process.env.BACKEND_URL = ORIGINAL_BACKEND ?? '';
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe('GET /api/agents/dispatch (availability probe)', () => {
  it('reports unavailable when no backend is configured', async () => {
    setBackend('');
    const body = await (await dispatchGET()).json();
    expect(body.available).toBe(false);
  });

  it('reports available when BACKEND_URL is set', async () => {
    setBackend('http://backend');
    const body = await (await dispatchGET()).json();
    expect(body.available).toBe(true);
  });
});

describe('POST /api/agents/dispatch', () => {
  it('returns 402 when user is not Pro', async () => {
    setBackend('http://backend');
    const res = await dispatchPOST(dispatchReq({ events: [] }, 'free@example.com'));
    expect(res.status).toBe(402);
    const body = await res.json();
    expect(body.upgradeRequired).toBe(true);
  });

  it('returns 503 when the backend is not configured', async () => {
    setBackend('');
    await saveEntitlement({
      email: 'pro@example.com',
      plan: 'pro',
      status: 'active',
      leadModel: 'grok-4-1-fast',
      updatedAt: new Date().toISOString(),
    });
    const res = await dispatchPOST(dispatchReq({ events: [] }));
    expect(res.status).toBe(503);
  });

  it('proxies executions from the backend on success', async () => {
    setBackend('http://backend');
    await saveEntitlement({
      email: 'pro@example.com',
      plan: 'pro',
      status: 'active',
      leadModel: 'grok-4-1-fast',
      updatedAt: new Date().toISOString(),
    });
    const fetchMock = vi.fn().mockResolvedValue(
      jsonResponse({
        dispatch_id: 'dsp_1',
        executions: [{ agent_id: 'a1', agent_type: 'analyzer', status: 'running', progress: 0 }],
      }),
    );
    vi.stubGlobal('fetch', fetchMock);

    const res = await dispatchPOST(dispatchReq({ events: [{ id: 'e1', title: 'x' }] }));
    const body = await res.json();

    expect(res.status).toBe(200);
    expect(body.executions).toHaveLength(1);
    expect(fetchMock).toHaveBeenCalledWith(
      'http://backend/api/v1/agents/dispatch',
      expect.objectContaining({ method: 'POST' }),
    );
  });

  it('returns 502 when the backend errors', async () => {
    setBackend('http://backend');
    await saveEntitlement({
      email: 'pro@example.com',
      plan: 'pro',
      status: 'active',
      leadModel: 'grok-4-1-fast',
      updatedAt: new Date().toISOString(),
    });
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse('boom', false, 500)));
    const res = await dispatchPOST(dispatchReq({ events: [] }));
    expect(res.status).toBe(502);
  });
});

describe('GET /api/agents/status', () => {
  it('returns 503 when the backend is not configured', async () => {
    setBackend('');
    const res = await statusGET(new Request('http://localhost/api/agents/status?agentId=a1'));
    expect(res.status).toBe(503);
  });

  it('returns 400 when agentId is missing', async () => {
    setBackend('http://backend');
    const res = await statusGET(new Request('http://localhost/api/agents/status'));
    expect(res.status).toBe(400);
  });

  it('proxies the backend status on success', async () => {
    setBackend('http://backend');
    const fetchMock = vi.fn().mockResolvedValue(
      jsonResponse({ agent_id: 'a1', status: 'complete', progress: 100 }),
    );
    vi.stubGlobal('fetch', fetchMock);

    const res = await statusGET(new Request('http://localhost/api/agents/status?agentId=a1'));
    const body = await res.json();

    expect(body.status).toBe('complete');
    expect(fetchMock).toHaveBeenCalledWith(
      'http://backend/api/v1/agents/a1/status',
      expect.anything(),
    );
  });
});
