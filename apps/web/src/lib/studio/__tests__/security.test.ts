import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { encode } from 'next-auth/jwt';
import { NextRequest } from 'next/server';
import { readStudioJson, requireStudioOwner, requireStudioMutationOrigin } from '../security';

const secret = 'offline-studio-test-secret-not-a-real-credential';
const endpoint = 'https://uvai.example/api/studio/chats';

beforeEach(() => {
  vi.stubEnv('NEXTAUTH_SECRET', secret);
  vi.stubEnv('NEXTAUTH_URL', 'https://uvai.example');
  vi.stubEnv('NODE_ENV', 'production');
});
afterEach(() => vi.unstubAllEnvs());

async function signedRequest(token: Record<string, unknown>, signingSecret = secret) {
  const value = await encode({ secret: signingSecret, token });
  return new NextRequest(endpoint, {
    headers: { cookie: `__Secure-next-auth.session-token=${value}` },
  });
}

describe('Studio verified ownership identity', () => {
  it('uses the verified NextAuth subject without requiring a Supabase UUID', async () => {
    const owner = await requireStudioOwner(await signedRequest({ sub: 'google-subject-123', email: 'a@example.test' }));
    expect(owner).toEqual({ subject: 'google-subject-123' });
  });

  it('rejects anonymous requests even when the global gate is bypassed', async () => {
    vi.stubEnv('AUTH_ALLOW_UNAUTHENTICATED', '1');
    vi.stubEnv('INTERNAL_REQUEST_TOKEN', 'internal-test-token');
    await expect(requireStudioOwner(new NextRequest(endpoint, {
      headers: { 'x-eventrelay-internal': 'internal-test-token', 'x-user-id': 'spoofed-owner' },
    }))).rejects.toMatchObject({ status: 401, code: 'authentication_required' });
  });

  it('rejects a token signed with another secret', async () => {
    await expect(requireStudioOwner(await signedRequest({ sub: 'attacker' }, 'wrong-secret')))
      .rejects.toMatchObject({ status: 401 });
  });

  it.each([{ email: 'a@example.test' }, { sub: '' }, { sub: '   ' }, { sub: 'a'.repeat(513) }])(
    'never substitutes email or malformed subjects for identity: %j', async (token) => {
      await expect(requireStudioOwner(await signedRequest(token))).rejects.toMatchObject({ status: 401 });
    },
  );

  it('rejects expired signed sessions', async () => {
    const value = await encode({ secret, token: { sub: 'expired-owner' }, maxAge: -60 });
    await expect(requireStudioOwner(new NextRequest(endpoint, {
      headers: { cookie: `__Secure-next-auth.session-token=${value}` },
    }))).rejects.toMatchObject({ status: 401 });
  });

  it('fails closed when session verification is not configured', async () => {
    vi.stubEnv('NEXTAUTH_SECRET', '');
    await expect(requireStudioOwner(new NextRequest(endpoint)))
      .rejects.toMatchObject({ status: 503, code: 'authentication_unavailable' });
  });

  it('uses the configured non-secure cookie only for local HTTP development', async () => {
    vi.stubEnv('NODE_ENV', 'development');
    vi.stubEnv('NEXTAUTH_URL', 'http://localhost:3000');
    const value = await encode({ secret, token: { sub: 'local-subject' } });
    await expect(requireStudioOwner(new NextRequest('http://localhost:3000/api/studio/chats', {
      headers: { cookie: `next-auth.session-token=${value}` },
    }))).resolves.toEqual({ subject: 'local-subject' });
  });
});

describe('Studio mutation origin checks', () => {
  it('accepts a same-origin browser mutation', () => {
    expect(() => requireStudioMutationOrigin(new NextRequest(endpoint, {
      method: 'POST', headers: { origin: 'https://uvai.example', 'sec-fetch-site': 'same-origin' },
    }))).not.toThrow();
  });

  it.each([null, 'null', 'https://untrusted.example', 'https://uvai.example.attacker.test', 'https://uvai.example/path'])('rejects origin %s', (origin) => {
    const headers = new Headers();
    if (origin !== null) headers.set('origin', origin);
    expect(() => requireStudioMutationOrigin(new NextRequest(endpoint, { method: 'POST', headers })))
      .toThrow(expect.objectContaining({ status: 403, code: 'invalid_origin' }));
  });

  it('does not trust forwarded-host headers to authorize a mutation', () => {
    expect(() => requireStudioMutationOrigin(new NextRequest(endpoint, {
      method: 'POST', headers: { origin: 'https://attacker.test', 'x-forwarded-host': 'attacker.test' },
    }))).toThrow(expect.objectContaining({ status: 403 }));
  });

  it('rejects cross-site browser requests', () => {
    expect(() => requireStudioMutationOrigin(new NextRequest(endpoint, {
      method: 'POST', headers: { origin: 'https://uvai.example', 'sec-fetch-site': 'cross-site' },
    }))).toThrow(expect.objectContaining({ status: 403 }));
  });
});

describe('bounded Studio JSON input', () => {
  function request(body: string, headers: Record<string, string> = {}) {
    return new NextRequest(endpoint, { method: 'POST', body, headers: { 'content-type': 'application/json', ...headers } });
  }

  it('reads valid JSON', async () => {
    await expect(readStudioJson(request('{"prompt":"Build an app"}'))).resolves.toEqual({ prompt: 'Build an app' });
  });
  it('requires JSON content type', async () => {
    await expect(readStudioJson(request('{}', { 'content-type': 'text/plain' }))).rejects.toMatchObject({ status: 415 });
  });
  it('sanitizes malformed JSON errors', async () => {
    await expect(readStudioJson(request('{private broken input'))).rejects.toMatchObject({ status: 400, message: 'Invalid JSON request.' });
  });
  it('rejects oversized declared payloads before reading', async () => {
    await expect(readStudioJson(request('{}', { 'content-length': '32769' }))).rejects.toMatchObject({ status: 413 });
  });
  it('bounds streamed bytes even without a content-length header', async () => {
    await expect(readStudioJson(request(JSON.stringify({ prompt: 'x'.repeat(32768) })))).rejects.toMatchObject({ status: 413 });
  });
  it('counts UTF-8 bytes rather than JavaScript characters', async () => {
    await expect(readStudioJson(request(JSON.stringify({ prompt: '界'.repeat(12000) })))).rejects.toMatchObject({ status: 413 });
  });
});
