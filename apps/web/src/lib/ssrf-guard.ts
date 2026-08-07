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
 * The single message every rejection reports to its caller.
 *
 * Callers of this guard sit behind unauthenticated routes and have historically
 * interpolated `err.message` straight into an HTTP response. A message that
 * varies by cause is therefore a DNS oracle: an attacker who can distinguish
 * "does not resolve" from "resolves to a private address" can enumerate
 * internal hostnames one guess at a time, without credentials and without ever
 * completing a fetch. Keeping one constant here makes every rejection
 * indistinguishable from outside (CWE-209).
 */
export const SSRF_REJECTION_MESSAGE = 'URL rejected: not a permitted public http(s) target';

/**
 * Rejection carrying a uniform public `message` and a specific `reason`.
 *
 * `reason` is for server-side logs only — it names the host, the resolved
 * address, or the resolver errno, all of which are exactly what the uniform
 * message exists to withhold. Never return it to a caller.
 */
export class SsrfGuardError extends Error {
  readonly reason: string;

  constructor(reason: string) {
    super(SSRF_REJECTION_MESSAGE);
    this.name = 'SsrfGuardError';
    this.reason = reason;
  }
}

/**
 * True for non-public IP ranges:
 * IPv4 — 10/8, 172.16/12, 192.168/16 (RFC1918), 127/8 (loopback),
 *        169.254/16 (link-local), 100.64/10 (CGNAT, RFC6598),
 *        0/8 (unspecified), >=224 (multicast/reserved).
 * IPv6 — ::1, :: , fe80::/10 (link-local), fc00::/7 (unique-local), and
 *        IPv4-mapped/compatible in ANY spelling (compressed or expanded).
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
    // IPv4-mapped (::ffff:0:0/96) or compatible (::/96) in ANY spelling
    // (compressed, expanded, or dotted) — decode the low 32 bits and re-check.
    if (
      h[0] === 0 && h[1] === 0 && h[2] === 0 && h[3] === 0 && h[4] === 0 &&
      (h[5] === 0xffff || h[5] === 0)
    ) {
      return ipIsPrivate(`${h[6] >> 8}.${h[6] & 0xff}.${h[7] >> 8}.${h[7] & 0xff}`);
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
    throw new SsrfGuardError(`Not a parseable URL: ${input}`);
  }
  if (u.protocol !== 'https:' && u.protocol !== 'http:') {
    throw new SsrfGuardError(`Blocked URL scheme: ${u.protocol}`);
  }
  const host = u.hostname.toLowerCase().replace(/\.$/, '');
  if (BLOCKED_HOSTNAMES.has(host) || host.endsWith('.internal') || host.endsWith('.local')) {
    throw new SsrfGuardError(`Blocked host: ${host}`);
  }
  if (net.isIP(host)) {
    if (ipIsPrivate(host)) throw new SsrfGuardError(`Blocked private IP literal: ${host}`);
    return u;
  }

  // `dns.lookup` rejects with ENOTFOUND/EAI_AGAIN rather than resolving empty,
  // so an uncaught rejection would propagate the resolver's own message
  // (`getaddrinfo ENOTFOUND evil.internal.corp`) to the caller — leaking both
  // the hostname and the resolver's verdict. Catching it here is what makes a
  // non-existent host indistinguishable from a private one.
  //
  // Beyond disclosing system error text, ANY difference between these outcomes
  // is a DNS oracle. "Does not resolve" versus "resolves to a private address"
  // is the sharpest one: it answers, for an unauthenticated caller, whether a
  // guessed internal name EXISTS and points at internal infrastructure. That is
  // precisely the reconnaissance this guard exists to block, so all four
  // outcomes — resolver rejection, transient failure, zero results, and a
  // private result — must be indistinguishable to the caller. The specific
  // cause survives in `SsrfGuardError.reason` for operators.
  //
  // #1381 collapsed these four onto one literal but deliberately left the
  // scheme/blocklist/IP-literal branches distinguishable, on the reasoning that
  // each call site would sanitize. `SsrfGuardError` supersedes that carve-out:
  // every branch now reports the same message from the guard itself, so a call
  // site cannot reintroduce the oracle by forwarding `err.message`.
  let resolved: LookupAddress[];
  try {
    resolved = await dns.lookup(host, { all: true });
  } catch (err) {
    const detail = err instanceof Error ? err.message : String(err);
    console.error('[ssrf-guard] DNS lookup failed:', err);
    throw new SsrfGuardError(`DNS lookup failed for ${host}: ${detail}`);
  }
  if (resolved.length === 0) {
    throw new SsrfGuardError(`DNS lookup returned no addresses for ${host}`);
  }
  for (const r of resolved) {
    if (ipIsPrivate(r.address)) {
      console.error(
        `[ssrf-guard] host resolved to a non-public address: ${host} -> ${r.address}`,
      );
      throw new SsrfGuardError(`Host ${host} resolves to private address ${r.address}`);
    }
  }
  return u;
}
