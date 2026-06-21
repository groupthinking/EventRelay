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
  { href: '/', label: 'Studio', hint: 'Local drafts' },
  { href: '/dashboard', label: 'Dashboard', hint: 'Live pipeline' },
  { href: '/dashboard/agents', label: 'Agents', hint: 'SSE graph' },
  { href: '/features', label: 'Features' },
  { href: '/pricing', label: 'Pricing' },
  { href: '/prototype', label: 'Prototype', hint: 'Design preview' },
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

        {/* Desktop links */}
        <div className="hidden md:flex items-center gap-1 ml-4">
          {NAV_LINKS.map(({ href, label, hint }) => (
            <Link
              key={href}
              href={href}
              title={hint}
              className={clsx(
                'text-sm px-3 py-2 rounded-lg transition-colors',
                pathname === href
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
