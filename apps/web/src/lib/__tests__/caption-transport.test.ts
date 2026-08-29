import { describe, expect, it } from 'vitest';
import {
  resolveCaptionTransport,
  timedtextLooksBlocked,
  webshareRotatingUrl,
} from '@/lib/caption-transport';

describe('caption transport', () => {
  it('builds the rotating US Webshare URL the Python backend uses', () => {
    const url = webshareRotatingUrl('acct', 's3cret');
    expect(url).toBe('http://acct-US-rotate:s3cret@p.webshare.io:80/');
    expect(url).not.toContain('s3cret-');
  });

  it('does not double-append -rotate', () => {
    expect(webshareRotatingUrl('acct-rotate', 'pw')).toBe(
      'http://acct-US-rotate:pw@p.webshare.io:80/',
    );
  });

  it('prefers Webshare credentials over a generic proxy URL', () => {
    const transport = resolveCaptionTransport({
      WEBSHARE_PROXY_USERNAME: 'acct',
      WEBSHARE_PROXY_PASSWORD: 'pw',
      WEBSHARE_PROXY_URL: 'http://other:pass@proxy.example:8080',
    });
    expect(transport.kind).toBe('webshare_residential');
    expect(transport.proxyUrl).toContain('p.webshare.io');
  });

  it('uses WEBSHARE_PROXY_URL when credentials are absent', () => {
    const transport = resolveCaptionTransport({
      WEBSHARE_PROXY_URL: 'http://user:pass@proxy.example:8080',
    });
    expect(transport.kind).toBe('rotating_residential_proxy');
    expect(transport.proxyUrl).toBe('http://user:pass@proxy.example:8080');
  });

  it('falls back to direct when proxy config is incomplete', () => {
    expect(resolveCaptionTransport({ WEBSHARE_PROXY_USERNAME: 'acct' }).kind).toBe('direct');
    expect(resolveCaptionTransport({}).kind).toBe('direct');
    expect(resolveCaptionTransport({ WEBSHARE_PROXY_URL: 'not-a-url' }).kind).toBe('direct');
  });

  it('treats empty HTML timedtext as blocked', () => {
    expect(timedtextLooksBlocked('text/html; charset=UTF-8', '')).toBe(true);
    expect(timedtextLooksBlocked('text/xml; charset=UTF-8', '<?xml version="1.0"?><transcript><text start="0">hi there this is real speech</text></transcript>')).toBe(false);
  });
});
