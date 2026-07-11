export type TurnstileVerifyResult = {
  ok: boolean;
  error?: string;
  errorCodes?: string[];
};

export async function verifyTurnstileToken(
  token: string,
  remoteIp?: string,
): Promise<TurnstileVerifyResult> {
  const secret = process.env.TURNSTILE_SECRET_KEY;
  if (!secret) {
    return { ok: false, error: 'turnstile_not_configured' };
  }
  if (!token?.trim()) {
    return { ok: false, error: 'turnstile_token_missing' };
  }

  const body = new URLSearchParams({ secret, response: token });
  if (remoteIp) {
    body.set('remoteip', remoteIp);
  }

  const res = await fetch('https://challenges.cloudflare.com/turnstile/v0/siteverify', {
    method: 'POST',
    headers: { 'content-type': 'application/x-www-form-urlencoded' },
    body,
  });

  if (!res.ok) {
    return { ok: false, error: `siteverify_http_${res.status}` };
  }

  const data = (await res.json()) as {
    success?: boolean;
    'error-codes'?: string[];
  };

  if (data.success) {
    return { ok: true };
  }

  return {
    ok: false,
    error: 'turnstile_verification_failed',
    errorCodes: data['error-codes'],
  };
}