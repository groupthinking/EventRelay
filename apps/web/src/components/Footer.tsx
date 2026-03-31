import Link from 'next/link';

const PRODUCT_LINKS = [
  { label: 'Dashboard', href: '/dashboard' },
  { label: 'Features', href: '/features' },
  { label: 'Pricing', href: '/pricing' },
  { label: 'API Docs', href: '/playground' },
];

const USE_CASES = ['Meeting Notes', 'Conference Talks', 'Tutorials', 'Product Demos', 'Podcasts'];

const EXTERNAL_LINKS = [
  { label: 'GitHub', href: 'https://github.com/groupthinking/EventRelay' },
  { label: 'Product Hunt', href: 'https://www.producthunt.com' },
];

interface FooterProps {
  /** Use the compact variant (just copyright + links) for app pages */
  variant?: 'full' | 'compact';
}

export default function Footer({ variant = 'compact' }: FooterProps) {
  if (variant === 'compact') {
    return (
      <footer className="border-t border-white/[0.06] py-6">
        <div className="max-w-6xl mx-auto px-6 flex items-center justify-between text-xs text-white/25">
          <span>UVAI • Video to Software</span>
          <div className="flex items-center gap-4">
            <Link href="/features" className="hover:text-white/50 transition py-2 px-1">
              Features
            </Link>
            <Link href="/playground" className="hover:text-white/50 transition py-2 px-1">
              API
            </Link>
            <a
              href="https://github.com/groupthinking/EventRelay"
              target="_blank"
              rel="noopener noreferrer"
              className="hover:text-white/50 transition py-2 px-1"
            >
              GitHub
            </a>
          </div>
        </div>
      </footer>
    );
  }

  return (
    <footer className="border-t border-white/[0.06] py-10">
      <div className="max-w-6xl mx-auto px-6">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-8 mb-10">
          <div>
            <div className="flex items-center gap-2 mb-4">
              <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-primary-500 to-primary-600 flex items-center justify-center font-black text-xs">
                U
              </div>
              <span className="font-bold text-sm">UVAI</span>
            </div>
            <p className="text-xs text-white/30 leading-relaxed">
              AI-powered video intelligence for teams and individuals.
            </p>
          </div>
          <div>
            <div className="text-xs font-semibold text-white/40 uppercase tracking-wider mb-4">
              Product
            </div>
            <ul className="space-y-2.5 text-xs text-white/35">
              {PRODUCT_LINKS.map(({ label, href }) => (
                <li key={label}>
                  <Link href={href} className="hover:text-white/60 transition">
                    {label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>
          <div>
            <div className="text-xs font-semibold text-white/40 uppercase tracking-wider mb-4">
              Use Cases
            </div>
            <ul className="space-y-2.5 text-xs text-white/35">
              {USE_CASES.map((u) => (
                <li key={u}>
                  <span className="cursor-default">{u}</span>
                </li>
              ))}
            </ul>
          </div>
          <div>
            <div className="text-xs font-semibold text-white/40 uppercase tracking-wider mb-4">
              Links
            </div>
            <ul className="space-y-2.5 text-xs text-white/35">
              {EXTERNAL_LINKS.map(({ label, href }) => (
                <li key={label}>
                  <a
                    href={href}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="hover:text-white/60 transition"
                  >
                    {label}
                  </a>
                </li>
              ))}
            </ul>
          </div>
        </div>
        <div className="border-t border-white/[0.05] pt-6 flex flex-col md:flex-row items-center justify-between gap-3 text-xs text-white/25">
          <span>© 2026 UVAI. MIT License.</span>
          <div className="flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse" />
            <span>All systems operational</span>
          </div>
        </div>
      </div>
    </footer>
  );
}
