# Layouts and shared chrome

The App Router root layout owns global metadata, fonts, analytics, billing activation, structured data, and the navigation shell. Dashboard pages add their own canvas/split-view layout under this root.

## apps/web/src/app/layout.tsx

```tsx
import type { Metadata, Viewport } from 'next';
import { Analytics } from '@vercel/analytics/next';
import { SpeedInsights } from '@vercel/speed-insights/next';
import { Inter, JetBrains_Mono, Space_Grotesk } from 'next/font/google';
import './globals.css';
import { StructuredData } from '@/components/StructuredData';

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
      <head>
        <StructuredData />
        <link rel="preconnect" href="https://img.youtube.com" crossOrigin="anonymous" />
        <link rel="preconnect" href="https://i.ytimg.com" crossOrigin="anonymous" />
      </head>
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
```

## apps/web/src/components/Nav.tsx

```tsx
'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { clsx } from 'clsx';
import { useState } from 'react';
import { Menu, X } from 'lucide-react';

interface NavProps {
  /** Optional right-side content override (e.g., processing status badge) */
  rightSlot?: React.ReactNode;
  /** Optional subtitle shown next to the logo (e.g., "Dashboard", breadcrumb JSX) */
  subtitle?: React.ReactNode;
  /** Whether to use the sticky/fixed variant (for marketing pages) */
  fixed?: boolean;
}

/** Primary product navigation — dashboard-first journey. */
const NAV_LINKS = [
  { href: '/dashboard', label: 'Dashboard', hint: 'Video library' },
  { href: '/dashboard/agents', label: 'Agents', hint: 'Pipeline graph' },
  { href: '/features', label: 'Features' },
  { href: '/pricing', label: 'Pricing' },
];

/** Secondary / developer surfaces — not part of the default user path. */
const DEV_LINKS = [
  { href: '/studio', label: 'Studio', hint: 'Local drafts' },
  { href: '/docs/api', label: 'API' },
];

/**
 * Renders the main site navigation bar.
 *
 * @param rightSlot - Optional content to display on the right side
 * @param subtitle - Optional content displayed next to the logo
 * @param fixed - Renders the navigation bar with fixed positioning when `true`
 */
export default function Nav({ rightSlot, subtitle, fixed = false }: NavProps) {
  const pathname = usePathname();
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <nav
      className={clsx(
        'flex flex-wrap items-center justify-between px-6 lg:px-12 py-4 border-b border-white/[0.05] z-50',
        fixed
          ? 'fixed top-0 left-0 right-0 bg-surface-950/80 backdrop-blur-xl'
          : 'bg-surface-950/80 backdrop-blur-xl'
      )}
    >
      <div className="flex items-center gap-4">
        <Link href="/dashboard" className="flex items-center gap-3 group">
          <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-primary-500 to-primary-600 flex items-center justify-center font-black text-base shadow-lg shadow-primary-500/25 transition-transform group-hover:scale-105">
            U
          </div>
          <span className="font-bold text-lg font-heading">UVAI</span>
        </Link>

        {subtitle && (
          <>
            <div className="h-5 w-px bg-white/[0.08]" />
            <span className="text-white/50 font-medium text-sm">{subtitle}</span>
          </>
        )}

        <div className="hidden md:flex items-center gap-1 ml-4">
          {NAV_LINKS.map(({ href, label, hint }) => (
            <Link
              key={href}
              href={href}
              aria-current={pathname === href ? 'page' : undefined}
              title={hint}
              className={clsx(
                'text-sm px-3 py-2 rounded-lg transition-colors',
                pathname === href || pathname.startsWith(`${href}/`)
                  ? 'text-white/90 bg-white/[0.05]'
                  : 'text-white/40 hover:text-white/70 hover:bg-white/[0.03]'
              )}
            >
              <span>{label}</span>
              {hint && (
                <span className="ml-1.5 hidden lg:inline text-[9px] uppercase tracking-wider text-white/25">
                  {hint}
                </span>
              )}
            </Link>
          ))}
          <div className="h-5 w-px bg-white/[0.08] mx-1" />
          {DEV_LINKS.map(({ href, label, hint }) => (
            <Link
              key={href}
              href={href}
              title={hint}
              className={clsx(
                'text-sm px-3 py-2 rounded-lg transition-colors text-white/30 hover:text-white/55 hover:bg-white/[0.03]',
                pathname === href && 'text-white/60 bg-white/[0.04]'
              )}
            >
              {label}
            </Link>
          ))}
        </div>
      </div>

      <div className="flex items-center gap-3">
        {rightSlot || (
          <Link href="/dashboard" className="btn btn-primary py-2 px-5 text-sm">
            Open Dashboard
          </Link>
        )}
        <button
          type="button"
          onClick={() => setMobileOpen((open) => !open)}
          aria-expanded={mobileOpen}
          aria-controls="mobile-nav"
          aria-label={mobileOpen ? 'Close navigation menu' : 'Open navigation menu'}
          className="md:hidden inline-flex items-center justify-center w-10 h-10 rounded-lg text-white/70 hover:text-white hover:bg-white/[0.05] transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-primary-500/50"
        >
          {mobileOpen ? (
            <X className="h-5 w-5" aria-hidden="true" />
          ) : (
            <Menu className="h-5 w-5" aria-hidden="true" />
          )}
        </button>
      </div>

      {/* Mobile links */}
      {mobileOpen && (
        <div
          id="mobile-nav"
          className="md:hidden w-full mt-3 flex flex-col gap-1 border-t border-white/[0.05] pt-3"
        >
          {NAV_LINKS.map(({ href, label }) => (
            <Link
              key={href}
              href={href}
              onClick={() => setMobileOpen(false)}
              aria-current={pathname === href ? 'page' : undefined}
              className={clsx(
                'text-sm px-3 py-2.5 rounded-lg transition-colors',
                pathname === href
                  ? 'text-white/90 bg-white/[0.05]'
                  : 'text-white/50 hover:text-white/80 hover:bg-white/[0.03]'
              )}
            >
              {label}
            </Link>
          ))}
        </div>
      )}
    </nav>
  );
}
```

## apps/web/src/components/Footer.tsx

```tsx
import Link from 'next/link';

const PRODUCT_LINKS = [
  { label: 'Dashboard', href: '/dashboard' },
  { label: 'Features', href: '/features' },
  { label: 'Pricing', href: '/pricing' },
  { label: 'API Docs', href: '/playground' },
];

const USE_CASES = ['Meeting Notes', 'Conference Talks', 'Tutorials', 'Product Demos', 'Podcasts'];

const EXTERNAL_LINKS = [
  { label: 'GitHub', href: 'https://github.com/groupthinking/EventRelay' },
  { label: 'Product Hunt', href: 'https://www.producthunt.com' },
];

interface FooterProps {
  /** Use the compact variant (just copyright + links) for app pages */
  variant?: 'full' | 'compact';
}

/**
 * Renders the site footer in a compact or full layout.
 *
 * @param variant - The footer layout to render.
 */
export default function Footer({ variant = 'compact' }: FooterProps) {
  if (variant === 'compact') {
    return (
      <footer className="border-t border-white/[0.06] py-6">
        <div className="max-w-6xl mx-auto px-6 flex items-center justify-between text-xs text-white/25">
          <span>UVAI • Video to Software</span>
          <div className="flex items-center gap-4">
            <Link href="/features" className="hover:text-white/50 transition py-2 px-1">
              Features
            </Link>
            <Link href="/playground" className="hover:text-white/50 transition py-2 px-1">
              API
            </Link>
            <a
              href="https://github.com/groupthinking/EventRelay"
              target="_blank"
              rel="noopener noreferrer"
              className="hover:text-white/50 transition py-2 px-1"
            >
              GitHub
            </a>
          </div>
        </div>
      </footer>
    );
  }

  return (
    <footer className="border-t border-white/[0.06] py-10">
      <div className="max-w-6xl mx-auto px-6">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-8 mb-10">
          <div>
            <div className="flex items-center gap-2 mb-4">
              <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-primary-500 to-primary-600 flex items-center justify-center font-black text-xs">
                U
              </div>
              <span className="font-bold text-sm">UVAI</span>
            </div>
            <p className="text-xs text-white/30 leading-relaxed">
              AI-powered video intelligence for teams and individuals.
            </p>
          </div>
          <div>
            <div className="text-xs font-semibold text-white/40 uppercase tracking-wider mb-4">
              Product
            </div>
            <ul className="space-y-2.5 text-xs text-white/35">
              {PRODUCT_LINKS.map(({ label, href }) => (
                <li key={label}>
                  <Link href={href} className="hover:text-white/60 transition">
                    {label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>
          <div>
            <div className="text-xs font-semibold text-white/40 uppercase tracking-wider mb-4">
              Use Cases
            </div>
            <ul className="space-y-2.5 text-xs text-white/35">
              {USE_CASES.map((u) => (
                <li key={u}>
                  <span className="cursor-default">{u}</span>
                </li>
              ))}
            </ul>
          </div>
          <div>
            <div className="text-xs font-semibold text-white/40 uppercase tracking-wider mb-4">
              Links
            </div>
            <ul className="space-y-2.5 text-xs text-white/35">
              {EXTERNAL_LINKS.map(({ label, href }) => (
                <li key={label}>
                  <a
                    href={href}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="hover:text-white/60 transition"
                  >
                    {label}
                  </a>
                </li>
              ))}
            </ul>
          </div>
        </div>
        <div className="border-t border-white/[0.05] pt-6 flex flex-col md:flex-row items-center justify-between gap-3 text-xs text-white/25">
          <span>© 2026 UVAI. MIT License.</span>
          <div className="flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse motion-reduce:animate-none" />
            <span>All systems operational</span>
          </div>
        </div>
      </div>
    </footer>
  );
}
```
