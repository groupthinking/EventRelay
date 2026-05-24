'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { clsx } from 'clsx';

interface NavProps {
  /** Optional right-side content override (e.g., processing status badge) */
  rightSlot?: React.ReactNode;
  /** Optional subtitle shown next to the logo (e.g., "Dashboard", breadcrumb JSX) */
  subtitle?: React.ReactNode;
  /** Whether to use the sticky/fixed variant (for marketing pages) */
  fixed?: boolean;
}

const NAV_LINKS = [
  { href: '/features', label: 'Features' },
  { href: '/pricing', label: 'Pricing' },
  { href: '/prototype', label: 'Prototype' },
  { href: '/playground', label: 'API' },
];

export default function Nav({ rightSlot, subtitle, fixed = false }: NavProps) {
  const pathname = usePathname();

  return (
    <nav
      className={clsx(
        'flex items-center justify-between px-6 lg:px-12 py-4 border-b border-white/[0.05] z-50',
        fixed
          ? 'fixed top-0 left-0 right-0 bg-surface-950/80 backdrop-blur-xl'
          : 'bg-surface-950/80 backdrop-blur-xl'
      )}
    >
      <div className="flex items-center gap-4">
        <Link href="/" className="flex items-center gap-3 group">
          <div
            className="w-8 h-8 rounded-lg flex items-center justify-center transition-transform duration-200 group-hover:scale-105"
            style={{ border: '2px solid #6af2de', color: '#6af2de' }}
            aria-hidden
          >
            <svg width="13" height="13" viewBox="0 0 24 24" fill="currentColor">
              <path d="M8 5v14l11-7z" />
            </svg>
          </div>
          <span className="font-bold text-lg tracking-tight font-heading">UVAI</span>
        </Link>

        {subtitle && (
          <>
            <div className="h-5 w-px bg-white/[0.08]" />
            <span className="text-white/50 font-medium text-sm">{subtitle}</span>
          </>
        )}

        {/* Desktop links */}
        <div className="hidden md:flex items-center gap-1 ml-4">
          {NAV_LINKS.map(({ href, label }) => (
            <Link
              key={href}
              href={href}
              className={clsx(
                'text-sm px-3 py-2 rounded-lg transition-colors',
                pathname === href
                  ? 'text-white/90 bg-white/[0.05]'
                  : 'text-white/40 hover:text-white/70 hover:bg-white/[0.03]'
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
            Dashboard
          </Link>
        )}
      </div>
    </nav>
  );
}
