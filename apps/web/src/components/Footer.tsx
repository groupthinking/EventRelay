import Link from 'next/link';
import { STUDIO_PRODUCT_TAGLINE } from '@/lib/studio-pipeline-status';

const PRODUCT_LINKS = [
  { label: 'Home', href: '/' },
  { label: 'Studio', href: '/studio' },
  { label: 'Pricing', href: '/pricing' },
  { label: 'API Docs', href: '/docs/api' },
];

const USE_CASES = ['Meeting Notes', 'Conference Talks', 'Tutorials', 'Product Demos', 'Podcasts'];

interface FooterProps {
  /** Use the compact variant (just copyright + links) for app pages */
  variant?: 'full' | 'compact';
}

/**
 * Quiet footer. Warm paper, faint type. Nothing shouts.
 */
export default function Footer({ variant = 'compact' }: FooterProps) {
  if (variant === 'compact') {
    return (
      <footer style={{ borderTop: '1px solid var(--uvai-border)' }} className="py-6">
        <div className="max-w-6xl mx-auto px-6 flex items-center justify-between text-xs" style={{ color: 'var(--uvai-ink-faint)' }}>
          <span>UVAI video intelligence</span>
          <div className="flex items-center gap-5">
            <Link href="/studio" className="transition py-2 px-1 hover:opacity-70">Studio</Link>
            <Link href="/docs/api" className="transition py-2 px-1 hover:opacity-70">API</Link>
            <a href="https://github.com/groupthinking/EventRelay" target="_blank" rel="noopener noreferrer" className="transition py-2 px-1 hover:opacity-70">
              GitHub
            </a>
          </div>
        </div>
      </footer>
    );
  }

  return (
    <footer style={{ borderTop: '1px solid var(--uvai-border)' }} className="py-12">
      <div className="max-w-6xl mx-auto px-6">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-8 mb-10">
          <div>
            <div className="flex items-center gap-2 mb-4">
              <div className="w-7 h-7 rounded-lg flex items-center justify-center text-xs font-semibold text-white" style={{ background: 'var(--uvai-accent)' }}>
                U
              </div>
              <span className="font-semibold text-sm" style={{ color: 'var(--uvai-ink)' }}>UVAI</span>
            </div>
            <p className="text-xs leading-relaxed" style={{ color: 'var(--uvai-ink-faint)' }}>
              {STUDIO_PRODUCT_TAGLINE}
            </p>
          </div>
          <div>
            <div className="uvai-label mb-4">Product</div>
            <ul className="space-y-2.5 text-sm" style={{ color: 'var(--uvai-ink-soft)' }}>
              {PRODUCT_LINKS.map(({ label, href }) => (
                <li key={label}>
                  <Link href={href} className="transition hover:opacity-70">{label}</Link>
                </li>
              ))}
            </ul>
          </div>
          <div>
            <div className="uvai-label mb-4">Use Cases</div>
            <ul className="space-y-2.5 text-sm" style={{ color: 'var(--uvai-ink-soft)' }}>
              {USE_CASES.map((u) => (
                <li key={u}><span className="cursor-default">{u}</span></li>
              ))}
            </ul>
          </div>
          <div>
            <div className="uvai-label mb-4">Links</div>
            <ul className="space-y-2.5 text-sm" style={{ color: 'var(--uvai-ink-soft)' }}>
              <li>
                <a href="https://github.com/groupthinking/EventRelay" target="_blank" rel="noopener noreferrer" className="transition hover:opacity-70">
                  GitHub
                </a>
              </li>
            </ul>
          </div>
        </div>
        <div className="pt-6 flex flex-col md:flex-row items-center justify-between gap-3 text-xs" style={{ borderTop: '1px solid var(--uvai-border)', color: 'var(--uvai-ink-faint)' }}>
          <span>© 2026 UVAI. MIT License.</span>
          <a href="https://github.com/groupthinking/EventRelay" target="_blank" rel="noopener noreferrer" className="transition hover:opacity-70">
            Inspect current source on GitHub
          </a>
        </div>
      </div>
    </footer>
  );
}
