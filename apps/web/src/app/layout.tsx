import type { Metadata, Viewport } from 'next';
import { Analytics } from '@vercel/analytics/next';
import { SpeedInsights } from '@vercel/speed-insights/next';
import { Inter, JetBrains_Mono, Space_Grotesk } from 'next/font/google';
import './globals.css';

const inter = Inter({
  subsets: ['latin'],
  display: 'swap',
  variable: '--font-body',
});

const jetBrainsMono = JetBrains_Mono({
  subsets: ['latin'],
  display: 'swap',
  variable: '--font-mono',
});

const spaceGrotesk = Space_Grotesk({
  subsets: ['latin'],
  display: 'swap',
  variable: '--font-heading',
});

export const metadata: Metadata = {
  title: {
    default: 'UVAI — Video to Workflow',
    template: '%s | UVAI',
  },
  description: 'Paste a YouTube URL. UVAI turns video evidence into useful workflows, exports, and deployable next steps.',
  keywords: ['video to software', 'AI video analysis', 'video to code', 'agentic video', 'code generation', 'video API', 'UVAI'],
  authors: [{ name: 'UVAI' }],
  creator: 'UVAI',
  publisher: 'UVAI',
  metadataBase: new URL('https://uvai.io'),
  openGraph: {
    type: 'website',
    locale: 'en_US',
    url: 'https://uvai.io',
    siteName: 'UVAI',
    title: 'UVAI — Video to Workflow',
    description: 'Paste a YouTube URL. UVAI turns video evidence into useful workflows, exports, and deployable next steps.',
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
    title: 'UVAI — Video to Workflow',
    description: 'Paste a YouTube URL. UVAI turns video evidence into useful workflows, exports, and deployable next steps.',
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
      { url: '/icon.svg', type: 'image/svg+xml' },
    ],
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

const shouldLoadAnalytics = process.env.VERCEL === '1';

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body
        className={`${inter.variable} ${jetBrainsMono.variable} ${spaceGrotesk.variable} min-h-screen bg-surface-950 font-sans antialiased`}
      >
        {/* Global background effects */}
        <div className="fixed inset-0 bg-mesh pointer-events-none" />
        <div className="fixed inset-0 noise pointer-events-none" />

        {/* Main content */}
        <div className="relative z-10">
          {children}
        </div>
        {shouldLoadAnalytics && <Analytics />}
        {shouldLoadAnalytics && <SpeedInsights />}
      </body>
    </html>
  );
}
