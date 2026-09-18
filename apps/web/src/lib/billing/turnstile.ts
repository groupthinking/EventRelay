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

  // Every other exit returns a TurnstileVerifyResult, so callers reasonably treat
  // this function as non-rejecting. Two awaits below can break that: the siteverify
  // fetch rejects on a transport failure (undici puts the resolved host and port in
  // the reason — `connect ECONNREFUSED 10.0.3.14:443`), and res.json() rejects when
  // Cloudflare answers 2xx with a truncated or non-JSON body. Either would escape
  // the sole caller — the unauthenticated /api/billing/checkout route — as an
  // unstructured framework 500 with no kaizenObserve trace. The reason is logged
  // server-side and collapsed into an app-authored literal.
  try {
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
  } catch (err) {
    console.error('[billing] turnstile siteverify unreachable:', err);

    return { ok: false, error: 'turnstile_verification_unavailable' };
  }
}