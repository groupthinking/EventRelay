import { afterEach, describe, expect, it, vi } from 'vitest';
import { GET, POST } from '@/app/api/realtime/session/route';

const ORIGINAL_OPENAI_KEY = process.env.OPENAI_API_KEY;
const ORIGINAL_SAFETY_IDENTIFIER = process.env.OPENAI_SAFETY_IDENTIFIER;

function sdpRequest(body: string) {
  return new Request('http://localhost/api/realtime/session', {
    method: 'POST',
    headers: { 'content-type': 'application/sdp' },
    body,
  });
}

function upstreamResponse(body: unknown, status = 200, headers: HeadersInit = { 'content-type': 'application/json' }) {
  return new Response(typeof body === 'string' ? body : JSON.stringify(body), {
    status,
    headers,
  });
}

afterEach(() => {
  if (ORIGINAL_OPENAI_KEY === undefined) delete process.env.OPENAI_API_KEY;
  else process.env.OPENAI_API_KEY = ORIGINAL_OPENAI_KEY;

  if (ORIGINAL_SAFETY_IDENTIFIER === undefined) delete process.env.OPENAI_SAFETY_IDENTIFIER;
  else process.env.OPENAI_SAFETY_IDENTIFIER = ORIGINAL_SAFETY_IDENTIFIER;

  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe('/api/realtime/session', () => {
  it('returns 500 when the OpenAI key is not configured', async () => {
    delete process.env.OPENAI_API_KEY;

    const res = await GET();
    const body = await res.json();

    expect(res.status).toBe(500);
    expect(body.error).toMatch(/OPENAI_API_KEY/);
    expect(body.code).toBe('realtime_not_configured');
  });

  it('returns 500 with a matching code when POST finds no OpenAI key', async () => {
    delete process.env.OPENAI_API_KEY;

    const res = await POST(sdpRequest('v=0\no=- 1 1 IN IP4 127.0.0.1'));
    const body = await res.json();

    expect(res.status).toBe(500);
    expect(body.code).toBe('realtime_not_configured');
  });

  it('mints a browser client secret with the GA Realtime session shape', async () => {
    process.env.OPENAI_API_KEY = 'test-key';
    process.env.OPENAI_SAFETY_IDENTIFIER = 'hashed-user';

    const fetchMock = vi.fn().mockResolvedValue(upstreamResponse({ value: 'ek_test', expires_at: 123 }));
    vi.stubGlobal('fetch', fetchMock);

    const res = await GET();
    const body = await res.json();
    const [, init] = fetchMock.mock.calls[0];
    const payload = JSON.parse(init.body as string);

    expect(res.status).toBe(200);
    expect(body.value).toBe('ek_test');
    expect(fetchMock).toHaveBeenCalledWith(
      'https://api.openai.com/v1/realtime/client_secrets',
      expect.objectContaining({ method: 'POST' }),
    );
    expect(init.headers).toMatchObject({
      Authorization: 'Bearer test-key',
      'Content-Type': 'application/json',
      'OpenAI-Safety-Identifier': 'hashed-user',
    });
    expect(payload.session).toMatchObject({
      type: 'realtime',
      model: 'gpt-realtime-2',
      audio: { output: { voice: 'marin' } },
    });
    expect(payload.session.tools[0].name).toBe('check_calendar');
  });

  it('rejects malformed SDP offers', async () => {
    process.env.OPENAI_API_KEY = 'test-key';

    const res = await POST(sdpRequest('not an sdp offer'));
    const body = await res.json();

    expect(res.status).toBe(400);
    expect(body.error).toMatch(/SDP offer/);
    expect(body.code).toBe('invalid_sdp_offer');
  });

  it('keeps the server-side SDP exchange available as a fallback', async () => {
    process.env.OPENAI_API_KEY = 'test-key';

    const fetchMock = vi.fn().mockResolvedValue(upstreamResponse('v=0\nanswer', 201, { 'content-type': 'application/sdp' }));
    vi.stubGlobal('fetch', fetchMock);

    const res = await POST(sdpRequest('v=0\no=- 1 1 IN IP4 127.0.0.1'));
    const [, init] = fetchMock.mock.calls[0];

    expect(res.status).toBe(201);
    expect(await res.text()).toContain('v=0');
    expect(fetchMock).toHaveBeenCalledWith(
      'https://api.openai.com/v1/realtime/calls',
      expect.objectContaining({ method: 'POST' }),
    );
    expect(init.headers).toMatchObject({ Authorization: 'Bearer test-key' });
    expect(init.body).toBeInstanceOf(FormData);
  });
});

/**
 * OpenAI error bodies echo org/project identifiers, quota state and — on a 401 —
 * a partial API key. None of that may reach the browser.
 */
describe('/api/realtime/session upstream error leakage', () => {
  const LEAKY_OPENAI_ERROR = JSON.stringify({
    error: {
      message:
        'Incorrect API key provided: sk-proj-****ABCD. You can find your API key at https://platform.openai.com/account/api-keys.',
      type: 'invalid_request_error',
      param: null,
      code: 'invalid_api_key',
    },
    organization: 'org-eventrelay-prod',
    project: 'proj_abc123',
  });

  const LEAKED_TOKENS = [
    'sk-proj',
    'invalid_api_key',
    'platform.openai.com',
    'org-eventrelay-prod',
    'proj_abc123',
  ];

  it('does not forward the OpenAI body when minting a client secret', async () => {
    process.env.OPENAI_API_KEY = 'test-key';
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {});
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(upstreamResponse(LEAKY_OPENAI_ERROR, 401)));

    const res = await GET();
    const raw = await res.text();

    // Upstream status is deliberately not mirrored — it is itself a signal
    // about the server's OpenAI account state.
    expect(res.status).toBe(502);
    expect(JSON.parse(raw)).toEqual({
      error: 'OpenAI Realtime client secret creation failed.',
      code: 'realtime_client_secret_failed',
    });
    for (const token of LEAKED_TOKENS) {
      expect(raw).not.toContain(token);
    }

    // ...but operators still get the full body server-side.
    expect(JSON.stringify(consoleError.mock.calls)).toContain('sk-proj-****ABCD');
  });

  it('does not forward the OpenAI body when exchanging an SDP offer', async () => {
    process.env.OPENAI_API_KEY = 'test-key';
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {});
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(upstreamResponse(LEAKY_OPENAI_ERROR, 429)));

    const res = await POST(sdpRequest('v=0\no=- 1 1 IN IP4 127.0.0.1'));
    const raw = await res.text();

    expect(res.status).toBe(502);
    expect(JSON.parse(raw)).toEqual({
      error: 'OpenAI Realtime session creation failed.',
      code: 'realtime_session_failed',
    });
    for (const token of LEAKED_TOKENS) {
      expect(raw).not.toContain(token);
    }
    expect(JSON.stringify(consoleError.mock.calls)).toContain('sk-proj-****ABCD');
  });
});

/**
 * A rejected fetch (DNS, TLS, reset, timeout) throws before any upstream status
 * exists. Without a catch it escapes to Next.js's own unstructured 500, which
 * breaks the JSON error contract the client parses and logs nothing.
 */
describe('/api/realtime/session transport failures', () => {
  it('returns the static 502 when the client-secret request never reaches OpenAI', async () => {
    process.env.OPENAI_API_KEY = 'test-key';
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {});
    vi.stubGlobal(
      'fetch',
      vi.fn().mockRejectedValue(new TypeError('fetch failed: getaddrinfo ENOTFOUND api.openai.com')),
    );

    const res = await GET();
    const raw = await res.text();

    expect(res.status).toBe(502);
    expect(JSON.parse(raw)).toEqual({
      error: 'OpenAI Realtime client secret creation failed.',
      code: 'realtime_client_secret_failed',
    });
    expect(JSON.stringify(consoleError.mock.calls)).toContain('client_secret request failed');
  });

  it('returns the static 502 when the SDP exchange never reaches OpenAI', async () => {
    process.env.OPENAI_API_KEY = 'test-key';
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {});
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('socket hang up')));

    const res = await POST(sdpRequest('v=0\no=- 1 1 IN IP4 127.0.0.1'));
    const raw = await res.text();

    expect(res.status).toBe(502);
    expect(JSON.parse(raw)).toEqual({
      error: 'OpenAI Realtime session creation failed.',
      code: 'realtime_session_failed',
    });
    expect(JSON.stringify(consoleError.mock.calls)).toContain('sdp_exchange request failed');
  });

  it('returns the static 502 when the upstream body cannot be read', async () => {
    process.env.OPENAI_API_KEY = 'test-key';
    vi.spyOn(console, 'error').mockImplementation(() => {});
    const truncated = new Response('', { status: 200 });
    vi.spyOn(truncated, 'text').mockRejectedValue(new Error('terminated: aborted mid-body'));
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(truncated));

    const res = await GET();

    expect(res.status).toBe(502);
    expect(await res.json()).toEqual({
      error: 'OpenAI Realtime client secret creation failed.',
      code: 'realtime_client_secret_failed',
    });
  });
});
