import { describe, it, expect } from 'vitest';
import {
  isPublicApiPath,
  isProtectedPagePath,
  needsAuthentication,
  safeCallbackPath,
  shouldSkipRateLimit,
} from '@/lib/auth-paths';

describe('auth path policy', () => {
  it('keeps NextAuth and Stripe webhook public', () => {
    expect(isPublicApiPath('/api/auth')).toBe(true);
    expect(isPublicApiPath('/api/auth/signin/google')).toBe(true);
    expect(isPublicApiPath('/api/auth/callback/google')).toBe(true);
    expect(isPublicApiPath('/api/billing/webhook')).toBe(true);
    expect(isPublicApiPath('/api/billing/status')).toBe(true);
    expect(isPublicApiPath('/api/billing/checkout')).toBe(true);
  });

  it('keeps checkout-lifecycle billing routes reachable without a NextAuth session', () => {
    // activate identifies the payer from the Stripe checkout sessionId and renew
    // from the signed billing cookie — neither has a NextAuth session at that
    // point, so middleware must not 401 them.
    expect(isPublicApiPath('/api/billing/activate')).toBe(true);
    expect(isPublicApiPath('/api/billing/renew')).toBe(true);
    expect(needsAuthentication('/api/billing/activate')).toBe(false);
    expect(needsAuthentication('/api/billing/renew')).toBe(false);
  });

  it('still gates non-allowlisted billing routes', () => {
    // A sibling billing route with no explicit exemption stays protected —
    // guards against prefix-match over-exposure.
    expect(isPublicApiPath('/api/billing/manage')).toBe(false);
    expect(needsAuthentication('/api/billing/manage')).toBe(true);
  });

  it('requires auth for product APIs and dashboard pages', () => {
    expect(needsAuthentication('/api/chat')).toBe(true);
    expect(needsAuthentication('/api/pipeline')).toBe(true);
    expect(needsAuthentication('/api/video')).toBe(true);
    expect(needsAuthentication('/dashboard')).toBe(true);
    expect(needsAuthentication('/dashboard/agents')).toBe(true);
    expect(isProtectedPagePath('/dashboard/agents')).toBe(true);
  });

  it('does not gate marketing pages', () => {
    expect(needsAuthentication('/')).toBe(false);
    expect(needsAuthentication('/pricing')).toBe(false);
    expect(needsAuthentication('/features')).toBe(false);
  });

  it('sanitizes callback paths against open redirects', () => {
    expect(safeCallbackPath('/dashboard')).toBe('/dashboard');
    expect(safeCallbackPath('/dashboard', '?tab=agents')).toBe('/dashboard?tab=agents');
    expect(safeCallbackPath('//evil.com')).toBe('/dashboard');
    expect(safeCallbackPath('https://evil.com')).toBe('/dashboard');
    expect(safeCallbackPath('/\\evil.com')).toBe('/dashboard');
  });

  it('skips rate limits for the auth handshake', () => {
    expect(shouldSkipRateLimit('/api/auth/csrf')).toBe(true);
    expect(shouldSkipRateLimit('/api/auth/callback/google')).toBe(true);
    expect(shouldSkipRateLimit('/api/chat')).toBe(false);
  });
});
