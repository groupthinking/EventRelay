/** @type {import('next').NextConfig} */
const CANONICAL_DOMAIN = 'uvai.io';

const nextConfig = {
  reactStrictMode: true,
  images: {
    domains: [],
  },
  async redirects() {
    // Redirect any non-canonical host to uvai.io at the Next.js level.
    // Vercel handles the same redirects at the CDN edge (vercel.json), but
    // this middleware-level guard also fires for self-hosted / local builds.
    const nonCanonicalHosts = [
      'event-relay-web.vercel.app',
      'v0-uvai.vercel.app',
      'youtube-extension.vercel.app',
      'uvai-io.pages.dev',
      `www.${CANONICAL_DOMAIN}`,
    ];

    return nonCanonicalHosts.map((host) => ({
      source: '/:path*',
      has: [{ type: 'host', value: host }],
      destination: `https://${CANONICAL_DOMAIN}/:path*`,
      permanent: true,
    }));
  },
  async headers() {
    return [
      {
        source: '/(.*)',
        headers: [
          // Help crawlers identify the authoritative URL.
          {
            key: 'Link',
            value: `<https://${CANONICAL_DOMAIN}>; rel="canonical"`,
          },
        ],
      },
    ];
  },
}

module.exports = nextConfig
