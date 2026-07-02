import { cookies } from 'next/headers';
import { getToken } from 'next-auth/jwt';
import { normalizeBillingEmail } from './entitlement-store';
import { verifyBillingEmailCookie } from './billing-cookie';

export const BILLING_EMAIL_COOKIE = 'er_billing_email';

/**
 * Trusted billing identity for entitlement checks.
 * Order: NextAuth session email → HMAC-signed httpOnly billing cookie.
 * Never accepts client-supplied body/header email, and never trusts an
 * unsigned/forged billing cookie (prevents Pro spoofing + Stripe ID disclosure).
 */
export async function resolveTrustedBillingEmail(
  request: Request,
): Promise<string | null> {
  const secret = process.env.NEXTAUTH_SECRET;
  if (secret) {
    try {
      const token = await getToken({ req: request as Parameters<typeof getToken>[0]['req'], secret });
      const sessionEmail = typeof token?.email === 'string' ? token.email : null;
      if (sessionEmail?.trim()) {
        return normalizeBillingEmail(sessionEmail);
      }
    } catch {
      // fall through to cookie
    }
  }

  try {
    const jar = await cookies();
    const fromCookie = jar.get(BILLING_EMAIL_COOKIE)?.value;
    const verified = verifyBillingEmailCookie(fromCookie);
    if (verified) return normalizeBillingEmail(verified);
  } catch {
    // cookies() unavailable in some unit tests — allow Cookie header fallback
    const raw = request.headers.get('cookie') ?? '';
    const match = raw.match(new RegExp(`${BILLING_EMAIL_COOKIE}=([^;]+)`));
    if (match?.[1]) {
      const verified = verifyBillingEmailCookie(decodeURIComponent(match[1]));
      if (verified) return normalizeBillingEmail(verified);
    }
  }

  return null;
}

/** @deprecated Use resolveTrustedBillingEmail for entitlement; body email is not trusted. */
export async function resolveBillingEmailFromRequest(
  request: Request,
  _bodyEmail?: string,
): Promise<string | null> {
  return resolveTrustedBillingEmail(request);
}
