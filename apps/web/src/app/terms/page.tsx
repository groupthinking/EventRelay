import type { Metadata } from 'next';
import Link from 'next/link';
import Nav from '@/components/Nav';
import Footer from '@/components/Footer';
import { CONTACT_EMAIL } from '@/lib/constants';

export const metadata: Metadata = {
  title: 'Terms of Service',
  description:
    'Terms governing use of the UVAI hosted product. EventRelay is MIT-licensed and may be self-hosted at any time.',
  alternates: { canonical: '/terms' },
  robots: { index: true, follow: true },
};

const LAST_UPDATED = 'May 25, 2026';

export default function TermsPage() {
  return (
    <div className="min-h-screen bg-void text-ink">
      <Nav />
      <main className="mx-auto max-w-3xl px-6 py-20">
        <header className="mb-12">
          <p className="text-xs uppercase tracking-[0.2em] text-ink/40">Legal</p>
          <h1 className="mt-2 font-heading text-4xl font-black">Terms of Service</h1>
          <p className="mt-3 text-sm text-ink/50">Last updated: {LAST_UPDATED}</p>
        </header>

        <div className="prose prose-invert space-y-8 text-ink/80">
          <section>
            <p>
              By using the hosted UVAI product you agree to these terms. The
              underlying EventRelay code is open source under the MIT license;
              these terms apply specifically to the hosted product served from
              this domain.
            </p>
          </section>

          <section>
            <h2 className="font-heading text-2xl font-bold text-ink">Acceptable use</h2>
            <ul className="list-disc space-y-2 pl-6">
              <li>Only submit YouTube content you have the right to analyze.</li>
              <li>
                Do not attempt to exfiltrate the model, abuse the platform with
                automated scraping, or use UVAI to generate content that
                violates applicable law.
              </li>
              <li>
                Do not use UVAI to make consequential decisions about
                individuals without human review.
              </li>
            </ul>
          </section>

          <section>
            <h2 className="font-heading text-2xl font-bold text-ink">No warranty</h2>
            <p>
              UVAI is provided &ldquo;as is&rdquo; without warranty of any
              kind. AI outputs may be incorrect, incomplete, or biased — treat
              them as drafts requiring review. We are not liable for
              decisions made on the basis of automated output.
            </p>
          </section>

          <section>
            <h2 className="font-heading text-2xl font-bold text-ink">Your content</h2>
            <p>
              You retain ownership of any content you submit. By submitting,
              you grant UVAI a limited license to process that content solely
              for the purpose of fulfilling your request.
            </p>
          </section>

          <section>
            <h2 className="font-heading text-2xl font-bold text-ink">Changes</h2>
            <p>
              These terms may evolve as the product matures. Material changes
              will be flagged on this page with an updated revision date.
            </p>
          </section>

          <section>
            <h2 className="font-heading text-2xl font-bold text-ink">Contact</h2>
            <p>
              Questions:{' '}
              <a className="text-teal-400 hover:underline" href={`mailto:${CONTACT_EMAIL}`}>
                {CONTACT_EMAIL}
              </a>
              . See also our{' '}
              <Link className="text-teal-400 hover:underline" href="/privacy">
                Privacy Policy
              </Link>
              .
            </p>
          </section>
        </div>
      </main>
      <Footer />
    </div>
  );
}
