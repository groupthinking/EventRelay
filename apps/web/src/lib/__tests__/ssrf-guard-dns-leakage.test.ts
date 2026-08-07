import { describe, it, expect, afterEach, vi } from 'vitest';

vi.mock('node:dns/promises', () => ({
  lookup: vi.fn(),
}));

import * as dns from 'node:dns/promises';
import { assertPublicHttpUrl, SSRF_REJECTION_MESSAGE } from '@/lib/ssrf-guard';

afterEach(() => {
  vi.restoreAllMocks();
  vi.mocked(dns.lookup).mockReset();
});

/**
 * `assertPublicHttpUrl` throws app-authored literals everywhere except the
 * `dns.lookup` await, which rejects with Node resolver text embedding the
 * caller's own hostname. `fetchTranscript` interpolates that into
 * `Rejected audioUrl: ${guardErr.message}` and `/api/transcribe` returns it
 * verbatim in its 503 — so a resolver reason reaching the caller is both
 * system-error disclosure and a DNS oracle over the server's network position.
 */
describe('assertPublicHttpUrl DNS failure leakage', () => {
  const PROBED_HOST = 'vault.internal-corp.example';

  it('does not surface resolver text when the lookup rejects', async () => {
    const resolverError = Object.assign(
      new Error(`getaddrinfo ENOTFOUND ${PROBED_HOST}`),
      { code: 'ENOTFOUND', syscall: 'getaddrinfo', hostname: PROBED_HOST },
    );
    vi.mocked(dns.lookup).mockRejectedValue(resolverError);
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {});

    await expect(assertPublicHttpUrl(`https://${PROBED_HOST}/clip.mp3`)).rejects.toThrow(
      SSRF_REJECTION_MESSAGE,
    );

    const thrown = await assertPublicHttpUrl(`https://${PROBED_HOST}/clip.mp3`).catch(
      (e: unknown) => (e as Error).message,
    );
    for (const token of ['getaddrinfo', 'ENOTFOUND', PROBED_HOST]) {
      expect(thrown).not.toContain(token);
    }

    // Suppressed for the caller, retained for operators.
    expect(JSON.stringify(consoleError.mock.calls)).toContain('ENOTFOUND');
  });

  it('is indistinguishable from a transient resolver failure', async () => {
    // ENOTFOUND vs EAI_AGAIN would tell a caller whether the name exists but is
    // merely unreachable — the oracle. Both must collapse to one message.
    vi.mocked(dns.lookup).mockRejectedValue(
      Object.assign(new Error(`getaddrinfo EAI_AGAIN ${PROBED_HOST}`), { code: 'EAI_AGAIN' }),
    );
    vi.spyOn(console, 'error').mockImplementation(() => {});

    const transient = await assertPublicHttpUrl(`https://${PROBED_HOST}/a.mp3`).catch(
      (e: unknown) => (e as Error).message,
    );

    vi.mocked(dns.lookup).mockResolvedValue([] as never);
    const empty = await assertPublicHttpUrl(`https://${PROBED_HOST}/a.mp3`).catch(
      (e: unknown) => (e as Error).message,
    );

    expect(transient).toBe(SSRF_REJECTION_MESSAGE);
    expect(transient).toBe(empty);
  });

  it('still blocks hosts that resolve to a private address', async () => {
    vi.mocked(dns.lookup).mockResolvedValue([
      { address: '10.0.3.14', family: 4 },
    ] as never);
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {});

    const message = await assertPublicHttpUrl('https://public-looking.example/a.mp3').catch(
      (e: unknown) => (e as Error).message,
    );

    expect(message).toBe(SSRF_REJECTION_MESSAGE);
    // The resolved private address must not ride out on the rejection…
    expect(message).not.toContain('10.0.3.14');
    expect(message).not.toContain('private');
    // …but operators still get it.
    expect(JSON.stringify(consoleError.mock.calls)).toContain('10.0.3.14');
  });

  /**
   * The sharpest oracle of the set: a caller who can tell "this name does not
   * exist" from "this name exists and points somewhere internal" can enumerate
   * internal hostnames through an unauthenticated endpoint, which is the
   * reconnaissance the guard exists to prevent. Every outcome that is not a
   * public address must be one indistinguishable message.
   */
  it('does not reveal whether a probed internal name exists', async () => {
    vi.spyOn(console, 'error').mockImplementation(() => {});

    // A name that does not exist at all.
    vi.mocked(dns.lookup).mockRejectedValue(
      Object.assign(new Error(`getaddrinfo ENOTFOUND ${PROBED_HOST}`), { code: 'ENOTFOUND' }),
    );
    const absent = await assertPublicHttpUrl(`https://${PROBED_HOST}/a.mp3`).catch(
      (e: unknown) => (e as Error).message,
    );

    // A name that DOES exist and points at internal infrastructure.
    vi.mocked(dns.lookup).mockResolvedValue([
      { address: '10.0.3.14', family: 4 },
    ] as never);
    const present = await assertPublicHttpUrl(`https://${PROBED_HOST}/a.mp3`).catch(
      (e: unknown) => (e as Error).message,
    );

    expect(present).toBe(absent);
  });

  it('still allows a genuinely public host', async () => {
    vi.mocked(dns.lookup).mockResolvedValue([
      { address: '93.184.216.34', family: 4 },
    ] as never);

    const url = await assertPublicHttpUrl('https://example.com/a.mp3');

    expect(url.hostname).toBe('example.com');
  });
});
