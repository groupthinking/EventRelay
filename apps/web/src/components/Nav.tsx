'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { clsx } from 'clsx';
import { useState } from 'react';
import { Menu, X } from 'lucide-react';

interface NavProps {
  /** Optional right-side content override */
  rightSlot?: React.ReactNode;
  /** Optional subtitle shown next to the logo */
  subtitle?: React.ReactNode;
  /** Whether to use the sticky/fixed variant */
  fixed?: boolean;
}

const NAV_LINKS = [
  { href: '/', label: 'Player & Studio' },
  { href: '/dashboard', label: 'Library' },
  { href: '/features', label: 'How It Works' },
  { href: '/pricing', label: 'Pricing' },
];

/**
 * Main navigation bar — warm editorial daylight aesthetic (inspired by Video.js v10 & LinkedIn Learning).
 */
export default function Nav({ rightSlot, subtitle, fixed = false }: NavProps) {
  const pathname = usePathname();
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <nav
      className={clsx(
        'flex flex-wrap items-center justify-between px-6 lg:px-10 py-3.5 border-b border-[#e4decb] z-50',
        fixed
          ? 'fixed top-0 left-0 right-0 bg-[#f5f1e8]/95 backdrop-blur-md'
          : 'bg-[#f5f1e8]/95 backdrop-blur-md'
      )}
    >
      <div className="flex items-center gap-6">
        <Link href="/" className="flex items-center gap-2.5 group">
          <div className="w-8 h-8 rounded-lg bg-[#171716] text-[#f5f1e8] flex items-center justify-center font-heading font-black text-base transition-transform group-hover:scale-105">
            U
          </div>
          <span className="font-heading font-black text-xl tracking-tight text-[#171716]">
            UVAI<span className="text-[#ff5500]">.</span>
          </span>
        </Link>

        {subtitle && (
          <>
            <div className="h-4 w-px bg-[#d6cfc0]" />
            <span className="text-[#57554f] font-medium text-sm">{subtitle}</span>
          </>
        )}

        <div className="hidden md:flex items-center gap-1 ml-2">
          {NAV_LINKS.map(({ href, label }) => {
            const active =
              href === '/'
                ? pathname === '/'
                : pathname === href || pathname.startsWith(`${href}/`);
            return (
              <Link
                key={href}
                href={href}
                aria-current={active ? 'page' : undefined}
                className={clsx(
                  'text-sm font-semibold px-3.5 py-2 rounded-lg transition-colors',
                  active
                    ? 'text-[#171716] bg-[#e8e2d5]'
                    : 'text-[#57554f] hover:text-[#171716] hover:bg-[#ebe5d8]'
                )}
              >
                {label}
              </Link>
            );
          })}
        </div>
      </div>

      <div className="flex items-center gap-3">
        {rightSlot || (
          <Link
            href="/"
            className="rounded-xl bg-[#ff5500] px-5 py-2 text-sm font-bold text-white transition-colors hover:bg-[#e04b00]"
          >
            Analyze a video
          </Link>
        )}
        <button
          type="button"
          onClick={() => setMobileOpen((open) => !open)}
          aria-expanded={mobileOpen}
          aria-controls="mobile-nav"
          aria-label={mobileOpen ? 'Close navigation menu' : 'Open navigation menu'}
          className="md:hidden inline-flex items-center justify-center w-10 h-10 rounded-lg text-[#171716] hover:bg-[#e8e2d5] transition-colors"
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
          className="md:hidden w-full mt-3 flex flex-col gap-1 border-t border-[#e4decb] pt-3"
        >
          {NAV_LINKS.map(({ href, label }) => (
            <Link
              key={href}
              href={href}
              onClick={() => setMobileOpen(false)}
              aria-current={pathname === href ? 'page' : undefined}
              className={clsx(
                'text-base font-semibold px-3.5 py-2.5 rounded-lg transition-colors',
                pathname === href
                  ? 'text-[#171716] bg-[#e8e2d5]'
                  : 'text-[#57554f] hover:text-[#171716] hover:bg-[#ebe5d8]'
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
