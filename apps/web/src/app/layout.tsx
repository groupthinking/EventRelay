import type { Metadata, Viewport } from 'next';
import { Inter, JetBrains_Mono } from 'next/font/google';
import './globals.css';

const inter = Inter({
  subsets: ['latin'],
  display: 'swap',
  variable: '--font-inter',
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ['latin'],
  display: 'swap',
  variable: '--font-mono',
});

export const metadata: Metadata = {
  title: {
    default: 'UVAI.io - Transform Video into Actionable Intelligence',
    template: '%s | UVAI.io',
  },
  description: 'Stop watching. Start acting. UVAI extracts insights, generates action items, and deploys live applications from any video in 2.3 seconds.',
  keywords: ['video intelligence', 'AI video analysis', 'video to code', 'meeting transcription', 'action items', 'video API'],
  authors: [{ name: 'UVAI Team' }],
  creator: 'UVAI.io',
  publisher: 'UVAI.io',
  metadataBase: new URL('https://uvai.io'),
  openGraph: {
    type: 'website',
    locale: 'en_US',
    url: 'https://uvai.io',
    siteName: 'UVAI.io',
    title: 'UVAI.io - Transform Video into Actionable Intelligence',
    description: 'Stop watching. Start acting. UVAI extracts insights, generates action items, and deploys live applications from any video in 2.3 seconds.',
    images: [
      {
        url: '/og-image.png',
        width: 1200,
        height: 630,
        alt: 'UVAI.io - Video Intelligence Platform',
      },
    ],
  },
  twitter: {
    card: 'summary_large_image',
    title: 'UVAI.io - Transform Video into Actionable Intelligence',
    description: 'Stop watching. Start acting. UVAI extracts insights, generates action items, and deploys live applications from any video in 2.3 seconds.',
    images: ['/og-image.png'],
    creator: '@uvai_io',
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
    { media: '(prefers-color-scheme: light)', color: '#8b5cf6' },
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
    <html lang="en" className={`${inter.variable} ${jetbrainsMono.variable}`}>
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
      </head>
      <body className="min-h-screen bg-surface-950 font-sans antialiased">
        {/* Global background effects */}
        <div className="fixed inset-0 bg-mesh pointer-events-none" />
        <div className="fixed inset-0 noise pointer-events-none" />

        {/* Main content */}
        <div className="relative z-10">
          {children}
        </div>
      </body>
    </html>
  );
}