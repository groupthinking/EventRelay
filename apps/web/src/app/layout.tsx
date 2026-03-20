import type { Metadata, Viewport } from 'next';
import { Analytics } from '@vercel/analytics/next';
import './globals.css';
import { ToastProvider } from '@/components/ui/Toast';

// Font CSS variables are defined via <link> to Google Fonts in <head> and
// resolved in globals.css / tailwind.config. This avoids next/font/google
// which hard-fails during build if the Google Fonts API is unreachable
// (common in sandboxed CI and offline environments).

export const metadata: Metadata = {
  title: {
    default: 'EventRelay — Video to Software',
    template: '%s | EventRelay',
  },
  description: 'Paste a YouTube URL. AI analyzes the video, extracts technologies and concepts, generates a project scaffold, and deploys it.',
  keywords: ['video to software', 'AI video analysis', 'video to code', 'agentic video', 'code generation', 'video API'],
  authors: [{ name: 'EventRelay' }],
  creator: 'EventRelay',
  publisher: 'EventRelay',
  metadataBase: new URL('https://uvai.io'),
  openGraph: {
    type: 'website',
    locale: 'en_US',
    url: 'https://uvai.io',
    siteName: 'EventRelay',
    title: 'EventRelay — Video to Software',
    description: 'Paste a YouTube URL. AI analyzes the video, extracts technologies and concepts, generates a project scaffold, and deploys it.',
    images: [
      {
        url: '/og-image.png',
        width: 1200,
        height: 630,
        alt: 'EventRelay — Agentic Video Execution Platform',
      },
    ],
  },
  twitter: {
    card: 'summary_large_image',
    title: 'EventRelay — Video to Software',
    description: 'Paste a YouTube URL. AI analyzes the video, extracts technologies and concepts, generates a project scaffold, and deploys it.',
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
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=Inter:wght@100..900&family=JetBrains+Mono:wght@100..800&display=swap"
          rel="stylesheet"
        />
      </head>
      <body className="min-h-screen bg-surface-950 font-sans antialiased">
        {/* Global background effects */}
        <div className="fixed inset-0 bg-mesh pointer-events-none" />
        <div className="fixed inset-0 noise pointer-events-none" />

        {/* Main content */}
        <div className="relative z-10">
          <ToastProvider>
            {children}
          </ToastProvider>
        </div>
        <Analytics />
      </body>
    </html>
  );
}
