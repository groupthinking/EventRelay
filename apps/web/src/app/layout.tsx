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
  description: 'UVAI takes what is inside a YouTube video — tools, workflows, concepts — and builds from them. Transcripts, typed events, action items, and agentic execution powered by Gemini and OpenAI.',
  keywords: ['UVAI', 'video to action', 'YouTube build', 'video intelligence', 'structured events', 'Gemini', 'OpenAI', 'EventRelay', 'agentic video execution'],
  authors: [{ name: 'UVAI' }],
  creator: 'UVAI',
  publisher: 'UVAI',
  metadataBase: new URL('https://v0-uvai.vercel.app'),
  openGraph: {
    type: 'website',
    locale: 'en_US',
    url: 'https://v0-uvai.vercel.app',
    siteName: 'UVAI',
    title: 'UVAI — The Action Layer for Video',
    description: 'Paste a YouTube URL. UVAI takes what is inside the video and builds from it — transcripts, typed events, action items, and agentic execution powered by Gemini and OpenAI.',
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
    description: 'Paste a YouTube URL. UVAI takes what is inside the video and builds from it — transcripts, typed events, action items, and agentic execution powered by Gemini and OpenAI.',
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
