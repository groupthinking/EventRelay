import type { Metadata } from 'next';
import Nav from '@/components/Nav';
import Footer from '@/components/Footer';
import HomePasteForm from '@/components/home/HomePasteForm';
import HomeProCheckout from '@/components/home/HomeProCheckout';
import HomeTemplateShell from '@/components/home/HomeTemplateShell';
import '@/components/home/home-template.css';
import {
  WORKFLOW_PRO_PRODUCT_NAME,
  workflowProPriceLabel,
} from '@/lib/billing/checkout-config';
import { customBadge } from '@/flags';

export const metadata: Metadata = {
  title: 'UVAI — YouTube URL to Studio',
  description:
    'Paste a YouTube URL to open a hashed Video Pack in Studio. Transcript quality varies by source.',
  alternates: { canonical: '/' },
};

const OFFERS = [
  {
    name: WORKFLOW_PRO_PRODUCT_NAME,
    price: `${workflowProPriceLabel(false)} · ${workflowProPriceLabel(true)}`,
  },
  {
    name: 'Ship',
    price: 'per-job quote',
  },
  {
    name: 'Maintain',
    price: '$199/mo',
  },
] as const;

/**
 * OpenAI Responses starter shell adapted to the existing UVAI entry workflow.
 * Source intake remains primary; workflow context is separate from plan selection.
 */
export default async function HomePage() {
  const showCustomBadge = await customBadge();

  return (
    <main className="min-h-screen" style={{ background: 'var(--uvai-bg)' }}>
      <Nav />

      <section aria-labelledby="home-heading" className="px-4 sm:px-6 lg:px-12 pb-20 pt-8 md:pt-12">
        <div className="mx-auto max-w-6xl">
          <HomeTemplateShell context={
            <div>
              <p className="uvai-label">Source → context → next step</p>
              <h2 className="mt-4 text-xl">A workspace for what comes next.</h2>
              <p className="mt-3 text-sm leading-relaxed" style={{ color: 'var(--uvai-ink-soft)' }}>
                Start with the source. Review the evidence before deciding what to build.
              </p>
              <ol className="mt-8 space-y-8">
                <li className="home-workflow-step">
                  <span className="home-step-number" aria-hidden="true">01</span>
                  <div><h3 className="text-base font-medium">Bring a YouTube URL</h3>
                    <p className="mt-2 text-sm" style={{ color: 'var(--uvai-ink-soft)' }}>A tutorial, product walkthrough, or process recording. Source access and transcript availability affect the result.</p></div>
                </li>
                <li className="home-workflow-step">
                  <span className="home-step-number" aria-hidden="true">02</span>
                  <div><h3 className="text-base font-medium">Inspect the Video Pack</h3>
                    <p className="mt-2 text-sm" style={{ color: 'var(--uvai-ink-soft)' }}>Studio organizes the source into a hashed Video Pack with events, tools, and proposed work.</p></div>
                </li>
                <li className="home-workflow-step">
                  <span className="home-step-number" aria-hidden="true">03</span>
                  <div><h3 className="text-base font-medium">Review your next move</h3>
                    <p className="mt-2 text-sm" style={{ color: 'var(--uvai-ink-soft)' }}>Ask questions and inspect build rails. Proposed work is not a verified deployment.</p></div>
                </li>
              </ol>
              <div className="mt-8 border-t pt-5 text-xs leading-relaxed" style={{ borderColor: 'var(--uvai-border)', color: 'var(--uvai-ink-soft)' }}>
                Your source stays the reference. Missing evidence should remain an open question.
              </div>
            </div>
          }>
            <div>
              <p className="uvai-label">
                Universal Video Action Intelligence
              </p>
              {showCustomBadge && (
                <p className="mt-4 inline-flex rounded-full px-3 py-1 text-xs font-medium"
                   style={{ border: '1px solid var(--uvai-border)', background: 'var(--uvai-accent-soft)', color: 'var(--uvai-accent)' }}>
                  New: configurable with Vercel Flags
                </p>
              )}

              <h1 id="home-heading" className="mt-6 max-w-2xl text-4xl sm:text-5xl md:text-6xl" style={{ color: 'var(--uvai-ink)' }}>
                Your videos know what to do next.
              </h1>
              <p className="mt-6 max-w-xl text-lg leading-relaxed" style={{ color: 'var(--uvai-ink-soft)' }}>
                Paste a YouTube URL. UVAI pulls the events, actions, and decisions out of it,
                prepares proposed work and build rails for you to review in Studio.
              </p>
              <p className="mt-3 text-sm" style={{ color: 'var(--uvai-ink-faint)' }}>
                Transcript quality varies by source. No guaranteed production outcome.
              </p>

              <div className="home-source-composer w-full max-w-xl">
                <HomePasteForm />
              </div>
            </div>

          </HomeTemplateShell>

          <section id="get-pro" aria-labelledby="workflow-pro-heading" className="mt-10 grid grid-cols-1 gap-6 lg:grid-cols-2 lg:items-center">
            <div className="px-2 sm:px-6">
              <p className="uvai-label">Workflow Pro</p>
              <h2 id="workflow-pro-heading" className="font-display mt-3 text-3xl" style={{ color: 'var(--uvai-ink)' }}>
                Get Pro through the existing checkout.
              </h2>
              <p className="mt-3 max-w-lg text-sm leading-relaxed" style={{ color: 'var(--uvai-ink-soft)' }}>
                Start with a source in Studio. When you need Workflow Pro, choose a billing cadence.
                Stripe confirms the amount and renewal terms before payment.
              </p>
            </div>
            <HomeProCheckout />
          </section>

          {/* Offers */}
          <section aria-labelledby="offer-summary-heading" className="mt-12">
            <div className="uvai-card px-8 py-10 sm:px-10">
              <p className="uvai-label">Options</p>
              <h2 id="offer-summary-heading" className="font-display mt-3 text-3xl" style={{ color: 'var(--uvai-ink)' }}>
                Start in Studio, then choose the right level of support.
              </h2>
              <p className="mt-3 max-w-lg text-sm leading-relaxed" style={{ color: 'var(--uvai-ink-soft)' }}>
                Workflow Pro is the available self-serve checkout. Ship and Maintain remain
                request-based options.
              </p>

              <div className="mt-8 grid grid-cols-1 gap-4 sm:grid-cols-3">
                {OFFERS.map((offer) => (
                  <article
                    key={offer.name}
                    className="rounded-xl px-6 py-6"
                    style={{ border: '1px solid var(--uvai-border)', background: 'var(--uvai-surface-warm)' }}
                  >
                    <p className="uvai-label">{offer.name}</p>
                    <p className="mt-2 text-lg font-semibold" style={{ color: 'var(--uvai-ink)' }}>{offer.price}</p>
                  </article>
                ))}
              </div>
            </div>
          </section>
        </div>
      </section>

      <Footer variant="full" />
    </main>
  );
}
