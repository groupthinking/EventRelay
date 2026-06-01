/**
 * SSRF guard for server-side fetches of user-supplied URLs.
 *
 * Rejects non-http(s) schemes and any host that resolves to a private,
 * loopback, link-local, or cloud-metadata address (e.g. 169.254.169.254).
 *
 * Note: this resolves DNS and checks the result, which closes the common SSRF
 * cases. It does not fully defeat DNS-rebinding (a TOCTOU gap between this check
 * and the actual fetch); for that, pin the resolved IP and fetch by IP with a
 * Host header. This is a strong, low-cost first line of defense.
 */
import * as dns from 'node:dns/promises';
import * as net from 'node:net';

const BLOCKED_HOSTNAMES = new Set(['localhost', 'metadata.google.internal']);

function ipIsPrivate(ip: string): boolean {
  if (net.isIPv4(ip)) {
    const p = ip.split('.').map(Number);
    return (
      p[0] === 10 ||
      (p[0] === 172 && p[1] >= 16 && p[1] <= 31) ||
      (p[0] === 192 && p[1] === 168) ||
      p[0] === 127 || // loopback
      (p[0] === 169 && p[1] === 254) || // link-local incl. cloud metadata
      p[0] === 0 ||
      p[0] >= 224 // multicast / reserved
    );
  }
  if (net.isIPv6(ip)) {
    const lc = ip.toLowerCase();
    if (lc === '::1' || lc === '::') return true; // loopback / unspecified
    if (lc.startsWith('fe80') || lc.startsWith('fc') || lc.startsWith('fd')) {
      return true; // link-local / unique-local
    }
    const mapped = lc.match(/::ffff:(\d+\.\d+\.\d+\.\d+)/); // IPv4-mapped
    if (mapped) return ipIsPrivate(mapped[1]);
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
