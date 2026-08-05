import { describe, it, expect, afterEach, vi } from 'vitest';

vi.mock('node:dns/promises', () => ({
  lookup: vi.fn(),
}));

import * as dns from 'node:dns/promises';
import { assertPublicHttpUrl } from '@/lib/ssrf-guard';

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
      'Host does not resolve',
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

    expect(transient).toBe('Host does not resolve');
    expect(transient).toBe(empty);
  });

  it('still blocks hosts that resolve to a private address', async () => {
    vi.mocked(dns.lookup).mockResolvedValue([
      { address: '10.0.3.14', family: 4 },
    ] as never);

    await expect(assertPublicHttpUrl('https://public-looking.example/a.mp3')).rejects.toThrow(
      'Host resolves to a private address',
    );
  });

  it('still allows a genuinely public host', async () => {
    vi.mocked(dns.lookup).mockResolvedValue([
      { address: '93.184.216.34', family: 4 },
    ] as never);

    const url = await assertPublicHttpUrl('https://example.com/a.mp3');

    expect(url.hostname).toBe('example.com');
  });
});
