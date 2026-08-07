import { describe, it, expect } from 'vitest';
import {
  isAiRoute,
  isPublicApiPath,
  isProtectedPagePath,
  needsAuthentication,
  resolveAuthGateMode,
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

  it('keeps /api/pipeline/stream public (core EventRelay pipeline entry point)', () => {
    // The pipeline/stream SSE endpoint is the primary unauthenticated entry
    // point for the YouTube → transcript → agents workflow. Gating it behind
    // a session would block the E2E smoke tests and anonymous end-users.
    expect(isPublicApiPath('/api/pipeline/stream')).toBe(true);
    expect(needsAuthentication('/api/pipeline/stream')).toBe(false);
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

describe('login gate mode (issue #1058)', () => {
  it('enforces whenever a secret is configured, in any environment', () => {
    expect(resolveAuthGateMode({ secret: 's', nodeEnv: 'production' })).toBe('enforce');
    expect(resolveAuthGateMode({ secret: 's', nodeEnv: 'development' })).toBe('enforce');
    // An explicit opt-out must never downgrade a properly configured deployment.
    expect(
      resolveAuthGateMode({ secret: 's', nodeEnv: 'production', allowUnauthenticated: '1' }),
    ).toBe('enforce');
  });

  it('fails closed in production when the secret is missing', () => {
    expect(resolveAuthGateMode({ nodeEnv: 'production' })).toBe('misconfigured');
    expect(resolveAuthGateMode({ secret: '', nodeEnv: 'production' })).toBe('misconfigured');
    // Whitespace-only is not a usable secret.
    expect(resolveAuthGateMode({ secret: '   ', nodeEnv: 'production' })).toBe('misconfigured');
  });

  it('keeps the gate off outside production so local dev is unaffected', () => {
    expect(resolveAuthGateMode({ nodeEnv: 'development' })).toBe('disabled');
    expect(resolveAuthGateMode({ nodeEnv: 'test' })).toBe('disabled');
    expect(resolveAuthGateMode({})).toBe('disabled');
  });

  it('allows a deliberate public production deployment only via an explicit flag', () => {
    for (const flag of ['1', 'true', 'TRUE', 'yes', 'on']) {
      expect(resolveAuthGateMode({ nodeEnv: 'production', allowUnauthenticated: flag })).toBe(
        'disabled',
      );
    }
    // Anything that is not an affirmative value must still fail closed, so a
    // typo (or an empty value from a CI secret) cannot silently open the app.
    for (const flag of ['0', 'false', 'no', '', 'maybe', undefined]) {
      expect(resolveAuthGateMode({ nodeEnv: 'production', allowUnauthenticated: flag })).toBe(
        'misconfigured',
      );
    }
  });
});

describe('AI route classification (rate-limit budget)', () => {
  it('meters model-backed routes against the AI budget', () => {
    for (const path of [
      '/api/agents/dispatch',
      '/api/chat',
      '/api/extract-events',
      '/api/pipeline',
      '/api/realtime',
      '/api/training',
      '/api/transcribe',
      '/api/video',
    ]) {
      expect(isAiRoute(path, 'POST')).toBe(true);
    }
  });

  it('leaves non-AI API routes on the general budget', () => {
    expect(isAiRoute('/api/billing/status', 'GET')).toBe(false);
    expect(isAiRoute('/api/health', 'GET')).toBe(false);
    expect(isAiRoute('/api/auth/session', 'GET')).toBe(false);
  });

  it('keeps starting a workflow run on the AI budget', () => {
    // POST .../video-to-actions fetches a transcript and runs an action agent.
    // That is genuine model work and must stay metered.
    expect(isAiRoute('/api/workflows/video-to-actions', 'POST')).toBe(true);
  });

  it('exempts workflow status polls from the AI budget', () => {
    // GET .../:runId reads stored run state and makes no model call. Metering
    // it as AI-class throttles the poller to 12/min while it polls at 30/min.
    expect(isAiRoute('/api/workflows/video-to-actions/run_123', 'GET')).toBe(false);
    expect(isAiRoute('/api/workflows/video-to-actions/run_123', 'HEAD')).toBe(false);
  });

  it('does not let a status poll drain the shared AI bucket', () => {
    // The bucket is keyed by class, not path: every AI prefix shares one
    // `ai:<ip>` counter. If polls were AI-class, one Studio run would 429
    // /api/chat and /api/transcribe as collateral. This is the regression that
    // motivated the method-aware check, so assert the pairing directly.
    const poll = '/api/workflows/video-to-actions/run_123';
    expect(isAiRoute(poll, 'GET')).toBe(false);
    expect(isAiRoute('/api/chat', 'GET')).toBe(true);
  });

  it('is case-insensitive about the method', () => {
    expect(isAiRoute('/api/workflows/video-to-actions/run_1', 'get')).toBe(false);
  });

  it('keeps mutating verbs on workflows AI-class', () => {
    // Only reads are exempt — a DELETE/PUT that reaches the workflow runtime
    // must not slip onto the looser budget.
    for (const method of ['POST', 'PUT', 'PATCH', 'DELETE']) {
      expect(isAiRoute('/api/workflows/video-to-actions/run_1', method)).toBe(true);
    }
  });

  it('defaults to the stricter budget when no method is supplied', () => {
    // Fail safe: an omitted argument must not silently widen the allowance.
    expect(isAiRoute('/api/workflows/video-to-actions/run_1')).toBe(true);
    expect(isAiRoute('/api/chat')).toBe(true);
  });

  it('does not exempt GET on other AI routes', () => {
    // The exemption is deliberately per-prefix. A blanket GET carve-out would
    // open every model-backed route the moment one served work over GET.
    expect(isAiRoute('/api/chat/history', 'GET')).toBe(true);
    expect(isAiRoute('/api/transcribe/status', 'GET')).toBe(true);
  });
});
