import Link from 'next/link';
import { clsx } from 'clsx';
import { STUDIO_PRODUCT_TAGLINE } from '@/lib/studio-pipeline-status';

const PRODUCT_LINKS = [
  { label: 'Home', href: '/' },
  { label: 'Studio', href: '/studio' },
  { label: 'Pricing', href: '/pricing' },
  { label: 'API Docs', href: '/docs/api' },
];

const USE_CASES = ['Meeting Notes', 'Conference Talks', 'Tutorials', 'Product Demos', 'Podcasts'];

const EXTERNAL_LINKS = [
  { label: 'GitHub', href: 'https://github.com/groupthinking/EventRelay' },
];

interface FooterProps {
  /** Use the compact variant (just copyright + links) for app pages */
  variant?: 'full' | 'compact';
  /** Color tone. 'light' matches the card system (DESIGN_LANGUAGE.md); 'dark' is the legacy skin. */
  tone?: 'dark' | 'light';
}

/**
 * Renders the site footer in a compact or full layout.
 *
 * @param variant - The footer layout to render.
 */
export default function Footer({ variant = 'compact', tone = 'dark' }: FooterProps) {
  const light = tone === 'light';
  const heading = light ? 'text-slate-500' : 'text-white/40';
  const body = light ? 'text-slate-500' : 'text-white/35';
  const linkHover = light ? 'hover:text-slate-900' : 'hover:text-white/60';
  const faint = light ? 'text-slate-400' : 'text-white/25';
  const faintHover = light ? 'hover:text-slate-700' : 'hover:text-white/50';
  const border = light ? 'border-slate-200' : 'border-white/[0.06]';
  const borderSoft = light ? 'border-slate-200/70' : 'border-white/[0.05]';

  if (variant === 'compact') {
    return (
      <footer className={clsx('border-t py-6', border)}>
        <div className={clsx('max-w-6xl mx-auto px-6 flex items-center justify-between text-xs', faint)}>
          <span>UVAI video intelligence</span>
          <div className="flex items-center gap-4">
            <Link href="/studio" className={clsx('transition py-2 px-1', faintHover)}>
              Studio
            </Link>
            <Link href="/docs/api" className={clsx('transition py-2 px-1', faintHover)}>
              API
            </Link>
            <a
              href="https://github.com/groupthinking/EventRelay"
              target="_blank"
              rel="noopener noreferrer"
              className={clsx('transition py-2 px-1', faintHover)}
            >
              GitHub
            </a>
          </div>
        </div>
      </footer>
    );
  }

  return (
    <footer className={clsx('border-t py-10', border)}>
      <div className="max-w-6xl mx-auto px-6">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-8 mb-10">
          <div>
            <div className="flex items-center gap-2 mb-4">
              <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-amber-500 to-amber-600 flex items-center justify-center font-black text-xs text-white">
                U
              </div>
              <span className={clsx('font-bold text-sm', light ? 'text-slate-900' : 'text-white')}>UVAI</span>
            </div>
            <p className={clsx('text-xs leading-relaxed', light ? 'text-slate-400' : 'text-white/30')}>
              {STUDIO_PRODUCT_TAGLINE}
            </p>
          </div>
          <div>
            <div className={clsx('text-xs font-semibold uppercase tracking-wider mb-4', heading)}>
              Product
            </div>
            <ul className={clsx('space-y-2.5 text-xs', body)}>
              {PRODUCT_LINKS.map(({ label, href }) => (
                <li key={label}>
                  <Link href={href} className={clsx('transition', linkHover)}>
                    {label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>
          <div>
            <div className={clsx('text-xs font-semibold uppercase tracking-wider mb-4', heading)}>
              Use Cases
            </div>
            <ul className={clsx('space-y-2.5 text-xs', body)}>
              {USE_CASES.map((u) => (
                <li key={u}>
                  <span className="cursor-default">{u}</span>
                </li>
              ))}
            </ul>
          </div>
          <div>
            <div className={clsx('text-xs font-semibold uppercase tracking-wider mb-4', heading)}>
              Links
            </div>
            <ul className={clsx('space-y-2.5 text-xs', body)}>
              {EXTERNAL_LINKS.map(({ label, href }) => (
                <li key={label}>
                  <a
                    href={href}
                    target="_blank"
                    rel="noopener noreferrer"
                    className={clsx('transition', linkHover)}
                  >
                    {label}
                  </a>
                </li>
              ))}
            </ul>
          </div>
        </div>
        <div className={clsx('border-t pt-6 flex flex-col md:flex-row items-center justify-between gap-3 text-xs', borderSoft, faint)}>
          <span>© 2026 UVAI. MIT License.</span>
          <a
            href="https://github.com/groupthinking/EventRelay"
            target="_blank"
            rel="noopener noreferrer"
            className={clsx('transition', faintHover)}
          >
            Inspect current source on GitHub
          </a>
        </div>
      </div>
    </footer>
  );
}
