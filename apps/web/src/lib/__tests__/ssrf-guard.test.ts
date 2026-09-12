import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest';

/**
 * Regression tests for the SSRF guard's DNS oracle (CWE-209).
 *
 * `assertPublicHttpUrl` is reached from `/api/transcribe`, an unauthenticated
 * route that interpolates the guard's message into its response. Before #1381
 * every DNS outcome carried a distinct message, so a caller could tell "this
 * internal hostname does not exist" from "this internal hostname exists and is
 * private" purely by diffing the response body — enumerating internal DNS with
 * no credentials and no completed fetch.
 *
 * #1381 closed that by collapsing all four DNS outcomes onto one constant and
 * logging the real cause server-side. It shipped without tests, so this file is
 * the first coverage this module has had; it pins the property #1381 argued for
 * rather than the incidental wording it chose.
 *
 * The load-bearing assertion is *indistinguishability*. A test that only
 * checked "some static string is returned" would still pass if two branches
 * returned two different static strings — which is the same oracle. So the
 * assertions compare the branches against each other, not against a literal.
 */

// `vi.hoisted` lets the mock factory close over `lookup` without hitting the
// temporal dead zone a plain `const` would, so the module under test can be
// imported statically and keep its types.
const { lookup } = vi.hoisted(() => ({ lookup: vi.fn() }));
vi.mock('node:dns/promises', () => ({ lookup }));

import { assertPublicHttpUrl } from '@/lib/ssrf-guard';

/** Reject and hand back the error, failing loudly if the call unexpectedly resolved. */
async function rejectionOf(url: string): Promise<Error> {
  try {
    await assertPublicHttpUrl(url);
  } catch (err) {
    return err as Error;
  }
  throw new Error(`Expected ${url} to be rejected, but it was allowed`);
}

let errorSpy: ReturnType<typeof vi.spyOn>;

beforeEach(() => {
  lookup.mockReset();
  errorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
});

afterEach(() => {
  errorSpy.mockRestore();
});

/** Everything the guard logged this test, flattened to one searchable string. */
function loggedText(): string {
  return errorSpy.mock.calls
    .map((call: unknown[]) =>
      call.map((arg: unknown) => (arg instanceof Error ? arg.message : String(arg))).join(' ')
    )
    .join('\n');
}

describe('assertPublicHttpUrl — DNS oracle', () => {
  it('reports a non-existent host and a privately-resolving host identically', async () => {
    lookup.mockRejectedValueOnce(
      Object.assign(new Error('getaddrinfo ENOTFOUND vault.corp.example'), { code: 'ENOTFOUND' })
    );
    const missing = await rejectionOf('https://vault.corp.example/x');
    const missingLog = loggedText();

    errorSpy.mockClear();
    lookup.mockResolvedValueOnce([{ address: '10.1.2.3', family: 4 }]);
    const private_ = await rejectionOf('https://vault.corp.example/x');
    const privateLog = loggedText();

    // The oracle: these two must be indistinguishable to the caller.
    expect(missing.message).toBe(private_.message);

    // ...while the operator still gets the distinction server-side. If both
    // branches logged the same thing, the cause would be lost entirely rather
    // than merely moved, so assert the server-side signal actually differs.
    expect(missingLog).not.toBe(privateLog);
    expect(missingLog).toContain('ENOTFOUND');
    expect(privateLog).toContain('10.1.2.3');
  });

  it('gives every DNS outcome the same caller-visible message', async () => {
    // Resolver rejection (NXDOMAIN), transient resolver failure, zero results,
    // and a private result are the four outcomes #1381 set out to merge.
    lookup.mockRejectedValueOnce(
      Object.assign(new Error('getaddrinfo ENOTFOUND a.corp.example'), { code: 'ENOTFOUND' })
    );
    const nxdomain = await rejectionOf('https://a.corp.example/');

    lookup.mockRejectedValueOnce(
      Object.assign(new Error('getaddrinfo EAI_AGAIN b.corp.example'), { code: 'EAI_AGAIN' })
    );
    const transient = await rejectionOf('https://b.corp.example/');

    lookup.mockResolvedValueOnce([]);
    const empty = await rejectionOf('https://c.corp.example/');

    lookup.mockResolvedValueOnce([{ address: '192.168.1.7', family: 4 }]);
    const private_ = await rejectionOf('https://d.corp.example/');

    const messages = new Set(
      [nxdomain, transient, empty, private_].map((err) => err.message)
    );
    expect(messages.size).toBe(1);
  });

  it('keeps the hostname, errno, and resolver text out of the caller-visible message', async () => {
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
    expect(loggedText()).toContain('EAI_AGAIN');
  });

  it('does not leak the resolved private address to the caller', async () => {
    lookup.mockResolvedValueOnce([{ address: '169.254.169.254', family: 4 }]);
    const err = await rejectionOf('https://metadata.example.com/');

    expect(err.message).not.toContain('169.254.169.254');
    expect(loggedText()).toContain('169.254.169.254');
  });
});

describe('assertPublicHttpUrl — the guard still guards', () => {
  it('allows a host that resolves to a public address', async () => {
    // The control: this passes both before and after #1381, which is what makes
    // it a control rather than another oracle assertion.
    lookup.mockResolvedValueOnce([{ address: '93.184.216.34', family: 4 }]);
    const url = await assertPublicHttpUrl('https://example.com/audio.mp3');
    expect(url.hostname).toBe('example.com');
  });

  it('rejects a private address hiding behind an IPv4-mapped IPv6 spelling', async () => {
    lookup.mockResolvedValueOnce([{ address: '0:0:0:0:0:ffff:7f00:1', family: 6 }]);
    const err = await rejectionOf('https://sneaky.example.com/');
    // Pin that resolution is what rejected this, not a pre-DNS branch. The
    // mirror of the `not.toHaveBeenCalled()` assertions below, and load-bearing
    // for the same reason: this PR adds a new pre-DNS branch, so a future change
    // that routed a hostname into it would leave this test throwing, passing,
    // and no longer testing resolution at all.
    expect(lookup).toHaveBeenCalledWith('sneaky.example.com', { all: true });
    expect(loggedText()).toContain('0:0:0:0:0:ffff:7f00:1');
    expect(err).toBeInstanceOf(Error);
  });

  it('rejects when any resolved address is private, even if another is public', async () => {
    lookup.mockResolvedValueOnce([
      { address: '93.184.216.34', family: 4 },
      { address: '10.0.0.5', family: 4 },
    ]);
    await rejectionOf('https://mixed.example.com/');
    expect(lookup).toHaveBeenCalledWith('mixed.example.com', { all: true });
    expect(loggedText()).toContain('10.0.0.5');
  });

  it('rejects a private address in tail position among three answers', async () => {
    // The two-address case above kills a `resolved[0]`-only scan. This one
    // additionally kills a "check a prefix of the answers" bug, and is the only
    // case here that exercises 172.16/12.
    lookup.mockResolvedValueOnce([
      { address: '93.184.216.34', family: 4 },
      { address: '151.101.1.140', family: 4 },
      { address: '172.16.31.9', family: 4 },
    ]);
    await rejectionOf('https://tail.example.com/');
    expect(lookup).toHaveBeenCalledWith('tail.example.com', { all: true });
    expect(loggedText()).toContain('172.16.31.9');
  });

  it('range-checks a bracketed IPv6 literal instead of resolving it', async () => {
    // `URL.hostname` returns `[::1]`, which `net.isIP` rejects. Before the
    // bracket strip, this fell through to `dns.lookup('[::1]')` — blocked only
    // because the resolver errors on a bracketed name, never because the
    // address was recognised as loopback.
    const err = await rejectionOf('http://[::1]/');
    expect(lookup).not.toHaveBeenCalled();
    expect(err.message).toBe('Blocked private IP literal');
  });

  it('allows a public IPv6 literal, which the bracket bug used to reject', async () => {
    const url = await assertPublicHttpUrl('http://[2606:4700:4700::1111]/x');
    expect(lookup).not.toHaveBeenCalled();
    expect(url.hostname).toBe('[2606:4700:4700::1111]');
  });

  it('rejects pre-DNS causes without consulting the resolver', async () => {
    // Scheme, blocklisted host, and IP-literal rejections are decided from the
    // caller's own input, so they must not reach `dns.lookup` at all.
    for (const url of [
      'not-a-url',
      'file:///etc/passwd',
      'http://localhost/',
      'http://metadata.google.internal/',
      'http://box.internal/',
      'http://box.local/',
      'http://127.0.0.1/',
      'http://169.254.169.254/',
      'http://[::1]/',
    ]) {
      await rejectionOf(url);
    }
    expect(lookup).not.toHaveBeenCalled();
  });

  it('rejects public IPv6 literals that encode a private IPv4 destination', async () => {
    // Routing IPv6 literals into `ipIsPrivate` (the bracket fix above) exposed
    // that its IPv6 branch ends in `return false` for anything it does not
    // recognise. The transition prefixes below are *syntactically* public but
    // carry an IPv4 destination in their bits, so a NAT64/6to4-capable egress
    // path resolves them to the embedded address — 169.254.169.254 in each of
    // these cases. Flagged by CodeRabbit on #1486.
    //
    // 0xa9fe = 169.254, so a9fe:a9fe is 169.254.169.254.
    for (const url of [
      'http://[64:ff9b::a9fe:a9fe]/', // well-known NAT64, /96
      'http://[64:ff9b:1::1]/', // RFC 8215 local-use NAT64
      'http://[2002:a9fe:a9fe::]/', // 6to4
      'http://[::ffff:0:a9fe:a9fe]/', // IPv4-translated, ::ffff:0:0:0/96
      'http://[fec0::1]/', // site-local
      'http://[100::1]/', // discard-only
      'http://[2002:0a00:0005::]/', // 6to4 carrying 10.0.0.5
      'http://[64:ff9b::7f00:1]/', // NAT64 carrying 127.0.0.1
    ]) {
      const err = await rejectionOf(url);
      expect(err.message, `${url} must be rejected`).toBe('Blocked private IP literal');
    }
    expect(lookup).not.toHaveBeenCalled();
  });

  it('still allows transition-prefix literals that encode a public IPv4', async () => {
    // The controls. Without these, the test above would pass just as well if
    // the guard blocked every NAT64 and 6to4 address outright — which would be
    // over-blocking dressed up as a fix. 0x5db8d822 is 93.184.216.34.
    for (const url of ['http://[64:ff9b::5db8:d822]/', 'http://[2002:5db8:d822::]/']) {
      const parsed = await assertPublicHttpUrl(url);
      expect(parsed.protocol).toBe('http:');
    }
    expect(lookup).not.toHaveBeenCalled();
  });

  it('applies the same transition-prefix checks to resolved addresses', async () => {
    // `ipIsPrivate` guards both paths, so a hostname that *resolves* to a NAT64
    // address must be refused too — otherwise the literal fix just moves the
    // bypass one DNS lookup away.
    lookup.mockResolvedValueOnce([{ address: '64:ff9b::a9fe:a9fe', family: 6 }]);
    await rejectionOf('https://nat64.example.com/');
    expect(lookup).toHaveBeenCalledWith('nat64.example.com', { all: true });
    expect(loggedText()).toContain('64:ff9b::a9fe:a9fe');
  });

  it('keeps the IP-literal rejection distinct from the DNS one, by design', async () => {
    // #1381 deliberately did NOT merge this branch into the DNS message: the
    // caller supplied the address, so naming it private reveals nothing they
    // did not already know, and no hostname is confirmed or denied. #1428
    // proposed collapsing all six paths onto one constant instead. This pins
    // the merged decision so a future uniformity pass has to change a failing
    // test — and read this comment — rather than silently flip it.
    lookup.mockResolvedValueOnce([{ address: '10.0.0.9', family: 4 }]);
    const viaDns = await rejectionOf('https://private.example.com/');
    const viaLiteral = await rejectionOf('http://10.0.0.9/');

    expect(viaLiteral.message).not.toBe(viaDns.message);
  });
});
