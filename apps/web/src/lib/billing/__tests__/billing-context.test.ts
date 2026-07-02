import { describe, it, expect } from 'vitest';
import { resolveTrustedBillingEmail, BILLING_EMAIL_COOKIE } from '../billing-context';

describe('resolveTrustedBillingEmail', () => {
  it('reads billing email from httpOnly cookie header', async () => {
    const req = new Request('http://localhost/api/chat', {
      headers: { cookie: `${BILLING_EMAIL_COOKIE}=trusted%40example.com` },
    });
    const email = await resolveTrustedBillingEmail(req);
    expect(email).toBe('trusted@example.com');
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