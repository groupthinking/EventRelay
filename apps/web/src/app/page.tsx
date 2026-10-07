import type { Metadata } from 'next';
import Nav from '@/components/Nav';
import Footer from '@/components/Footer';
import HomePasteForm from '@/components/home/HomePasteForm';
import HomeProCheckout from '@/components/home/HomeProCheckout';
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
 * Landing page — Muse design language.
 * Warm paper, serif headlines, quiet cards. Nothing shouts.
 */
export default async function HomePage() {
  const showCustomBadge = await customBadge();

  return (
    <main className="min-h-screen" style={{ background: 'var(--uvai-bg)' }}>
      <Nav />

      <section aria-labelledby="home-heading" className="px-6 lg:px-12 pb-20 pt-16 md:pt-24">
        <div className="mx-auto max-w-6xl">
          <div className="grid grid-cols-1 gap-8 lg:grid-cols-[minmax(0,1.2fr)_minmax(20rem,0.8fr)] lg:items-start">
            {/* Hero card */}
            <div className="uvai-card p-8 sm:p-12">
              <p className="uvai-label">
                Universal Video Action Intelligence
              </p>
              {showCustomBadge && (
                <p className="mt-4 inline-flex rounded-full px-3 py-1 text-xs font-medium"
                   style={{ border: '1px solid var(--uvai-border)', background: 'var(--uvai-accent-soft)', color: 'var(--uvai-accent)' }}>
                  New: configurable with Vercel Flags
                </p>
              )}

              <h1 id="home-heading" className="font-display mt-6 max-w-2xl text-4xl sm:text-5xl md:text-6xl" style={{ color: 'var(--uvai-ink)' }}>
                Your videos know what to do next.
              </h1>
              <p className="mt-6 max-w-xl text-lg leading-relaxed" style={{ color: 'var(--uvai-ink-soft)' }}>
                Paste a YouTube URL. UVAI pulls the events, actions, and decisions out of it,
                lines up the next move for your approval, and turns it into something real.
              </p>
              <p className="mt-3 text-sm" style={{ color: 'var(--uvai-ink-faint)' }}>
                Transcript quality varies by source. No guaranteed production outcome.
              </p>

              <div className="mt-10 w-full max-w-xl">
                <HomePasteForm />
              </div>
            </div>

            {/* Pro checkout */}
            <aside id="get-pro" aria-labelledby="workflow-pro-heading" className="uvai-card p-8">
              <p className="uvai-label">Workflow Pro</p>
              <h2 id="workflow-pro-heading" className="font-display mt-3 text-2xl" style={{ color: 'var(--uvai-ink)' }}>
                Get Pro through the existing checkout.
              </h2>
              <p className="mt-3 text-sm leading-relaxed" style={{ color: 'var(--uvai-ink-soft)' }}>
                Choose a billing cadence for the existing Workflow Pro checkout. Stripe confirms
                the amount and renewal terms before payment.
              </p>
              <div className="mt-6">
                <HomeProCheckout />
              </div>
            </aside>
          </div>

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
