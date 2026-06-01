import type { Metadata, Viewport } from 'next';
import { Analytics } from '@vercel/analytics/next';
import { SpeedInsights } from '@vercel/speed-insights/next';
import { SITE_URL } from '@/lib/site';
import './globals.css';

// Fonts use the system stack declared in tailwind.config (Inter / JetBrains
// Mono with system-ui fallbacks). We intentionally avoid next/font/google
// because it hard-fails during build when the Google Fonts API is unreachable
// (common in sandboxed CI and offline environments).

export const metadata: Metadata = {
  title: {
    default: 'UVAI — The Action Layer for Video',
    template: '%s | UVAI',
  },
  description: 'UVAI takes what is inside a YouTube video and builds from it — transcripts, typed events, action items, and agentic execution powered by Gemini and OpenAI. Open source via EventRelay.',
  keywords: ['UVAI', 'video to action', 'YouTube build', 'video intelligence', 'structured events', 'Gemini', 'OpenAI', 'EventRelay', 'agentic video execution'],
  authors: [{ name: 'UVAI' }],
  creator: 'UVAI',
  publisher: 'UVAI',
  metadataBase: new URL(SITE_URL),
  alternates: {
    canonical: SITE_URL,
  },
  openGraph: {
    type: 'website',
    locale: 'en_US',
    url: SITE_URL,
    siteName: 'UVAI',
    title: 'UVAI — The Action Layer for Video',
    description: 'Paste a YouTube URL. UVAI takes what is inside the video and builds from it — transcripts, typed events, action items, and agentic execution.',
    images: [
      {
        url: '/og-image.png',
        width: 1200,
        height: 630,
        alt: 'UVAI — The Action Layer for Video',
      },
    ],
  },
  twitter: {
    card: 'summary_large_image',
    title: 'UVAI — The Action Layer for Video',
    description: 'Paste a YouTube URL. UVAI takes what is inside the video and builds from it — transcripts, typed events, action items, and agentic execution.',
    images: ['/og-image.png'],
    creator: '@groupthinking',
  },
  robots: {
    index: true,
    follow: true,
    googleBot: {
      index: true,
      follow: true,
      'max-video-preview': -1,
      'max-image-preview': 'large',
      'max-snippet': -1,
    },
  },
  icons: {
    icon: [
      { url: '/favicon.ico' },
      { url: '/icon.svg', type: 'image/svg+xml' },
    ],
    apple: '/apple-touch-icon.png',
  },
  manifest: '/manifest.json',
};

export const viewport: Viewport = {
  themeColor: [
    { media: '(prefers-color-scheme: light)', color: '#14b8a6' },
    { media: '(prefers-color-scheme: dark)', color: '#020617' },
  ],
  width: 'device-width',
  initialScale: 1,
  maximumScale: 5,
};

const jsonLd = {
  '@context': 'https://schema.org',
  '@graph': [
    {
      '@type': 'Organization',
      '@id': `${SITE_URL}/#organization`,
      name: 'UVAI',
      url: SITE_URL,
      logo: `${SITE_URL}/icon.svg`,
      sameAs: ['https://github.com/groupthinking/EventRelay'],
    },
    {
      '@type': 'WebSite',
      '@id': `${SITE_URL}/#website`,
      url: SITE_URL,
      name: 'UVAI — The Action Layer for Video',
      description:
        'Paste a YouTube URL. UVAI extracts transcripts, typed events, and action items, then builds from them.',
      publisher: { '@id': `${SITE_URL}/#organization` },
    },
    {
      '@type': 'SoftwareApplication',
      name: 'UVAI',
      applicationCategory: 'DeveloperApplication',
      operatingSystem: 'Web',
      description:
        'AI-powered video automation: transcripts, typed events, action items, and agentic execution. Open source via EventRelay.',
      offers: { '@type': 'Offer', price: '0', priceCurrency: 'USD' },
      url: SITE_URL,
    },
  ],
};

// Escape `<` so a stray "</script>" inside JSON values cannot break out of the
// inline JSON-LD block. This is the React/Next-recommended safe pattern for
// inline JSON without `dangerouslySetInnerHTML`.
const jsonLdString = JSON.stringify(jsonLd).replace(/</g, '\\u003c');

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="bg-void">
      <body className="min-h-screen bg-void font-sans antialiased">
        <script type="application/ld+json">{jsonLdString}</script>
        {/* Skip to main content for keyboard/screen reader users */}
        <a
          href="#main"
          className="sr-only focus:not-sr-only focus:fixed focus:top-2 focus:left-2 focus:z-[100] focus:px-4 focus:py-2 focus:rounded-lg focus:bg-[#6af2de] focus:text-[#021a18] focus:font-bold"
        >
          Skip to main content
        </a>
        {/* Global background effects */}
        <div className="fixed inset-0 bg-mesh pointer-events-none" aria-hidden="true" />
        <div className="fixed inset-0 noise pointer-events-none" aria-hidden="true" />

        {/* Main content — id="main" lives on the layout wrapper so the
            skip-to-main link works on every route, not just the homepage. */}
        <div id="main" className="relative z-10">
          {children}
        </div>
        <Analytics />
        <SpeedInsights />
      </body>
    </html>
  );
}
