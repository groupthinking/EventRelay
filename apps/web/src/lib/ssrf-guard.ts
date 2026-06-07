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
import * as net from 'node:net';

const BLOCKED_HOSTNAMES = new Set(['localhost', 'metadata.google.internal']);

/**
 * True for non-public IP ranges:
 * IPv4 — 10/8, 172.16/12, 192.168/16 (RFC1918), 127/8 (loopback),
 *        169.254/16 (link-local), 100.64/10 (CGNAT, RFC6598),
 *        0/8 (unspecified), >=224 (multicast/reserved).
 * IPv6 — ::1, :: , fe80::/10 (link-local), fc00::/7 (unique-local),
 *        and IPv4-mapped (::ffff:a.b.c.d).
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
    const lc = ip.toLowerCase();
    if (lc === '::1' || lc === '::') return true;
    if (/^fe[89ab]/.test(lc)) return true; // fe80::/10 link-local
    if (/^f[cd]/.test(lc)) return true; // fc00::/7 unique-local
    // Any trailing dotted-quad: IPv4-mapped (::ffff:1.2.3.4) or compatible (::1.2.3.4).
    const dotted = lc.match(/:(\d{1,3}(?:\.\d{1,3}){3})$/);
    if (dotted) return ipIsPrivate(dotted[1]);
    // IPv4-mapped hex form (::ffff:7f00:1 === 127.0.0.1) — decode hextets to octets.
    const hex = lc.match(/::ffff:([0-9a-f]{1,4}):([0-9a-f]{1,4})$/);
    if (hex) {
      const a = parseInt(hex[1], 16);
      const b = parseInt(hex[2], 16);
      return ipIsPrivate(`${a >> 8}.${a & 0xff}.${b >> 8}.${b & 0xff}`);
    }
    return false;
  }
  return true; // unknown form → block
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
  if (net.isIP(host)) {
    if (ipIsPrivate(host)) throw new Error('Blocked private IP literal');
    return u;
  }
  const resolved = await dns.lookup(host, { all: true });
  if (resolved.length === 0) throw new Error('Host does not resolve');
  for (const r of resolved) {
    if (ipIsPrivate(r.address)) throw new Error('Host resolves to a private address');
  }
  return u;
}
