const path = require('path');

let withSentryConfig = (config) => config;
try {
  ({ withSentryConfig } = require('@sentry/nextjs'));
} catch {
  // Allow builds to continue when optional Sentry runtime peers are unavailable.
}

// Vercel Workflow DevKit — enables "use workflow" / "use step" compilation.
// https://workflow-sdk.dev/docs/getting-started/next
let withWorkflow = (config) => config;
try {
  ({ withWorkflow } = require('workflow/next'));
} catch {
  // Optional when workflow package is not installed in a partial install.
}

const contentSecurityPolicy = [
  "default-src 'self'",
  "base-uri 'self'",
  "object-src 'none'",
  "frame-ancestors 'none'",
  "form-action 'self'",
  "img-src 'self' data: blob: https://uvai.io https://api.uvai.io https://img.youtube.com https://i.ytimg.com https://*.ytimg.com",
  "font-src 'self' data:",
  "style-src 'self' 'unsafe-inline'",
  "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://www.youtube.com https://www.youtube-nocookie.com https://js.stripe.com https://challenges.cloudflare.com https://va.vercel-scripts.com https://vitals.vercel-insights.com",
  "connect-src 'self' https://api.uvai.io https://uvai-backend-gpwz4wb5na-uc.a.run.app https://api.openai.com https://generativelanguage.googleapis.com https://*.supabase.co wss://*.supabase.co https://*.upstash.io https://challenges.cloudflare.com https://vitals.vercel-insights.com https://*.vercel-insights.com https://*.ingest.us.sentry.io https://*.ingest.sentry.io",
  "frame-src 'self' https://www.youtube.com https://www.youtube-nocookie.com https://js.stripe.com https://hooks.stripe.com https://challenges.cloudflare.com",
  "media-src 'self' blob: data:",
  "worker-src 'self' blob:",
  "manifest-src 'self'",
  "upgrade-insecure-requests",
].join('; ');

const securityHeaders = [
  { key: 'X-DNS-Prefetch-Control', value: 'on' },
  {
    key: 'Strict-Transport-Security',
    value: 'max-age=63072000; includeSubDomains; preload',
  },
  { key: 'X-Content-Type-Options', value: 'nosniff' },
  { key: 'X-Frame-Options', value: 'DENY' },
  { key: 'Referrer-Policy', value: 'strict-origin-when-cross-origin' },
  {
    key: 'Permissions-Policy',
    value: 'camera=(), geolocation=(), microphone=(self), payment=(), usb=()',
  },
  { key: 'Content-Security-Policy', value: contentSecurityPolicy },
];

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Keep local Chrome QA functional when the dev server is reached by its
  // loopback IP instead of the canonical localhost name.
  allowedDevOrigins: ['127.0.0.1'],
  // #1538: webpack-bundling undici + @workflow/world-vercel produces two
  // undici class copies. Agent.dispatch then throws #P even after the
  // postinstall rewrite to undici.fetch (preview dpl_6g5ZcZwr still 500).
  // Leave them as Node runtime requires so Agent and fetch share one module.
  serverExternalPackages: ['undici', '@workflow/world-vercel'],
  experimental: {
    optimizePackageImports: ['lucide-react'],
  },
  turbopack: {
    // Monorepo root so Turbopack resolves hoisted/workspace deps outside apps/web.
    root: path.resolve(__dirname, '../..'),
  },
  images: {
    formats: ['image/avif', 'image/webp'],
    remotePatterns: [
      { protocol: 'https', hostname: 'uvai.io' },
      { protocol: 'https', hostname: 'api.uvai.io' },
      { protocol: 'https', hostname: 'img.youtube.com' },
      { protocol: 'https', hostname: 'i.ytimg.com' },
    ],
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
      'www.uvai.io',
    ];

    return [
      {
        source: '/dashboard',
        destination: '/',
        permanent: true,
      },
      {
        source: '/dashboard/:path*',
        destination: '/',
        permanent: true,
      },
      ...legacyHosts.map((host) => ({
        source: '/:path*',
        has: [{ type: 'host', value: host }],
        destination: 'https://uvai.io/:path*',
        permanent: true,
      })),
    ];
  },
  async headers() {
    return [
      {
        source: '/:path*',
        headers: securityHeaders,
      },
    ];
  },
};

const sentryWebpackPluginOptions = {
  org: process.env.SENTRY_ORG || '',
  project: process.env.SENTRY_PROJECT || 'v0-uvai',
  silent: !process.env.CI,
  // Preview/prod builds succeed without Sentry upload credentials.
  disableServerWebpackPlugin: !process.env.SENTRY_AUTH_TOKEN,
  disableClientWebpackPlugin: !process.env.SENTRY_AUTH_TOKEN,
};

module.exports = withWorkflow(
  withSentryConfig(nextConfig, sentryWebpackPluginOptions),
);
