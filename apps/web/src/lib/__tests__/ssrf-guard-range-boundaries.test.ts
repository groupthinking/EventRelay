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
 * Boundary coverage for the IPv6 range checks in `ipIsPrivate`.
 *
 * `ssrf-guard.test.ts` establishes that each blocked range *is* blocked — it
 * walks NAT64, 6to4, IPv4-translated, site-local and discard with an address
 * squarely inside each. That is the "too narrow" direction: a check that missed
 * would let an address through.
 *
 * Nothing yet holds the other direction. `fec0::/10` and `100::/64` are the two
 * checks written as bit masks rather than exact matches, and a mask that is too
 * *wide* fails silently in the opposite way — it refuses public space, and the
 * only symptom is a legitimate fetch being rejected with the same uniform
 * message every other rejection uses. Neither edge of either mask is pinned
 * today, so widening one would break no test.
 *
 * Each range therefore gets both edges plus a just-outside neighbour.
 */
describe('assertPublicHttpUrl IPv6 range boundaries', () => {
  const rejectionOf = async (url: string): Promise<Error> => {
    vi.spyOn(console, 'error').mockImplementation(() => {});
    try {
      await assertPublicHttpUrl(url);
    } catch (err) {
      // `catch` binds as `unknown`; narrow rather than assert, so a non-Error
      // throw surfaces as itself instead of being mistyped as an Error and
      // failing later on a missing `.message`.
      if (err instanceof Error) return err;
      throw err;
    }
    throw new Error(`${url} was expected to be rejected, but was allowed`);
  };

  describe('fec0::/10 site-local', () => {
    it.each([
      ['fec0::', 'first address in the range'],
      ['feff:ffff:ffff:ffff:ffff:ffff:ffff:ffff', 'last address in the range'],
    ])('rejects [%s] (%s)', async (address) => {
      const err = await rejectionOf(`http://[${address}]/`);

      expect(err.message).toBe('Blocked private IP literal');
    });

    /**
     * `fe00::1` sits below `fec0::/10` and is not caught by `fe80::/10` either,
     * so it lands in the gap between the two masks. If the site-local check were
     * widened to `fe00::/8` — an easy slip, since both start `fe` — this is the
     * address that would start being refused.
     */
    it('still allows [fe00::1], which is below the range', async () => {
      const url = await assertPublicHttpUrl('http://[fe00::1]/');

      expect(url.hostname).toBe('[fe00::1]');
      expect(dns.lookup).not.toHaveBeenCalled();
    });
  });

  describe('100::/64 discard', () => {
    it.each([
      ['100::', 'first address in the range'],
      ['100:0:0:0:ffff:ffff:ffff:ffff', 'last address in the range'],
    ])('rejects [%s] (%s)', async (address) => {
      const err = await rejectionOf(`http://[${address}]/`);

      expect(err.message).toBe('Blocked private IP literal');
    });

    /**
     * The discard prefix is a /64, not a /16 or /32. Both of these share the
     * leading `100` hextet and would be refused if the check tested only `h[0]`.
     */
    it.each([
      ['100:0:0:1::1', 'inside 100::/16 but outside the /64'],
      ['101::1', 'adjacent prefix'],
    ])('still allows [%s] (%s)', async (address) => {
      const url = await assertPublicHttpUrl(`http://[${address}]/`);

      expect(url.hostname).toBe(`[${address}]`);
    });
  });

  /**
   * `ipv6ToHextets` folds a trailing dotted quad into two hextets before any
   * range check runs, so the dotted spelling of a NAT64 address has to reach the
   * same verdict as the hex one. `ssrf-guard.test.ts` covers
   * `64:ff9b::a9fe:a9fe`; this is the same destination written the other way.
   */
  it('rejects the dotted-quad spelling of a NAT64 address', async () => {
    const err = await rejectionOf('http://[64:ff9b::169.254.169.254]/');

    expect(err.message).toBe('Blocked private IP literal');
  });

  /**
   * The same boundaries via DNS answers rather than URL literals. The two paths
   * reach `ipIsPrivate` through different branches of `assertPublicHttpUrl` and
   * report different messages, so a regression could land on one and not the
   * other.
   */
  describe('applied to resolved addresses', () => {
    it('rejects a site-local answer at the top of the range', async () => {
      vi.mocked(dns.lookup).mockResolvedValue([{ address: 'feff::1', family: 6 }] as never);
      vi.spyOn(console, 'error').mockImplementation(() => {});

      await expect(assertPublicHttpUrl('https://edge.example/a.mp3')).rejects.toThrow(
        'Host does not resolve to a public address',
      );
    });

    it('still allows an answer just outside the discard prefix', async () => {
      vi.mocked(dns.lookup).mockResolvedValue([{ address: '101::1', family: 6 }] as never);

      const url = await assertPublicHttpUrl('https://edgeok.example/a.mp3');

      expect(url.hostname).toBe('edgeok.example');
    });
  });
});
