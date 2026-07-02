import { describe, it, expect } from 'vitest';
import { resolveTrustedBillingEmail, BILLING_EMAIL_COOKIE } from '../billing-context';
import { signBillingEmail } from '../billing-cookie';

describe('resolveTrustedBillingEmail', () => {
  it('reads billing email from a valid HMAC-signed httpOnly cookie', async () => {
    const signed = signBillingEmail('trusted@example.com');
    expect(signed).toBeTruthy();
    const req = new Request('http://localhost/api/chat', {
      headers: { cookie: `${BILLING_EMAIL_COOKIE}=${encodeURIComponent(signed as string)}` },
    });
    const email = await resolveTrustedBillingEmail(req);
    expect(email).toBe('trusted@example.com');
  });

  it('rejects a forged (unsigned) billing cookie', async () => {
    // Attacker sets the cookie to a plaintext victim email — the old vuln.
    const req = new Request('http://localhost/api/chat', {
      headers: { cookie: `${BILLING_EMAIL_COOKIE}=victim%40example.com` },
    });
    const email = await resolveTrustedBillingEmail(req);
    expect(email).toBeNull();
  });

  it('rejects a signed cookie whose signature has been tampered with', async () => {
    const signed = signBillingEmail('trusted@example.com') as string;
    const tampered = signed.slice(0, -3) + 'AAA';
    const req = new Request('http://localhost/api/chat', {
      headers: { cookie: `${BILLING_EMAIL_COOKIE}=${encodeURIComponent(tampered)}` },
    });
    const email = await resolveTrustedBillingEmail(req);
    expect(email).toBeNull();
  });

  it('ignores spoofed body billing_email (not used by resolver)', async () => {
    const req = new Request('http://localhost/api/chat', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ billing_email: 'spoofed@example.com' }),
    });
    const email = await resolveTrustedBillingEmail(req);
    expect(email).toBeNull();
  });
});
