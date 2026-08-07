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
 * Detection-robustness coverage for `assertPublicHttpUrl`, distinct from
 * `ssrf-guard-dns-leakage.test.ts`.
 *
 * That file asks whether a rejection *tells the caller too much*. These ask the
 * prior question: does the guard reject at all? Both cases below are ways a
 * private destination can survive a resolution that looks public at a glance —
 * one hides the address inside an alternate IPv6 spelling, the other hides it
 * behind a public sibling record. Neither is exercised anywhere else, and both
 * are silent failures if they regress: the guard would return a URL and the
 * caller would fetch it.
 *
 * Salvaged from #1428, whose CWE-209 fix was superseded by #1381 (feae3d3) but
 * whose detection cases were not carried over. Ported to the merged API, where
 * every DNS-path rejection is the single `NOT_PUBLIC` literal.
 */
const NOT_PUBLIC = 'Host does not resolve to a public address';

describe('assertPublicHttpUrl resolution bypasses', () => {
  it('rejects a loopback address written in expanded IPv4-mapped IPv6 form', async () => {
    // `0:0:0:0:0:ffff:7f00:1` is 127.0.0.1 spelled without `::` compression and
    // without dotted-quad notation. A check that pattern-matched `::ffff:` or
    // looked for dots would pass it straight through to a fetch of localhost.
    vi.mocked(dns.lookup).mockResolvedValue([
      { address: '0:0:0:0:0:ffff:7f00:1', family: 6 },
    ] as never);

    await expect(assertPublicHttpUrl('https://sneaky.example.com/a.mp3')).rejects.toThrow(
      NOT_PUBLIC,
    );
  });

  it('rejects when any resolved address is private, even if another is public', async () => {
    // Multi-record DNS: the guard must scan every answer, not just the first.
    // Returning after one public hit would let an attacker pair a real public A
    // record with an internal one and win whichever the fetch layer picks.
    vi.mocked(dns.lookup).mockResolvedValue([
      { address: '93.184.216.34', family: 4 },
      { address: '10.0.0.5', family: 4 },
    ] as never);

    await expect(assertPublicHttpUrl('https://mixed.example.com/a.mp3')).rejects.toThrow(
      NOT_PUBLIC,
    );
  });

  it('rejects a private address that appears after several public ones', async () => {
    // Guards against an off-by-one or early-exit that only inspects a prefix of
    // the answer set.
    vi.mocked(dns.lookup).mockResolvedValue([
      { address: '93.184.216.34', family: 4 },
      { address: '151.101.1.140', family: 4 },
      { address: '172.16.31.9', family: 4 },
    ] as never);

    await expect(assertPublicHttpUrl('https://tail.example.com/a.mp3')).rejects.toThrow(
      NOT_PUBLIC,
    );
  });

  it('still allows a host whose answers are all public', async () => {
    // The control: without it, a guard that rejected everything would pass the
    // three assertions above.
    vi.mocked(dns.lookup).mockResolvedValue([
      { address: '93.184.216.34', family: 4 },
      { address: '151.101.1.140', family: 4 },
    ] as never);

    const url = await assertPublicHttpUrl('https://public.example.com/a.mp3');

    expect(url.hostname).toBe('public.example.com');
  });
});
