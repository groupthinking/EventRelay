import 'server-only';

import { createHmac, timingSafeEqual } from 'node:crypto';

/**
 * HMAC-signed billing identity cookie.
 *
 * SECURITY: The billing entitlement cookie (`er_billing_email`) is a trusted
 * identity used to grant Pro features and expose a customer's Stripe IDs. It was
 * previously stored as a plaintext email. `httpOnly` prevents JavaScript from
 * *reading* it, but does nothing to stop a client from *forging* it — anyone
 * could send `Cookie: er_billing_email=victim@example.com` to impersonate a
 * paying user (free Pro access + Stripe ID disclosure).
 *
 * The value is now `base64url(email).base64url(HMAC-SHA256(payload, secret))`.
 * Verification recomputes the HMAC with a constant-time comparison, so a cookie
 * is only trusted if it was minted server-side. Legacy unsigned cookies fail
 * verification and are treated as anonymous (users simply re-activate).
 */

/**
 * Resolve the signing secret. We reuse existing server secrets so no new env var
 * is strictly required in production (Stripe billing already needs a webhook
 * secret). A dedicated `BILLING_COOKIE_SECRET` can be set to rotate independently.
 */
function getSigningSecret(): string | null {
  return (
    process.env.BILLING_COOKIE_SECRET?.trim() ||
    process.env.NEXTAUTH_SECRET?.trim() ||
    process.env.STRIPE_WEBHOOK_SECRET?.trim() ||
    null
  );
}

function b64url(input: string): string {
  return Buffer.from(input, 'utf8').toString('base64url');
}

function computeSignature(payload: string, secret: string): string {
  return createHmac('sha256', secret).update(payload).digest('base64url');
}

/**
 * Produce a signed cookie value for the given email. Returns `null` when no
 * signing secret is configured — callers must then decline to set the cookie
 * rather than fall back to an unsigned (forgeable) value.
 */
export function signBillingEmail(email: string): string | null {
  const secret = getSigningSecret();
  if (!secret) return null;
  const payload = b64url(email);
  const signature = computeSignature(payload, secret);
  return `${payload}.${signature}`;
}

/**
 * Verify a signed cookie value and return the embedded email, or `null` if the
 * value is missing, malformed, unsigned (legacy), or has an invalid signature.
 */
export function verifyBillingEmailCookie(value: string | undefined | null): string | null {
  if (!value) return null;
  const secret = getSigningSecret();
  if (!secret) return null;

  const separator = value.lastIndexOf('.');
  if (separator <= 0 || separator >= value.length - 1) return null;

  const payload = value.slice(0, separator);
  const providedSig = value.slice(separator + 1);
  const expectedSig = computeSignature(payload, secret);

  const providedBuf = Buffer.from(providedSig);
  const expectedBuf = Buffer.from(expectedSig);
  if (providedBuf.length !== expectedBuf.length) return null;
  if (!timingSafeEqual(providedBuf, expectedBuf)) return null;

  try {
    const email = Buffer.from(payload, 'base64url').toString('utf8');
    return email.trim() ? email : null;
  } catch {
    return null;
  }
}
