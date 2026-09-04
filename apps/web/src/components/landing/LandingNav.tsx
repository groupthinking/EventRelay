'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useState, useEffect } from 'react';
import { clsx } from 'clsx';
import { GitFork, Menu, Play, X } from 'lucide-react';

const NAV_LINKS = [
  { href: '/#features', label: 'Features', page: '/features' },
  { href: '/#workflow', label: 'How it works' },
  { href: '/pricing', label: 'Pricing', page: '/pricing' },
  { href: '/#contact', label: 'Contact' },
];

const REPO_URL = 'https://github.com/groupthinking/EventRelay';

export default function LandingNav() {
  const [scrolled, setScrolled] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const pathname = usePathname();

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 40);
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  return (
    <nav
      aria-label="Primary"
      className="fixed top-0 left-0 right-0 z-50 transition-all duration-500"
      style={{
        background: scrolled
          ? 'rgba(5, 5, 8, 0.92)'
          : 'transparent',
        backdropFilter: scrolled ? 'blur(24px)' : 'none',
        WebkitBackdropFilter: scrolled ? 'blur(24px)' : 'none',
        borderBottom: scrolled ? '1px solid rgba(106,242,222,0.08)' : '1px solid transparent',
      }}
    >
      <div className="mx-auto flex max-w-[1440px] items-center justify-between px-4 py-4 sm:px-6 md:px-8 md:py-5">
        {/* Logo */}
        <Link href="/" className="flex items-center gap-2.5 group focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#6af2de] rounded-lg" aria-label="UVAI home">
          <span
            className="inline-flex items-center justify-center w-8 h-8 rounded-lg transition-all duration-300 group-hover:scale-110"
            style={{ border: '2px solid #6af2de', color: '#6af2de' }}
            aria-hidden
          >
            <Play className="h-3.5 w-3.5" fill="currentColor" aria-hidden="true" />
          </span>
          <span className="text-xl font-black tracking-tight font-heading text-ink">UVAI</span>
        </Link>

        {/* Center nav links */}
        <div className="hidden md:flex gap-1 items-center">
          {NAV_LINKS.map((l) => {
            const isActive = l.page === pathname;
            return (
              <Link
                key={l.href}
                href={l.href}
                className={clsx(
                  'text-sm px-4 py-2 rounded-lg transition-all duration-200 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#6af2de]',
                  isActive
                    ? 'text-ink/90 bg-white/[0.06]'
                    : 'text-ink/50 hover:text-ink/90 hover:bg-white/[0.04]'
                )}
              >
                {l.label}
              </Link>
            );
          })}
        </div>

        {/* Right actions */}
        <div className="flex items-center gap-2 sm:gap-3">
          <a
            href={REPO_URL}
            target="_blank"
            rel="noopener noreferrer"
            aria-label="EventRelay source code on GitHub (opens in new tab)"
            className="hidden sm:inline-flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200 text-ink/50 hover:text-ink/80 border border-transparent hover:border-white/10 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#6af2de]"
          >
            <GitFork className="h-3.5 w-3.5 opacity-70" aria-hidden="true" />
            GitHub
          </a>
          <Link
            href="/"
            className="hidden rounded-lg px-5 py-2.5 text-sm font-bold transition-all duration-200 active:scale-95 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#6af2de] sm:inline-flex"
            style={{ background: '#6af2de', color: '#021a18' }}
          >
            Open studio
          </Link>
          <button
            type="button"
            aria-expanded={mobileOpen}
            aria-controls="mobile-navigation"
            aria-label={mobileOpen ? 'Close navigation' : 'Open navigation'}
            onClick={() => setMobileOpen((open) => !open)}
            className="inline-flex min-h-11 min-w-11 items-center justify-center rounded-lg border border-white/10 text-ink/70 transition-colors hover:bg-white/[0.06] hover:text-ink focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#6af2de] md:hidden"
          >
            {mobileOpen ? <X className="h-5 w-5" aria-hidden="true" /> : <Menu className="h-5 w-5" aria-hidden="true" />}
          </button>
        </div>
      </div>
      {mobileOpen && (
        <div id="mobile-navigation" className="border-t border-white/[0.08] bg-[#050508]/95 px-4 pb-5 pt-3 backdrop-blur-2xl md:hidden">
          <div className="mx-auto flex max-w-[1440px] flex-col gap-1">
            {NAV_LINKS.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                onClick={() => setMobileOpen(false)}
                className="flex min-h-11 items-center rounded-lg px-3 text-sm font-medium text-ink/70 transition-colors hover:bg-white/[0.06] hover:text-ink focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#6af2de]"
              >
                {link.label}
              </Link>
            ))}
            <Link
              href="/"
              onClick={() => setMobileOpen(false)}
              className="evidence-primary-button mt-2 flex min-h-11 items-center justify-center rounded-lg px-5 text-sm font-bold"
            >
              Open studio
            </Link>
          </div>
        </div>
      )}
    </nav>
  );
}
