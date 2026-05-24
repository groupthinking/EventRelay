'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useState, useEffect } from 'react';
import { clsx } from 'clsx';

const NAV_LINKS = [
  { href: '/#features', label: 'Features', page: '/features' },
  { href: '/#workflow', label: 'How it works' },
  { href: '/pricing', label: 'Pricing', page: '/pricing' },
  { href: '/#contact', label: 'Contact' },
];

const REPO_URL = 'https://github.com/groupthinking/EventRelay';

export default function LandingNav() {
  const [scrolled, setScrolled] = useState(false);
  const pathname = usePathname();

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 40);
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  return (
    <nav
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
      <div className="flex justify-between items-center px-8 py-5 max-w-[1440px] mx-auto">
        {/* Logo */}
        <Link href="/" className="flex items-center gap-2.5 group">
          <span
            className="inline-flex items-center justify-center w-8 h-8 rounded-lg transition-all duration-300 group-hover:scale-110"
            style={{ border: '2px solid #6af2de', color: '#6af2de' }}
            aria-hidden
          >
            <svg width="13" height="13" viewBox="0 0 24 24" fill="currentColor">
              <path d="M8 5v14l11-7z" />
            </svg>
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
                  'text-sm px-4 py-2 rounded-lg transition-all duration-200',
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
        <div className="flex items-center gap-3">
          <a
            href={REPO_URL}
            target="_blank"
            rel="noopener noreferrer"
            className="hidden sm:inline-flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200 text-ink/50 hover:text-ink/80 border border-transparent hover:border-white/10"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor" className="opacity-70" aria-hidden>
              <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0 0 24 12c0-6.63-5.37-12-12-12z" />
            </svg>
            GitHub
          </a>
          <Link
            href="/dashboard"
            className="px-5 py-2.5 rounded-lg font-bold text-sm transition-all duration-200 active:scale-95"
            style={{ background: '#6af2de', color: '#021a18' }}
          >
            Open dashboard
          </Link>
        </div>
      </div>
    </nav>
  );
}
