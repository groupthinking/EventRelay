import type { Metadata } from 'next';
import Link from 'next/link';
import Nav from '@/components/Nav';
import Footer from '@/components/Footer';
import { CONTACT_EMAIL } from '@/lib/constants';

export const metadata: Metadata = {
  title: 'Privacy Policy',
  description:
    'How UVAI (EventRelay) collects, processes, and protects data when you analyze YouTube videos and use our AI pipelines.',
  alternates: { canonical: '/privacy' },
  robots: { index: true, follow: true },
};

const LAST_UPDATED = 'May 25, 2026';

export default function PrivacyPage() {
  return (
    <div className="min-h-screen bg-[var(--uvai-bg)] text-[var(--uvai-ink)]">
      <Nav />
      <main className="mx-auto max-w-3xl px-6 py-16">
        <header className="mb-10 border-b border-[var(--uvai-border-strong)] pb-8">
          <nav aria-label="Breadcrumb" className="text-xs text-[var(--uvai-ink-faint)]">
            <ol className="flex items-center gap-2">
              <li>
                <Link className="hover:text-[var(--uvai-ink)] hover:underline" href="/">
                  Home
                </Link>
              </li>
              <li aria-hidden="true">/</li>
              <li>Legal</li>
              <li aria-hidden="true">/</li>
              <li aria-current="page" className="text-[var(--uvai-ink-soft)]">
                Privacy Policy
              </li>
            </ol>
          </nav>
          <h1 className="mt-4 text-4xl font-medium tracking-tight">Privacy Policy</h1>
          <p className="mt-3 text-sm text-[var(--uvai-ink-soft)]">Last updated: {LAST_UPDATED}</p>
        </header>

        <div className="space-y-6 text-[var(--uvai-ink-soft)] leading-7 [&_section]:rounded-xl [&_section]:border [&_section]:border-[var(--uvai-border)] [&_section]:bg-[var(--uvai-surface)] [&_section]:p-6">
          <section>
            <p>
              UVAI is an open-source video intelligence product operated by the
              EventRelay project. This page describes, in plain language, what
              data we touch when you use the hosted UVAI product. It is not
              legal advice, and it will be replaced with a formal policy before
              we collect data from organizations under contract.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-medium tracking-tight text-[var(--uvai-ink)] mb-3">What we process</h2>
            <ul className="list-disc space-y-2 pl-6">
              <li>
                <strong className="text-[var(--uvai-ink)]">YouTube URLs you submit.</strong> We resolve metadata
                and transcripts via the public YouTube APIs and our
                transcription pipeline.
              </li>
              <li>
                <strong className="text-[var(--uvai-ink)]">Derived artifacts.</strong> Transcripts, extracted
                events, embeddings, and agent traces produced while running
                your request.
              </li>
              <li>
                <strong className="text-[var(--uvai-ink)]">Operational telemetry.</strong> Anonymous performance
                and error data via Vercel Analytics and Speed Insights. We do
                not sell this data.
              </li>
            </ul>
          </section>

          <section>
            <h2 className="text-xl font-medium tracking-tight text-[var(--uvai-ink)] mb-3">What we do not do</h2>
            <ul className="list-disc space-y-2 pl-6">
              <li>We do not sell personal data.</li>
              <li>We do not train foundation models on your inputs.</li>
              <li>
                We do not store credentials for third-party services in our
                browser bundles.
              </li>
            </ul>
          </section>

          <section>
            <h2 className="text-xl font-medium tracking-tight text-[var(--uvai-ink)] mb-3">Third-party processors</h2>
            <p>
              UVAI routes inference through Gemini, OpenAI, Anthropic, or Grok
              depending on the task. Your input may be transmitted to one of
              these providers under their respective terms. Hosting is on
              Vercel.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-medium tracking-tight text-[var(--uvai-ink)] mb-3">Your rights</h2>
            <p>
              You can request deletion of artifacts associated with your
              account by emailing{' '}
              <a className="text-[var(--uvai-accent-ink,var(--uvai-accent))] underline-offset-4 hover:underline" href={`mailto:${CONTACT_EMAIL}`}>
                {CONTACT_EMAIL}
              </a>
              . Because UVAI is open source under MIT, you can also self-host
              and retain full control.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-medium tracking-tight text-[var(--uvai-ink)] mb-3">Contact</h2>
            <p>
              Questions about this policy:{' '}
              <a className="text-[var(--uvai-accent-ink,var(--uvai-accent))] underline-offset-4 hover:underline" href={`mailto:${CONTACT_EMAIL}`}>
                {CONTACT_EMAIL}
              </a>
              . See also our{' '}
              <Link className="text-[var(--uvai-accent-ink,var(--uvai-accent))] underline-offset-4 hover:underline" href="/terms">
                Terms of Service
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
