import { afterEach, describe, expect, it, vi } from 'vitest';
import { encode } from 'next-auth/jwt';
import { NextRequest } from 'next/server';
import { getNextAuthJwtFromRequest, nextAuthUseSecureCookies } from '@/lib/auth-jwt';

afterEach(() => {
  vi.unstubAllEnvs();
});

describe('nextAuthUseSecureCookies', () => {
  it('forces secure cookies in production even without NEXTAUTH_URL', () => {
    vi.stubEnv('NODE_ENV', 'production');
    vi.stubEnv('NEXTAUTH_URL', '');
    expect(nextAuthUseSecureCookies()).toBe(true);
  });

  it('uses secure cookies when NEXTAUTH_URL is https', () => {
    vi.stubEnv('NODE_ENV', 'development');
    vi.stubEnv('NEXTAUTH_URL', 'https://uvai.io');
    expect(nextAuthUseSecureCookies()).toBe(true);
  });
});

describe('getNextAuthJwtFromRequest', () => {
  it('reads __Secure- session cookies in production without NEXTAUTH_URL', async () => {
    vi.stubEnv('NODE_ENV', 'production');
    vi.stubEnv('NEXTAUTH_URL', '');
    vi.stubEnv('NEXTAUTH_SECRET', 'test-secret-at-least-32-chars-long');

    const token = await encode({
      token: { sub: 'user-1', email: 'garveyht@gmail.com' },
      secret: process.env.NEXTAUTH_SECRET!,
    });

    const req = new NextRequest('https://uvai.io/studio', {
      headers: { cookie: `__Secure-next-auth.session-token=${token}` },
    });

    const decoded = await getNextAuthJwtFromRequest(req, process.env.NEXTAUTH_SECRET!);
    expect(decoded?.sub).toBe('user-1');
    expect(decoded?.email).toBe('garveyht@gmail.com');
  });
});
