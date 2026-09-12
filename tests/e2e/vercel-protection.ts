/**
 * Vercel Deployment Protection helpers for the live E2E harness.
 *
 * Preview SSO returns HTTP 401 JSON `{ error: { message: "Protected deployment" } }`
 * (and HTML auth walls on document routes). That is not an application 401.
 */

export const VERCEL_PROTECTION_MESSAGE = 'Protected deployment';

export function isVercelProtectedDeploymentBody(body: string): boolean {
  const trimmed = body.trim();
  if (!trimmed) return false;
  if (trimmed.includes('vercel_auth_callback') && /protected deployment/i.test(trimmed)) {
    return true;
  }
  try {
    const parsed: unknown = JSON.parse(trimmed);
    if (parsed === null || typeof parsed !== 'object') return false;
    const record = parsed as Record<string, unknown>;
    const error = record.error;
    if (error !== null && typeof error === 'object') {
      const message = (error as Record<string, unknown>).message;
      if (typeof message === 'string' && message === VERCEL_PROTECTION_MESSAGE) {
        return true;
      }
    }
    const protection = record.protection;
    return protection !== null && typeof protection === 'object';
  } catch {
    return /authentication required|vercel\.com\/sso-api/i.test(trimmed);
  }
}

export function vercelProtectionHeaders(): Record<string, string> {
  const headers: Record<string, string> = {};
  const bypass = process.env.VERCEL_AUTOMATION_BYPASS_SECRET?.trim() ?? '';
  const oidc = process.env.VERCEL_OIDC_IDP_TOKEN?.trim() ?? '';
  if (bypass) {
    headers['x-vercel-protection-bypass'] = bypass;
    headers['x-vercel-set-bypass-cookie'] = 'true';
  }
  if (oidc) {
    headers['x-vercel-trusted-oidc-idp-token'] = oidc;
  }
  return headers;
}

export function shouldSkipLiveE2EForVercelProtection(input: {
  status: number;
  body: string;
}): boolean {
  return input.status === 401 && isVercelProtectedDeploymentBody(input.body);
}
