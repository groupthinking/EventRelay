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
    <div className="min-h-screen bg-void text-ink">
      <Nav />
      <main className="mx-auto max-w-3xl px-6 py-20">
        <header className="mb-12">
          <p className="text-xs uppercase tracking-[0.2em] text-ink/40">Legal</p>
          <h1 className="mt-2 font-heading text-4xl font-black">Privacy Policy</h1>
          <p className="mt-3 text-sm text-ink/50">Last updated: {LAST_UPDATED}</p>
        </header>

        <div className="prose prose-invert space-y-8 text-ink/80">
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
            <h2 className="font-heading text-2xl font-bold text-ink">What we process</h2>
            <ul className="list-disc space-y-2 pl-6">
              <li>
                <strong>YouTube URLs you submit.</strong> We resolve metadata
                and transcripts via the public YouTube APIs and our
                transcription pipeline.
              </li>
              <li>
                <strong>Derived artifacts.</strong> Transcripts, extracted
                events, embeddings, and agent traces produced while running
                your request.
              </li>
              <li>
                <strong>Operational telemetry.</strong> Anonymous performance
                and error data via Vercel Analytics and Speed Insights. We do
                not sell this data.
              </li>
            </ul>
          </section>

          <section>
            <h2 className="font-heading text-2xl font-bold text-ink">What we do not do</h2>
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
            <h2 className="font-heading text-2xl font-bold text-ink">Third-party processors</h2>
            <p>
              UVAI routes inference through Gemini, OpenAI, Anthropic, or Grok
              depending on the task. Your input may be transmitted to one of
              these providers under their respective terms. Hosting is on
              Vercel.
            </p>
          </section>

          <section>
            <h2 className="font-heading text-2xl font-bold text-ink">Your rights</h2>
            <p>
              You can request deletion of artifacts associated with your
              account by emailing{' '}
              <a className="text-teal-400 hover:underline" href={`mailto:${CONTACT_EMAIL}`}>
                {CONTACT_EMAIL}
              </a>
              . Because UVAI is open source under MIT, you can also self-host
              and retain full control.
            </p>
          </section>

          <section>
            <h2 className="font-heading text-2xl font-bold text-ink">Contact</h2>
            <p>
              Questions about this policy:{' '}
              <a className="text-teal-400 hover:underline" href={`mailto:${CONTACT_EMAIL}`}>
                {CONTACT_EMAIL}
              </a>
              . See also our{' '}
              <Link className="text-teal-400 hover:underline" href="/terms">
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
