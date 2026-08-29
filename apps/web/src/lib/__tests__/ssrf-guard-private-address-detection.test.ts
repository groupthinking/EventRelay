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
 * Companion to `ssrf-guard-dns-leakage.test.ts`, which covers what a rejection
 * *says*. This file covers which resolved answers are rejected at all.
 *
 * The distinction matters because the leakage fix made every non-public outcome
 * report one identical message. That is correct for disclosure, and it also
 * means a detection regression no longer looks any different from a working
 * rejection — "blocked" and "blocked for the wrong reason" are now the same
 * string. The two answers below are the ones where `ipIsPrivate` does real work
 * beyond a plain RFC1918 compare, so they are where a silent regression would
 * hide.
 */
describe('assertPublicHttpUrl private-address detection', () => {
  const NOT_PUBLIC = 'Host does not resolve to a public address';

  /**
   * `net.isIPv4('0:0:0:0:0:ffff:7f00:1')` is false, so the IPv4 branch never
   * sees this. Only the hextet expansion catches that the low 32 bits decode to
   * 127.0.0.1. A resolver is free to return this fully-expanded spelling rather
   * than `::ffff:127.0.0.1`, so the guard cannot rely on the compressed form.
   */
  it('rejects loopback hiding behind an expanded IPv4-mapped IPv6 answer', async () => {
    vi.mocked(dns.lookup).mockResolvedValue([
      { address: '0:0:0:0:0:ffff:7f00:1', family: 6 },
    ] as never);
    vi.spyOn(console, 'error').mockImplementation(() => {});

    await expect(assertPublicHttpUrl('https://mapped.example/a.mp3')).rejects.toThrow(NOT_PUBLIC);
  });

  /**
   * A genuinely public IPv6 answer must still pass, otherwise the test above
   * would be satisfied by a guard that simply rejected all IPv6.
   */
  it('still allows a genuine public IPv6 answer', async () => {
    vi.mocked(dns.lookup).mockResolvedValue([
      { address: '2606:2800:220:1:248:1893:25c8:1946', family: 6 },
    ] as never);

    const url = await assertPublicHttpUrl('https://v6.example/a.mp3');

    expect(url.hostname).toBe('v6.example');
  });

  /**
   * DNS rebinding's cheap cousin: return one public address alongside a private
   * one and hope the guard checks only the first. Every answer has to clear the
   * check, not just `resolved[0]`.
   */
  it('rejects when any answer is private, even if a public one comes first', async () => {
    vi.mocked(dns.lookup).mockResolvedValue([
      { address: '93.184.216.34', family: 4 },
      { address: '10.0.0.5', family: 4 },
    ] as never);
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {});

    await expect(assertPublicHttpUrl('https://mixed.example/a.mp3')).rejects.toThrow(NOT_PUBLIC);
    // The offending address is the one an operator needs; confirm it is logged
    // rather than merely absent from the response.
    expect(JSON.stringify(consoleError.mock.calls)).toContain('10.0.0.5');
  });
});
