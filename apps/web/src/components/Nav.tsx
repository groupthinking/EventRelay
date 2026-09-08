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

/** Primary product navigation — one studio chrome. */
const NAV_LINKS = [
  { href: '/', label: 'Studio' },
  { href: '/features', label: 'Features' },
  { href: '/pricing', label: 'Pricing' },
];

function isNavActive(pathname: string, href: string): boolean {
  if (href === '/') return pathname === '/' || pathname === '/studio';
  return pathname === href || pathname.startsWith(`${href}/`);
}

/** Secondary / developer surfaces — not part of the default user path. */
const DEV_LINKS = [
  { href: '/docs/api', label: 'API' },
];

/**
 * Renders the main site navigation bar.
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
        <Link href="/" className="flex items-center gap-3 group">
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
          {NAV_LINKS.map(({ href, label }) => (
            <Link
              key={href}
              href={href}
              aria-current={isNavActive(pathname, href) ? 'page' : undefined}
              className={clsx(
                'text-sm px-3 py-2 rounded-lg transition-colors',
                isNavActive(pathname, href)
                  ? 'text-white bg-white/[0.08]'
                  : 'text-white/55 hover:text-white hover:bg-white/[0.04]'
              )}
            >
              {label}
            </Link>
          ))}
          <div className="h-5 w-px bg-white/[0.08] mx-1" />
          {DEV_LINKS.map(({ href, label }) => (
            <Link
              key={href}
              href={href}
              className={clsx(
                'hidden text-sm px-3 py-2 rounded-lg transition-colors text-white/30 hover:text-white/55 hover:bg-white/[0.03] xl:inline-flex',
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
          <Link href="/" className="btn btn-primary py-2 px-5 text-sm">
            Analyze
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
              aria-current={isNavActive(pathname, href) ? 'page' : undefined}
              className={clsx(
                'text-sm px-3 py-2.5 rounded-lg transition-colors',
                isNavActive(pathname, href)
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
