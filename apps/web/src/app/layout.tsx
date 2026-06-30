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
    default: 'UVAI — Video to Structured Intelligence',
    template: '%s | UVAI',
  },
  description: 'UVAI turns YouTube videos into transcripts, typed events, action items, and AI-driven analysis using Gemini and OpenAI. Open source via the EventRelay project.',
  keywords: ['UVAI', 'video intelligence', 'YouTube transcript', 'structured events', 'Gemini', 'OpenAI', 'EventRelay', 'agentic video'],
  authors: [{ name: 'UVAI' }],
  creator: 'UVAI',
  publisher: 'UVAI',
  metadataBase: new URL('https://v0-uvai.vercel.app'),
  openGraph: {
    type: 'website',
    locale: 'en_US',
    url: 'https://v0-uvai.vercel.app',
    siteName: 'UVAI',
    title: 'UVAI — Video to Structured Intelligence',
    description: 'Paste a YouTube URL. Get transcripts, typed events, action items, and multi-agent analysis from an open-source video intelligence platform.',
    images: [
      {
        url: '/og-image.png',
        width: 1200,
        height: 630,
        alt: 'UVAI — Agentic Video Execution Platform',
      },
    ],
  },
  twitter: {
    card: 'summary_large_image',
    title: 'UVAI — Video to Structured Intelligence',
    description: 'Paste a YouTube URL. Get transcripts, typed events, action items, and multi-agent analysis from an open-source video intelligence platform.',
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

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-surface-950 font-sans antialiased">
        {/* Global background effects */}
        <div className="fixed inset-0 bg-mesh pointer-events-none" />
        <div className="fixed inset-0 noise pointer-events-none" />

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