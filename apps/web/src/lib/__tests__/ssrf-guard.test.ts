import { describe, expect, it, vi, beforeEach } from 'vitest';

/**
 * Regression tests for the SSRF guard's DNS oracle (CWE-209).
 *
 * The guard is reached from `/api/transcribe`, an unauthenticated route that
 * returns `result.error` verbatim. Before this change every rejection carried a
 * distinct message, so a caller could tell "this internal hostname does not
 * exist" from "this internal hostname exists and is private" purely by diffing
 * the response body — enumerating internal DNS without credentials.
 *
 * The load-bearing assertion here is therefore *indistinguishability*: the
 * caller-visible message must be byte-identical across causes. Asserting only
 * that some static string is returned would pass even if the two branches
 * returned two different static strings, which is the same oracle.
 */

// `vi.hoisted` lets the mock factory close over `lookup` without hitting the
// temporal dead zone that a plain `const` would, so the module under test can
// be imported statically and keep its types.
const { lookup } = vi.hoisted(() => ({ lookup: vi.fn() }));
vi.mock('node:dns/promises', () => ({ lookup }));

import { assertPublicHttpUrl, SsrfGuardError, SSRF_REJECTION_MESSAGE } from '@/lib/ssrf-guard';

/** Reject and hand back the error, failing loudly if the call unexpectedly resolved. */
async function rejectionOf(url: string): Promise<SsrfGuardError> {
  try {
    await assertPublicHttpUrl(url);
  } catch (err) {
    return err as SsrfGuardError;
  }
  throw new Error(`Expected ${url} to be rejected, but it was allowed`);
}

beforeEach(() => {
  lookup.mockReset();
});

describe('assertPublicHttpUrl — DNS oracle', () => {
  it('reports a non-existent host and a private host identically', async () => {
    const enotfound = Object.assign(new Error('getaddrinfo ENOTFOUND vault.corp.example'), {
      code: 'ENOTFOUND',
    });
    lookup.mockRejectedValueOnce(enotfound);
    const missing = await rejectionOf('https://vault.corp.example/x');

    lookup.mockResolvedValueOnce([{ address: '10.1.2.3', family: 4 }]);
    const private_ = await rejectionOf('https://vault.corp.example/x');

    // The oracle: these two must be indistinguishable to the caller.
    expect(missing.message).toBe(private_.message);
    expect(missing.message).toBe(SSRF_REJECTION_MESSAGE);

    // ...while the operator still gets the distinction server-side.
    expect(missing.reason).not.toBe(private_.reason);
    expect(missing.reason).toContain('ENOTFOUND');
    expect(private_.reason).toContain('10.1.2.3');
  });

  it('keeps the hostname and resolver errno out of the caller-visible message', async () => {
    lookup.mockRejectedValueOnce(
      Object.assign(new Error('getaddrinfo EAI_AGAIN jenkins.internal.corp'), {
        code: 'EAI_AGAIN',
      })
    );
    const err = await rejectionOf('https://jenkins.internal.corp/');

    expect(err.message).not.toContain('jenkins');
    expect(err.message).not.toContain('EAI_AGAIN');
    expect(err.message).not.toContain('getaddrinfo');
    // Suppressed for the caller, retained for the operator.
    expect(err.reason).toContain('jenkins.internal.corp');
    expect(err.reason).toContain('EAI_AGAIN');
  });

  it('does not leak the resolved private address to the caller', async () => {
    lookup.mockResolvedValueOnce([{ address: '169.254.169.254', family: 4 }]);
    const err = await rejectionOf('https://metadata.example.com/');

    expect(err.message).not.toContain('169.254.169.254');
    expect(err.reason).toContain('169.254.169.254');
  });

  it('gives every rejection cause the same caller-visible message', async () => {
    lookup.mockResolvedValue([{ address: '10.0.0.1', family: 4 }]);

    const rejections = await Promise.all(
      [
        'not-a-url',
        'file:///etc/passwd',
        'http://localhost/',
        'http://metadata.google.internal/',
        'http://box.internal/',
        'http://box.local/',
        'http://127.0.0.1/',
        'http://169.254.169.254/',
        'http://[::1]/',
        'https://resolves-privately.example.com/',
      ].map(rejectionOf)
    );

    const messages = new Set(rejections.map((r) => r.message));
    expect(messages).toEqual(new Set([SSRF_REJECTION_MESSAGE]));

    // Every one is still an SsrfGuardError carrying a distinct diagnostic.
    expect(rejections.every((r) => r instanceof SsrfGuardError)).toBe(true);
    expect(new Set(rejections.map((r) => r.reason)).size).toBe(rejections.length);
  });
});

describe('assertPublicHttpUrl — the guard still guards', () => {
  it('allows a host that resolves to a public address', async () => {
    lookup.mockResolvedValueOnce([{ address: '93.184.216.34', family: 4 }]);
    const url = await assertPublicHttpUrl('https://example.com/audio.mp3');
    expect(url.hostname).toBe('example.com');
  });

  it('rejects a private address hiding behind an IPv4-mapped IPv6 spelling', async () => {
    lookup.mockResolvedValueOnce([{ address: '0:0:0:0:0:ffff:7f00:1', family: 6 }]);
    const err = await rejectionOf('https://sneaky.example.com/');
    expect(err.reason).toContain('resolves to private address');
  });

  it('rejects when any resolved address is private, even if another is public', async () => {
    lookup.mockResolvedValueOnce([
      { address: '93.184.216.34', family: 4 },
      { address: '10.0.0.5', family: 4 },
    ]);
    const err = await rejectionOf('https://mixed.example.com/');
    expect(err.reason).toContain('10.0.0.5');
  });
});
