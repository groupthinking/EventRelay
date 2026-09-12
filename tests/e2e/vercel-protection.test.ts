import { afterEach, describe, expect, it } from 'vitest';
import {
  isVercelProtectedDeploymentBody,
  shouldSkipLiveE2EForVercelProtection,
  vercelProtectionHeaders,
} from './vercel-protection';

/** Live preview 401 body from v0-uvai-f6x0r2shi-garv1.vercel.app (PR 1903). */
const PREVIEW_PROTECTION_JSON = JSON.stringify({
  error: { message: 'Protected deployment', code: '401' },
  protection: {
    vercel_auth_callback:
      'https://vercel.com/sso-api?url=https%3A%2F%2Fv0-uvai-f6x0r2shi-garv1.vercel.app%2Fapi%2Fpipeline%2Fstream&nonce=0665eaf29cd1c4d928887310682f8cc52e56458219a5bad36720c46f0f92b6b7',
  },
});

describe('Vercel deployment protection detector', () => {
  afterEach(() => {
    delete process.env.VERCEL_AUTOMATION_BYPASS_SECRET;
    delete process.env.VERCEL_OIDC_IDP_TOKEN;
  });

  it('recognizes the live preview Protected deployment JSON', () => {
    expect(isVercelProtectedDeploymentBody(PREVIEW_PROTECTION_JSON)).toBe(true);
    expect(
      shouldSkipLiveE2EForVercelProtection({ status: 401, body: PREVIEW_PROTECTION_JSON }),
    ).toBe(true);
  });

  it('does not treat an application 401 as Vercel SSO', () => {
    const app401 = JSON.stringify({ error: 'A YouTube URL or video id is required' });
    expect(isVercelProtectedDeploymentBody(app401)).toBe(false);
    expect(shouldSkipLiveE2EForVercelProtection({ status: 401, body: app401 })).toBe(false);
  });

  it('does not skip a 400 missing-URL response (protection was bypassed or public)', () => {
    expect(
      shouldSkipLiveE2EForVercelProtection({
        status: 400,
        body: JSON.stringify({ status: 'error', error: 'url required' }),
      }),
    ).toBe(false);
  });

  it('attaches bypass and OIDC headers only when those env vars are set', () => {
    expect(vercelProtectionHeaders()).toEqual({});
    process.env.VERCEL_AUTOMATION_BYPASS_SECRET = 'bypass-secret';
    process.env.VERCEL_OIDC_IDP_TOKEN = 'oidc-token';
    expect(vercelProtectionHeaders()).toEqual({
      'x-vercel-protection-bypass': 'bypass-secret',
      'x-vercel-set-bypass-cookie': 'true',
      'x-vercel-trusted-oidc-idp-token': 'oidc-token',
    });
  });
});
