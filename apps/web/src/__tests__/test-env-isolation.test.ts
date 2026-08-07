import { describe, expect, it } from 'vitest';

/**
 * Hermeticity guard for the test environment.
 *
 * `vitest.config.ts` promises that route-handler tests are "deterministic
 * regardless of the developer's shell env". That promise was only partially
 * kept: `BACKEND_URL` and `BILLING_COOKIE_SECRET` were neutralised, but the
 * Vercel AI Gateway credentials were not.
 *
 * The consequence was a real, reproducible flake. `app/api/chat/route.ts`
 * branches on mere *presence* of a gateway key and then calls `generateText()`
 * against https://ai-gateway.vercel.sh. On any machine (or CI runner) with
 * `AI_GATEWAY_API_KEY` exported, `billing-chat-gating.test.ts` therefore issued
 * live network calls and intermittently blew its 5s timeout — a failure with no
 * relationship to the code under test.
 *
 * These assertions fail loudly if that neutralisation is ever dropped from
 * `vitest.config.ts`, on exactly the machines where it matters.
 *
 * Note this guards the *ambient default* only. Tests that genuinely exercise
 * the configured-provider path (chat-gateway-fallback, gemini-client,
 * vercel-ai-gateway) set these keys explicitly in their own setup and restore
 * them afterwards; that remains both supported and correct.
 */
describe('test environment isolation', () => {
  // Every variable consulted by resolveAiGatewayKey() in lib/vercel-ai-gateway.ts.
  // Keep in sync with that function — a key missing here is a key that can leak.
  const GATEWAY_KEYS = [
    'AI_GATEWAY_API_KEY',
    'VERCEL_AI_GATEWAY_API_KEY',
    'VERCEL_AI_GATEWAY_API',
    'VERCEL_API_KEY',
  ] as const;

  it.each(GATEWAY_KEYS)('does not leak %s from the ambient shell into tests', (key) => {
    expect(process.env[key] ?? '').toBe('');
  });

  it('does not leak a live BACKEND_URL into tests', () => {
    // Route handlers gate on `startsWith('http')`; anything else keeps them in
    // frontend-only mode, which is what the suite asserts against.
    expect(process.env.BACKEND_URL ?? '').not.toMatch(/^http/);
  });
});
