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