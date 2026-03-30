/** @type {import('next').NextConfig} */
const CANONICAL_DOMAIN = 'uvai.io';

const nextConfig = {
  reactStrictMode: true,
  images: {
    domains: ['uvai.io', 'api.uvai.io'],
  },
  async redirects() {
    return [
      // Redirect www to non-www
      {
        source: '/:path*',
        has: [
          {
            type: 'host',
            value: 'www.uvai.io',
          },
        ],
        destination: 'https://uvai.io/:path*',
        permanent: true,
      },
      // Redirect legacy Vercel domains
      {
        source: '/:path*',
        has: [
          {
            type: 'host',
            value: 'event-relay-web.vercel.app',
          },
        ],
        destination: 'https://uvai.io/:path*',
        permanent: true,
      },
      {
        source: '/:path*',
        has: [
          {
            type: 'host',
            value: 'v0-uvai.vercel.app',
          },
        ],
        destination: 'https://uvai.io/:path*',
        permanent: true,
      },
      {
        source: '/:path*',
        has: [
          {
            type: 'host',
            value: 'youtube-extension.vercel.app',
          },
        ],
        destination: 'https://uvai.io/:path*',
        permanent: true,
      },
    ]
  },
  async headers() {
    return [
      {
        source: '/:path*',
        headers: [
          {
            key: 'X-DNS-Prefetch-Control',
            value: 'on',
          },
          {
            key: 'Strict-Transport-Security',
            value: 'max-age=63072000; includeSubDomains; preload',
          },
          {
            key: 'X-Content-Type-Options',
            value: 'nosniff',
          },
          {
            key: 'X-Frame-Options',
            value: 'SAMEORIGIN',
          },
          {
            key: 'X-XSS-Protection',
            value: '1; mode=block',
          },
          {
            key: 'Referrer-Policy',
            value: 'origin-when-cross-origin',
          },
        ],
      },
    ]
  },
  async redirects() {
    return [
      {
        source: '/:path*',
        has: [{ type: 'host', value: 'event-relay-web.vercel.app' }],
        destination: 'https://uvai.io/:path*',
        permanent: true,
      },
      {
        source: '/:path*',
        has: [{ type: 'host', value: 'v0-uvai.vercel.app' }],
        destination: 'https://uvai.io/:path*',
        permanent: true,
      },
      {
        source: '/:path*',
        has: [{ type: 'host', value: 'youtube-extension.vercel.app' }],
        destination: 'https://uvai.io/:path*',
        permanent: true,
      },
      {
        source: '/:path*',
        has: [{ type: 'host', value: 'uvai-io.pages.dev' }],
        destination: 'https://uvai.io/:path*',
        permanent: true,
      },
      {
        source: '/:path*',
        has: [{ type: 'host', value: 'www.uvai.io' }],
        destination: 'https://uvai.io/:path*',
        permanent: true,
      },
    ];
  },
  async redirects() {
    const legacyHosts = [
      'event-relay-web.vercel.app',
      'v0-uvai.vercel.app',
      'youtube-extension.vercel.app',
      'uvai-io.pages.dev',
      'sell.solutions',
      'www.sell.solutions',
      'myai.directory',
      'www.myai.directory',
    ];

    return legacyHosts.map((host) => ({
      source: '/:path*',
      has: [{ type: 'host', value: host }],
      destination: 'https://uvai.io/:path*',
      permanent: true,
    }));
  },
  async headers() {
    return [
      {
        source: '/(.*)',
        headers: [
          { key: 'X-Frame-Options', value: 'DENY' },
          { key: 'X-Content-Type-Options', value: 'nosniff' },
          { key: 'Referrer-Policy', value: 'strict-origin-when-cross-origin' },
        ],
      },
    ];
  },
};

module.exports = nextConfig;
