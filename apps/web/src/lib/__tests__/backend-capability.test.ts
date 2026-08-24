import { describe, expect, it } from 'vitest';

import {
  resolveBackendCapability,
  resolveBackendStatusUrl,
} from '@/lib/backend/capability';

/**
 * Regression suite for audit finding **F1**.
 *
 * The production bug: every backend caller read `process.env.BACKEND_URL`
 * exclusively, but this project only sets `NEXT_PUBLIC_BACKEND_URL`. The backend
 * was live and CSP-whitelisted the entire time, yet every agent dispatch, build,
 * and deploy tool returned `isError: true`.
 *
 * The first test below is the specific guard: with ONLY
 * `NEXT_PUBLIC_BACKEND_URL` set, resolution must report `configured: true`. If
 * anyone narrows the resolver back to a single env name, this fails.
 */

const PROD_BACKEND = 'https://uvai-backend-gpwz4wb5na-uc.a.run.app';

describe('resolveBackendCapability — F1 regression', () => {
  it('resolves when ONLY NEXT_PUBLIC_BACKEND_URL is set (the exact production bug)', () => {
    const capability = resolveBackendCapability({
      NEXT_PUBLIC_BACKEND_URL: PROD_BACKEND,
      NODE_ENV: 'production',
    } as NodeJS.ProcessEnv);

    expect(capability.configured).toBe(true);
    expect(capability.url).toBe(PROD_BACKEND);
    expect(capability.source).toBe('NEXT_PUBLIC_BACKEND_URL');
  });

  it('resolves when ONLY NEXT_PUBLIC_API_URL is set', () => {
    const capability = resolveBackendCapability({
      NEXT_PUBLIC_API_URL: PROD_BACKEND,
    } as NodeJS.ProcessEnv);

    expect(capability.configured).toBe(true);
    expect(capability.source).toBe('NEXT_PUBLIC_API_URL');
  });

  it('prefers the server-only BACKEND_URL when several names are set', () => {
    const capability = resolveBackendCapability({
      BACKEND_URL: 'https://server.example.com',
      NEXT_PUBLIC_BACKEND_URL: PROD_BACKEND,
      NEXT_PUBLIC_API_URL: 'https://third.example.com',
    } as NodeJS.ProcessEnv);

    expect(capability.source).toBe('BACKEND_URL');
    expect(capability.url).toBe('https://server.example.com');
  });
});

describe('resolveBackendCapability — normalisation', () => {
  it('strips trailing slashes so callers can safely append /api/...', () => {
    const capability = resolveBackendCapability({
      BACKEND_URL: 'https://backend.example.com///',
    } as NodeJS.ProcessEnv);

    expect(capability.url).toBe('https://backend.example.com');
  });

  it('trims surrounding whitespace from Secret Manager values', () => {
    const capability = resolveBackendCapability({
      BACKEND_URL: `  ${PROD_BACKEND}\n`,
    } as NodeJS.ProcessEnv);

    expect(capability.configured).toBe(true);
    expect(capability.url).toBe(PROD_BACKEND);
  });

  it('reports host without the scheme for safe logging', () => {
    const capability = resolveBackendCapability({
      BACKEND_URL: PROD_BACKEND,
    } as NodeJS.ProcessEnv);

    expect(capability.host).toBe('uvai-backend-gpwz4wb5na-uc.a.run.app');
  });
});

describe('resolveBackendCapability — rejection paths', () => {
  it('is unconfigured when no candidate env var is present', () => {
    const capability = resolveBackendCapability({} as NodeJS.ProcessEnv);

    expect(capability.configured).toBe(false);
    expect(capability.url).toBeNull();
    // The reason must name every variable checked, so an operator can act on it.
    expect(capability.reason).toContain('BACKEND_URL');
    expect(capability.reason).toContain('NEXT_PUBLIC_BACKEND_URL');
    expect(capability.reason).toContain('NEXT_PUBLIC_API_URL');
  });

  it('rejects a malformed URL and explains which variable was bad', () => {
    const capability = resolveBackendCapability({
      BACKEND_URL: 'not-a-url',
    } as NodeJS.ProcessEnv);

    expect(capability.configured).toBe(false);
    expect(capability.reason).toContain('BACKEND_URL');
  });

  it('rejects non-http schemes', () => {
    const capability = resolveBackendCapability({
      BACKEND_URL: 'ftp://backend.example.com',
    } as NodeJS.ProcessEnv);

    expect(capability.configured).toBe(false);
    expect(capability.reason).toContain('scheme');
  });

  it('falls through a bad value to the next candidate rather than giving up', () => {
    const capability = resolveBackendCapability({
      BACKEND_URL: 'not-a-url',
      NEXT_PUBLIC_BACKEND_URL: PROD_BACKEND,
    } as NodeJS.ProcessEnv);

    expect(capability.configured).toBe(true);
    expect(capability.source).toBe('NEXT_PUBLIC_BACKEND_URL');
  });

  it('rejects a localhost backend in production', () => {
    const capability = resolveBackendCapability({
      BACKEND_URL: 'http://localhost:8000',
      NODE_ENV: 'production',
    } as NodeJS.ProcessEnv);

    expect(capability.configured).toBe(false);
    expect(capability.reason).toContain('non-routable');
  });

  it.each([
    'http://127.0.0.1:8000',
    'http://10.0.0.5',
    'http://192.168.1.10',
    'http://172.16.0.1',
    'http://169.254.169.254',
    'http://api.internal',
  ])('rejects non-routable %s in production', (url) => {
    const capability = resolveBackendCapability({
      BACKEND_URL: url,
      NODE_ENV: 'production',
    } as NodeJS.ProcessEnv);

    expect(capability.configured).toBe(false);
  });

  it('ALLOWS localhost outside production so local dev still works', () => {
    const capability = resolveBackendCapability({
      BACKEND_URL: 'http://localhost:8000',
      NODE_ENV: 'development',
    } as NodeJS.ProcessEnv);

    expect(capability.configured).toBe(true);
    expect(capability.url).toBe('http://localhost:8000');
  });
});

describe('resolveBackendStatusUrl — SSRF guard preserved', () => {
  it('resolves a relative status path against the backend origin', () => {
    expect(resolveBackendStatusUrl('/api/v1/jobs/abc', PROD_BACKEND)).toBe(
      `${PROD_BACKEND}/api/v1/jobs/abc`,
    );
  });

  it('accepts an absolute URL on the same origin', () => {
    expect(
      resolveBackendStatusUrl(`${PROD_BACKEND}/api/v1/jobs/abc`, PROD_BACKEND),
    ).toBe(`${PROD_BACKEND}/api/v1/jobs/abc`);
  });

  it('refuses a status URL on a foreign origin, so the API key never leaks', () => {
    expect(() =>
      resolveBackendStatusUrl('https://evil.example.com/steal', PROD_BACKEND),
    ).toThrow(/untrusted origin/);
  });
});
