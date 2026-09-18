const VERCEL_SSO_PATH = /vercel\.com\/sso-api/i;

export function buildVercelProtectionBypassHeaders(
  secret: string | null | undefined,
): Record<string, string> {
  const token = secret?.trim();
  return token ? { 'x-vercel-protection-bypass': token } : {};
}

export function isVercelProtectionResponse(
  status: number,
  location: string | null | undefined,
): boolean {
  return (
    status === 401 ||
    ([301, 302, 303, 307, 308].includes(status) && VERCEL_SSO_PATH.test(location ?? ''))
  );
}
