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
