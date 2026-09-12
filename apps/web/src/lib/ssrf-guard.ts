import 'server-only';

/**
 * SSRF guard for server-side fetches of user-supplied URLs.
 *
 * Rejects non-http(s) schemes and any host that resolves to a private,
 * loopback, link-local, CGNAT, or cloud-metadata address (e.g. 169.254.169.254).
 *
 * Note: this resolves DNS and checks the result, which closes the common SSRF
 * cases. It does not fully defeat DNS-rebinding (a TOCTOU gap between this check
 * and the actual fetch); for that, pin the resolved IP and fetch by IP with a
 * Host header. This is a strong, low-cost first line of defense.
 */
import * as dns from 'node:dns/promises';
import type { LookupAddress } from 'node:dns';
import * as net from 'node:net';

const BLOCKED_HOSTNAMES = new Set(['localhost', 'metadata.google.internal']);

/**
 * True for non-public IP ranges:
 * IPv4 — 10/8, 172.16/12, 192.168/16 (RFC1918), 127/8 (loopback),
 *        169.254/16 (link-local), 100.64/10 (CGNAT, RFC6598),
 *        0/8 (unspecified), >=224 (multicast/reserved).
 * IPv6 — ::1, :: , fe80::/10 (link-local), fc00::/7 (unique-local),
 *        fec0::/10 (site-local), 100::/64 (discard), and every form that
 *        encodes an IPv4 destination: IPv4-mapped/compatible in ANY spelling
 *        (compressed, expanded, or dotted), IPv4-translated (::ffff:0:0:0/96),
 *        NAT64 (64:ff9b::/96) and 6to4 (2002::/16) — each decoded and
 *        re-checked against the IPv4 rules above.
 *
 * The embedded-IPv4 forms matter because they are syntactically public: a
 * NAT64- or 6to4-capable egress path translates them to the address they
 * carry, so `64:ff9b::a9fe:a9fe` reaches 169.254.169.254. Anything not matched
 * here is treated as genuine public IPv6, so a new transition prefix must be
 * added explicitly rather than inheriting a safe default.
 */
function ipIsPrivate(ip: string): boolean {
  if (net.isIPv4(ip)) {
    const p = ip.split('.').map(Number);
    return (
      p[0] === 10 ||
      (p[0] === 172 && p[1] >= 16 && p[1] <= 31) ||
      (p[0] === 192 && p[1] === 168) ||
      (p[0] === 100 && p[1] >= 64 && p[1] <= 127) || // CGNAT 100.64.0.0/10
      p[0] === 127 ||
      (p[0] === 169 && p[1] === 254) ||
      p[0] === 0 ||
      p[0] >= 224
    );
  }
  if (net.isIPv6(ip)) {
    const h = ipv6ToHextets(ip);
    if (!h) return true; // valid IPv6 we can't parse → fail closed
    if (h.every((x) => x === 0)) return true; // :: (unspecified)
    if (h.slice(0, 7).every((x) => x === 0) && h[7] === 1) return true; // ::1 loopback
    if ((h[0] & 0xffc0) === 0xfe80) return true; // fe80::/10 link-local
    if ((h[0] & 0xfe00) === 0xfc00) return true; // fc00::/7 unique-local
    if ((h[0] & 0xffc0) === 0xfec0) return true; // fec0::/10 site-local (deprecated)
    if (h[0] === 0x0100 && h[1] === 0 && h[2] === 0 && h[3] === 0) return true; // 100::/64 discard

    // The low 32 bits as dotted IPv4, for the transition forms that carry one.
    const lowV4 = () => `${h[6] >> 8}.${h[6] & 0xff}.${h[7] >> 8}.${h[7] & 0xff}`;

    // IPv4-mapped (::ffff:0:0/96) or compatible (::/96) in ANY spelling
    // (compressed, expanded, or dotted) — decode the low 32 bits and re-check.
    if (
      h[0] === 0 && h[1] === 0 && h[2] === 0 && h[3] === 0 && h[4] === 0 &&
      (h[5] === 0xffff || h[5] === 0)
    ) {
      return ipIsPrivate(lowV4());
    }
    // IPv4-translated, ::ffff:0:0:0/96 (RFC 6052) — note h[4], not h[5], holds
    // the 0xffff, so the mapped/compatible test above does not cover it.
    if (h[0] === 0 && h[1] === 0 && h[2] === 0 && h[3] === 0 && h[4] === 0xffff && h[5] === 0) {
      return ipIsPrivate(lowV4());
    }
    // 64:ff9b::/96 — the well-known NAT64 prefix. A NAT64-capable egress path
    // translates these to the embedded IPv4, so `64:ff9b::a9fe:a9fe` reaches
    // 169.254.169.254. Match the exact /96 (h[2]..h[5] zero) before decoding:
    // testing only h[0]/h[1] would be 64:ff9b::/32, a wider claim than the low
    // 32 bits being an IPv4 address. Anything else in that /32 — e.g. the
    // RFC 8215 local-use 64:ff9b:1::/48 — is local-use by definition, so block
    // it outright rather than guess where its embedded IPv4 sits.
    if (h[0] === 0x0064 && h[1] === 0xff9b) {
      if (h[2] === 0 && h[3] === 0 && h[4] === 0 && h[5] === 0) return ipIsPrivate(lowV4());
      return true;
    }
    // 2002::/16 — 6to4, which carries its IPv4 in the next 32 bits (h[1], h[2])
    // rather than the low ones.
    if (h[0] === 0x2002) {
      return ipIsPrivate(`${h[1] >> 8}.${h[1] & 0xff}.${h[2] >> 8}.${h[2] & 0xff}`);
    }
    return false; // genuine public IPv6
  }
  return true; // unknown form → block
}

/**
 * Expand an IPv6 literal to its 8 hextets (numbers), resolving `::` zero
 * compression and folding any embedded IPv4 (e.g. `::ffff:1.2.3.4`). Returns
 * null if the input can't be parsed. This lets the private-range checks operate
 * on a canonical form regardless of how the literal was spelled, so expanded
 * IPv4-mapped forms like `0:0:0:0:0:ffff:7f00:1` can't slip past.
 */
function ipv6ToHextets(input: string): number[] | null {
  let s = input.toLowerCase();
  const zone = s.indexOf('%');
  if (zone !== -1) s = s.slice(0, zone);

  // Fold a trailing embedded IPv4 (a.b.c.d) into two hex groups.
  const v4 = s.match(/^(.*:)(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$/);
  if (v4) {
    const o = [v4[2], v4[3], v4[4], v4[5]].map(Number);
    if (o.some((n) => n > 255)) return null;
    s = `${v4[1]}${((o[0] << 8) | o[1]).toString(16)}:${((o[2] << 8) | o[3]).toString(16)}`;
  }

  const halves = s.split('::');
  if (halves.length > 2) return null;
  const left = halves[0] ? halves[0].split(':') : [];
  const right = halves.length === 2 ? (halves[1] ? halves[1].split(':') : []) : null;

  let groups: string[];
  if (right === null) {
    groups = left;
  } else {
    const missing = 8 - (left.length + right.length);
    if (missing < 1) return null;
    groups = [...left, ...new Array(missing).fill('0'), ...right];
  }
  if (groups.length !== 8) return null;

  const hextets = groups.map((g) => (/^[0-9a-f]{1,4}$/.test(g) ? parseInt(g, 16) : NaN));
  return hextets.some((x) => Number.isNaN(x)) ? null : hextets;
}

/**
 * Throws if `input` is not a public http(s) URL. Returns the parsed URL.
 */
export async function assertPublicHttpUrl(input: string): Promise<URL> {
  let u: URL;
  try {
    u = new URL(input);
  } catch {
    throw new Error('Invalid URL');
  }
  if (u.protocol !== 'https:' && u.protocol !== 'http:') {
    throw new Error(`Blocked URL scheme: ${u.protocol}`);
  }
  const host = u.hostname.toLowerCase().replace(/\.$/, '');
  if (BLOCKED_HOSTNAMES.has(host) || host.endsWith('.internal') || host.endsWith('.local')) {
    throw new Error('Blocked host');
  }
  // `URL.hostname` keeps the brackets on an IPv6 literal — `http://[::1]/`
  // yields `[::1]` — and `net.isIP` does not accept that spelling. Without
  // stripping them, every IPv6 literal skipped this branch and was handed to
  // `dns.lookup` instead, so `ipIsPrivate` never saw it. That failed closed
  // only by accident (the resolver errors on a bracketed name, which the DNS
  // branch below turns into a rejection); it also rejected *public* IPv6
  // literals, which this guard is meant to allow.
  const literal = host.startsWith('[') && host.endsWith(']') ? host.slice(1, -1) : host;
  if (net.isIP(literal)) {
    if (ipIsPrivate(literal)) throw new Error('Blocked private IP literal');
    return u;
  }
  // Every other throw here is an app-authored literal, but `dns.lookup` rejects
  // with Node resolver text that embeds the caller's own hostname — e.g.
  // `getaddrinfo ENOTFOUND evil.internal.corp`. `fetchTranscript` interpolates
  // that message into `Rejected audioUrl: ${guardErr.message}`, which the
  // transcribe route returns verbatim, so the reject reason would reach the
  // client.
  //
  // Beyond disclosing system error text, ANY difference between these outcomes
  // is a DNS oracle. "Does not resolve" versus "resolves to a private address"
  // is the sharpest one: it answers, for an unauthenticated caller, whether a
  // guessed internal name EXISTS and points at internal infrastructure. That is
  // precisely the reconnaissance this guard exists to block, so all four
  // outcomes — resolver rejection, transient failure, zero results, and a
  // private result — must be indistinguishable to the caller. The real reason
  // is logged for operators instead.
  //
  // The IP-literal branch above keeps its own message deliberately: the caller
  // supplied the address, so telling them it is private reveals nothing they
  // did not already know, and no name is confirmed or denied.
  const NOT_PUBLIC = 'Host does not resolve to a public address';
  let resolved: LookupAddress[];
  try {
    resolved = await dns.lookup(host, { all: true });
  } catch (err) {
    console.error('[ssrf-guard] DNS lookup failed:', err);
    throw new Error(NOT_PUBLIC);
  }
  if (resolved.length === 0) throw new Error(NOT_PUBLIC);
  for (const r of resolved) {
    if (ipIsPrivate(r.address)) {
      console.error(
        `[ssrf-guard] host resolved to a non-public address: ${host} -> ${r.address}`,
      );
      throw new Error(NOT_PUBLIC);
    }
  }
  return u;
}
