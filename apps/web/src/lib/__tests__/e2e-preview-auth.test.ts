import { afterEach, describe, expect, it, vi } from 'vitest';
import {
  buildVercelProtectionBypassHeaders,
  isVercelProtectionResponse,
} from '../e2e-preview-auth';

describe('E2E preview auth helpers', () => {
  afterEach(() => vi.unstubAllEnvs());

  it('sends only the per-request Vercel bypass header', () => {
    expect(buildVercelProtectionBypassHeaders('')).toEqual({});
    expect(buildVercelProtectionBypassHeaders('preview-secret')).toEqual({
      'x-vercel-protection-bypass': 'preview-secret',
    });
    expect(buildVercelProtectionBypassHeaders('preview-secret')).not.toHaveProperty(
      'x-vercel-set-bypass-cookie',
    );
  });

  it('reads Vercel bypass secret from env for each call', () => {
    vi.stubEnv('VERCEL_AUTOMATION_BYPASS_SECRET', 'first-secret');
    expect(buildVercelProtectionBypassHeaders()).toEqual({
      'x-vercel-protection-bypass': 'first-secret',
    });

    vi.stubEnv('VERCEL_AUTOMATION_BYPASS_SECRET', 'second-secret');
    expect(buildVercelProtectionBypassHeaders()).toEqual({
      'x-vercel-protection-bypass': 'second-secret',
    });
  });

  it.each([
    [401, '', true],
    [302, 'https://vercel.com/sso-api?from=%2F', true],
    [307, 'https://vercel.com/sso-api', true],
    [302, 'https://preview.example.test/', false],
    [200, '', false],
  ])(
    'classifies preview protection for status %s and location %s',
    (status, location, expected) => {
      expect(isVercelProtectionResponse(status, location)).toBe(expected);
    },
  );
});
