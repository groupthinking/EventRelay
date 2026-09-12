import { afterEach, describe, expect, it, vi } from 'vitest';
import { verifyTurnstileToken } from '@/lib/billing/turnstile';

const ORIGINAL_SECRET = process.env.TURNSTILE_SECRET_KEY;

afterEach(() => {
  if (ORIGINAL_SECRET === undefined) delete process.env.TURNSTILE_SECRET_KEY;
  else process.env.TURNSTILE_SECRET_KEY = ORIGINAL_SECRET;

  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe('verifyTurnstileToken', () => {
  it('reports ok when Cloudflare accepts the token', async () => {
    process.env.TURNSTILE_SECRET_KEY = 'test-secret';
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(new Response(JSON.stringify({ success: true }), { status: 200 })),
    );

    await expect(verifyTurnstileToken('token')).resolves.toEqual({ ok: true });
  });

  it('surfaces a non-2xx siteverify status as an app-authored literal', async () => {
    process.env.TURNSTILE_SECRET_KEY = 'test-secret';
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('', { status: 503 })));

    await expect(verifyTurnstileToken('token')).resolves.toEqual({
      ok: false,
      error: 'siteverify_http_503',
    });
  });
});

/**
 * Every other exit returns a TurnstileVerifyResult, so the sole caller — the
 * unauthenticated /api/billing/checkout route — treats this as non-rejecting.
 * A reject escapes it as an unstructured framework 500 with no kaizenObserve
 * trace, and undici's reason carries the resolved host and port.
 */
describe('verifyTurnstileToken transport failures', () => {
  it('resolves to a static result when siteverify is unreachable', async () => {
    process.env.TURNSTILE_SECRET_KEY = 'test-secret';
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {});
    vi.stubGlobal(
      'fetch',
      vi.fn().mockRejectedValue(new TypeError('fetch failed: connect ECONNREFUSED 10.0.3.14:443')),
    );

    const result = await verifyTurnstileToken('token');

    expect(result).toEqual({ ok: false, error: 'turnstile_verification_unavailable' });
    // The resolved host and port must not ride out on the result...
    expect(JSON.stringify(result)).not.toContain('10.0.3.14');
    expect(JSON.stringify(result)).not.toContain('ECONNREFUSED');
    // ...but operators still get the reason server-side. Asserted on the logged
    // argument itself: JSON.stringify would render an Error as `{}`, since its
    // properties are non-enumerable, and would pass vacuously.
    const [label, logged] = consoleError.mock.calls[0];
    expect(label).toContain('turnstile siteverify unreachable');
    expect((logged as Error).message).toContain('ECONNREFUSED 10.0.3.14:443');
  });

  it('resolves to a static result when the siteverify body is unreadable', async () => {
    process.env.TURNSTILE_SECRET_KEY = 'test-secret';
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {});
    const truncated = new Response('', { status: 200 });
    vi.spyOn(truncated, 'json').mockRejectedValue(new Error('Unexpected end of JSON input'));
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(truncated));

    const result = await verifyTurnstileToken('token');

    expect(result).toEqual({ ok: false, error: 'turnstile_verification_unavailable' });
    expect((consoleError.mock.calls[0][1] as Error).message).toContain(
      'Unexpected end of JSON input',
    );
  });

  it('never rejects, so the checkout route always reaches its 403 branch', async () => {
    process.env.TURNSTILE_SECRET_KEY = 'test-secret';
    vi.spyOn(console, 'error').mockImplementation(() => {});
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('socket hang up')));

    await expect(verifyTurnstileToken('token')).resolves.toMatchObject({ ok: false });
  });
});
