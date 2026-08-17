'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useState, useEffect } from 'react';
import { clsx } from 'clsx';
import { GitFork, Play } from 'lucide-react';

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
      <div className="flex justify-between items-center px-8 py-5 max-w-[1440px] mx-auto">
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
        <div className="flex items-center gap-3">
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
            href="/dashboard"
            className="px-5 py-2.5 rounded-lg font-bold text-sm transition-all duration-200 active:scale-95 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#6af2de]"
            style={{ background: '#6af2de', color: '#021a18' }}
          >
            Open dashboard
          </Link>
        </div>
      </div>
    </nav>
  );
}
