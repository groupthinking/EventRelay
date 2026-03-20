/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  images: {
    domains: [],
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
}

module.exports = nextConfig
