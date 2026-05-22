import type { Metadata, Viewport } from 'next';
import { Analytics } from '@vercel/analytics/next';
import { SpeedInsights } from '@vercel/speed-insights/next';
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
  metadataBase: new URL('https://uvai.io'),
  alternates: {
    canonical: 'https://uvai.io',
  },
  openGraph: {
    type: 'website',
    locale: 'en_US',
    url: 'https://uvai.io',
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
      '@id': 'https://uvai.io/#organization',
      name: 'UVAI',
      url: 'https://uvai.io',
      logo: 'https://uvai.io/icon.svg',
      sameAs: ['https://github.com/groupthinking/EventRelay'],
    },
    {
      '@type': 'WebSite',
      '@id': 'https://uvai.io/#website',
      url: 'https://uvai.io',
      name: 'UVAI — The Action Layer for Video',
      description:
        'Paste a YouTube URL. UVAI extracts transcripts, typed events, and action items, then builds from them.',
      publisher: { '@id': 'https://uvai.io/#organization' },
    },
    {
      '@type': 'SoftwareApplication',
      name: 'UVAI',
      applicationCategory: 'DeveloperApplication',
      operatingSystem: 'Web',
      description:
        'AI-powered video automation: transcripts, typed events, action items, and agentic execution. Open source via EventRelay.',
      offers: { '@type': 'Offer', price: '0', priceCurrency: 'USD' },
      url: 'https://uvai.io',
    },
  ],
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="bg-void">
      <body className="min-h-screen bg-void font-sans antialiased">
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
        />
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

        {/* Main content */}
        <div className="relative z-10">
          {children}
        </div>
        <Analytics />
        <SpeedInsights />
      </body>
    </html>
  );
}
