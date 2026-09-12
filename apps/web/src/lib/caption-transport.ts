/**
 * Caption egress for YouTube Innertube/timedtext.
 *
 * Same contract as apps/backend/main.py `_caption_transport`:
 * Webshare username/password → rotating residential US IPs.
 * WEBSHARE_PROXY_URL → generic HTTP(S) proxy.
 * Otherwise direct (works from a home IP, blocked from Vercel).
 */

export type CaptionTransportKind =
  | 'webshare_residential'
  | 'rotating_residential_proxy'
  | 'direct';

export interface CaptionTransport {
  kind: CaptionTransportKind;
  /** Full proxy URL including credentials. Never log this. */
  proxyUrl: string | null;
}

const WEBSHARE_HOST = 'p.webshare.io';
const WEBSHARE_PORT = '80';
const ROTATE_SUFFIX = '-rotate';

export function webshareRotatingUrl(
  username: string,
  password: string,
  locations: string[] = ['US'],
): string {
  let user = username.trim();
  if (user.endsWith(ROTATE_SUFFIX)) {
    user = user.slice(0, -ROTATE_SUFFIX.length);
  }
  const locationCodes = locations
    .map((code) => code.trim())
    .filter(Boolean)
    .map((code) => `-${code.toUpperCase()}`)
    .join('');
  const userinfo = `${user}${locationCodes}${ROTATE_SUFFIX}`;
  return `http://${encodeURIComponent(userinfo)}:${encodeURIComponent(password)}@${WEBSHARE_HOST}:${WEBSHARE_PORT}/`;
}

export function resolveCaptionTransport(
  env: NodeJS.Dict<string> = process.env,
): CaptionTransport {
  const username = (env.WEBSHARE_PROXY_USERNAME || '').trim();
  const password = (env.WEBSHARE_PROXY_PASSWORD || '').trim();
  const configuredUrl = (env.WEBSHARE_PROXY_URL || '').trim();

  if (username || password) {
    if (!username || !password) {
      return { kind: 'direct', proxyUrl: null };
    }
    return {
      kind: 'webshare_residential',
      proxyUrl: webshareRotatingUrl(username, password),
    };
  }

  if (configuredUrl) {
    try {
      const parsed = new URL(configuredUrl);
      if (
        (parsed.protocol === 'http:' || parsed.protocol === 'https:') &&
        parsed.hostname &&
        parsed.port
      ) {
        return { kind: 'rotating_residential_proxy', proxyUrl: configuredUrl };
      }
    } catch {
      return { kind: 'direct', proxyUrl: null };
    }
  }

  return { kind: 'direct', proxyUrl: null };
}

export function timedtextLooksBlocked(contentType: string, body: string): boolean {
  const trimmed = body.trim();
  if (trimmed.length < 40) return true;
  if (/text\/html/i.test(contentType) && !/<transcript\b|<text\b|"wireMagic"/i.test(trimmed)) {
    return true;
  }
  return false;
}
