import Link from 'next/link';
import { CONTACT_EMAIL } from '@/lib/constants';

const REPO_URL = 'https://github.com/groupthinking/EventRelay';

export default function LandingFooter() {
  return (
    <footer
      className="py-12 px-8"
      style={{ borderTop: '1px solid rgba(255,255,255,0.05)', background: 'rgba(5,5,8,1)' }}
    >
      <div className="max-w-[1440px] mx-auto flex flex-col md:flex-row items-start md:items-center justify-between gap-8">
        {/* Brand */}
        <div className="flex items-center gap-2.5">
          <span
            className="inline-flex items-center justify-center w-7 h-7 rounded-lg"
            style={{ border: '1.5px solid rgba(106,242,222,0.4)', color: '#6af2de' }}
            aria-hidden
          >
            <svg width="11" height="11" viewBox="0 0 24 24" fill="currentColor">
              <path d="M8 5v14l11-7z" />
            </svg>
          </span>
          <div>
            <p className="font-heading font-black text-base text-ink leading-none">UVAI</p>
            <p className="text-[10px] text-ink/25 mt-0.5">EventRelay open-source · MIT</p>
          </div>
        </div>

        {/* Links */}
        <nav className="flex flex-wrap gap-6" aria-label="Footer navigation">
          <Link href="/" className="text-sm text-ink/35 hover:text-ink/70 transition-colors">
            Studio
          </Link>
          <Link href="/features" className="text-sm text-ink/35 hover:text-ink/70 transition-colors">
            Features
          </Link>
          <Link href="/pricing" className="text-sm text-ink/35 hover:text-ink/70 transition-colors">
            Pricing
          </Link>
          <a
            href={REPO_URL}
            target="_blank"
            rel="noopener noreferrer"
            className="text-sm text-ink/35 hover:text-ink/70 transition-colors"
          >
            GitHub
          </a>
          <a
            href={`mailto:${CONTACT_EMAIL}`}
            className="text-sm text-ink/35 hover:text-ink/70 transition-colors"
          >
            Contact
          </a>
          <Link href="/privacy" className="text-sm text-ink/35 hover:text-ink/70 transition-colors">
            Privacy
          </Link>
          <Link href="/terms" className="text-sm text-ink/35 hover:text-ink/70 transition-colors">
            Terms
          </Link>
        </nav>

        <p className="text-xs text-ink/20">© 2026 UVAI. MIT licensed.</p>
      </div>
    </footer>
  );
}
