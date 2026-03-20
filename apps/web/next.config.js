/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  images: {
    domains: [],
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
