'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useState } from 'react';
import { Menu, X, Film } from 'lucide-react';

interface NavProps {
  rightSlot?: React.ReactNode;
  subtitle?: React.ReactNode;
  fixed?: boolean;
}

const NAV_LINKS = [
  { href: '/', label: 'Home' },
  { href: '/studio', label: 'Studio' },
  { href: '/pricing', label: 'Pricing' },
];

function isNavActive(pathname: string, href: string): boolean {
  if (href === '/') return pathname === '/';
  return pathname === href || pathname.startsWith(`${href}/`);
}

/**
 * Minimal top bar. Warm paper, quiet type, one accent CTA.
 * Muse design language: nothing shouts, everything breathes.
 */
export default function Nav({ rightSlot, subtitle, fixed = false }: NavProps) {
  const pathname = usePathname();
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <nav
      className="template-nav flex flex-wrap items-center justify-between px-4 sm:px-6 lg:px-10 py-3 z-50"
      style={{
        borderBottom: '1px solid var(--uvai-border)',
        background: 'var(--uvai-bg)',
        position: fixed ? 'fixed' : undefined,
        top: fixed ? 0 : undefined,
        left: fixed ? 0 : undefined,
        right: fixed ? 0 : undefined,
      }}
    >
      <div className="flex items-center gap-6">
        <Link href="/" className="flex items-center gap-2.5">
          <div
            className="w-8 h-8 rounded-lg flex items-center justify-center text-white font-semibold text-sm"
            style={{ background: 'var(--uvai-accent)' }}
          >
            <Film size={18} aria-hidden="true" />
          </div>
          <span className="font-semibold text-lg tracking-tight" style={{ color: 'var(--uvai-ink)' }}>
            UVAI
          </span>
        </Link>

        {subtitle && (
          <span className="text-sm" style={{ color: 'var(--uvai-ink-soft)' }}>{subtitle}</span>
        )}

        <div className="hidden md:flex items-center gap-1">
          {NAV_LINKS.map(({ href, label }) => {
            const active = isNavActive(pathname, href);
            return (
              <Link
                key={href}
                href={href}
                aria-current={active ? 'page' : undefined}
                className="text-sm px-3 py-2 rounded-lg transition-colors"
                style={{
                  color: active ? 'var(--uvai-ink)' : 'var(--uvai-ink-soft)',
                  background: active ? 'var(--uvai-surface-warm)' : 'transparent',
                }}
              >
                {label}
              </Link>
            );
          })}
        </div>
      </div>

      <div className="flex items-center gap-3">
        {rightSlot || (
          <Link href="/#get-pro" className="uvai-btn uvai-btn-primary py-2 px-5 text-sm">
            Get Pro
          </Link>
        )}
        <button
          type="button"
          onClick={() => setMobileOpen((open) => !open)}
          aria-expanded={mobileOpen}
          aria-controls="mobile-nav"
          aria-label={mobileOpen ? 'Close navigation menu' : 'Open navigation menu'}
          className="md:hidden inline-flex items-center justify-center w-10 h-10 rounded-lg"
          style={{ color: 'var(--uvai-ink-soft)' }}
        >
          {mobileOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
        </button>
      </div>

      {mobileOpen && (
        <div id="mobile-nav" className="md:hidden w-full mt-3 flex flex-col gap-1 pt-3" style={{ borderTop: '1px solid var(--uvai-border)' }}>
          {NAV_LINKS.map(({ href, label }) => (
            <Link
              key={href}
              href={href}
              onClick={() => setMobileOpen(false)}
              className="text-sm px-3 py-2.5 rounded-lg"
              style={{ color: isNavActive(pathname, href) ? 'var(--uvai-ink)' : 'var(--uvai-ink-soft)' }}
            >
              {label}
            </Link>
          ))}
        </div>
      )}
    </nav>
  );
}
