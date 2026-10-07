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
  /** Color tone. 'light' matches the card system (DESIGN_LANGUAGE.md); 'dark' is the legacy skin. */
  tone?: 'dark' | 'light';
}

/** Primary product navigation — Home sells; Studio is the workbench. */
const NAV_LINKS = [
  { href: '/', label: 'Home' },
  { href: '/studio', label: 'Studio' },
  { href: '/pricing', label: 'Pricing' },
];

function isNavActive(pathname: string, href: string): boolean {
  if (href === '/') return pathname === '/';
  return pathname === href || pathname.startsWith(`${href}/`);
}

/** Secondary / developer surfaces — not part of the default user path. */
const DEV_LINKS = [
  { href: '/docs/api', label: 'API' },
];

/**
 * Renders the main site navigation bar.
 */
export default function Nav({ rightSlot, subtitle, fixed = false, tone = 'dark' }: NavProps) {
  const pathname = usePathname();
  const [mobileOpen, setMobileOpen] = useState(false);
  const light = tone === 'light';

  return (
    <nav
      className={clsx(
        'flex flex-wrap items-center justify-between px-6 lg:px-12 py-4 border-b z-50',
        light
          ? 'border-slate-200 bg-white/85 backdrop-blur-xl'
          : 'border-white/[0.05] bg-surface-950/80 backdrop-blur-xl',
        fixed && 'fixed top-0 left-0 right-0'
      )}
    >
      <div className="flex items-center gap-4">
        <Link href="/" className="flex items-center gap-3 group">
          <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-amber-500 to-amber-600 flex items-center justify-center font-black text-base text-white shadow-lg shadow-amber-500/25 transition-transform group-hover:scale-105">
            U
          </div>
          <span className={clsx('font-bold text-lg font-heading', light ? 'text-slate-900' : 'text-white')}>UVAI</span>
        </Link>

        {subtitle && (
          <>
            <div className={clsx('h-5 w-px', light ? 'bg-slate-200' : 'bg-white/[0.08]')} />
            <span className={clsx('font-medium text-sm', light ? 'text-slate-500' : 'text-white/50')}>{subtitle}</span>
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
                  ? light
                    ? 'text-slate-900 bg-slate-100'
                    : 'text-white bg-white/[0.08]'
                  : light
                    ? 'text-slate-500 hover:text-slate-900 hover:bg-slate-100/60'
                    : 'text-white/55 hover:text-white hover:bg-white/[0.04]'
              )}
            >
              {label}
            </Link>
          ))}
          <div className={clsx('h-5 w-px mx-1', light ? 'bg-slate-200' : 'bg-white/[0.08]')} />
          {DEV_LINKS.map(({ href, label }) => (
            <Link
              key={href}
              href={href}
              className={clsx(
                'hidden text-sm px-3 py-2 rounded-lg transition-colors xl:inline-flex',
                light
                  ? 'text-slate-400 hover:text-slate-600 hover:bg-slate-100/50'
                  : 'text-white/30 hover:text-white/55 hover:bg-white/[0.03]',
                pathname === href && (light ? 'text-slate-600 bg-slate-100/60' : 'text-white/60 bg-white/[0.04]')
              )}
            >
              {label}
            </Link>
          ))}
        </div>
      </div>

      <div className="flex items-center gap-3">
        {rightSlot || (
          <Link href="/#get-pro" className="btn btn-primary py-2 px-5 text-sm">
            Get Pro
          </Link>
        )}
        <button
          type="button"
          onClick={() => setMobileOpen((open) => !open)}
          aria-expanded={mobileOpen}
          aria-controls="mobile-nav"
          aria-label={mobileOpen ? 'Close navigation menu' : 'Open navigation menu'}
          className={clsx(
            'md:hidden inline-flex items-center justify-center w-10 h-10 rounded-lg transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-amber-500/50',
            light
              ? 'text-slate-500 hover:text-slate-900 hover:bg-slate-100'
              : 'text-white/70 hover:text-white hover:bg-white/[0.05]'
          )}
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
          className={clsx(
            'md:hidden w-full mt-3 flex flex-col gap-1 border-t pt-3',
            light ? 'border-slate-200' : 'border-white/[0.05]'
          )}
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
                  ? light
                    ? 'text-slate-900 bg-slate-100'
                    : 'text-white/90 bg-white/[0.05]'
                  : light
                    ? 'text-slate-500 hover:text-slate-800 hover:bg-slate-100/60'
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
