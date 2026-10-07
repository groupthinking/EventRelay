import type { Metadata } from 'next';
import Nav from '@/components/Nav';
import Footer from '@/components/Footer';
import HomePasteForm from '@/components/home/HomePasteForm';
import HomeProCheckout from '@/components/home/HomeProCheckout';
import '@/styles/studio-cards.css';
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
 * Render the landing page with a YouTube URL-to-Studio handoff and Workflow Pro checkout.
 * Light card system per apps/web/DESIGN_LANGUAGE.md. Copy and pricing unchanged.
 * The optional badge appears only when its feature flag is enabled.
 */
export default async function HomePage() {
  const showCustomBadge = await customBadge();

  return (
    <main className="uvai-cards min-h-screen overflow-hidden">
      <Nav tone="light" />

      <section aria-labelledby="home-heading" className="px-5 pb-16 pt-12 sm:px-6 md:pb-24 md:pt-20">
        <div className="mx-auto max-w-6xl">
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-[minmax(0,1.15fr)_minmax(20rem,0.85fr)] lg:items-start lg:gap-8">
            <div className="uvai-card min-w-0 p-8 sm:p-10">
              <div className="flex items-center gap-3">
                <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-amber-500 to-amber-600 font-heading text-xl font-black text-white shadow-lg shadow-amber-500/25">
                  U
                </div>
                <span className="font-heading text-3xl font-black tracking-tight text-slate-900 sm:text-4xl">UVAI</span>
              </div>
              <p className="uvai-section-label mt-5">
                Universal Video Action Intelligence
              </p>
              {showCustomBadge && (
                <p className="mt-4 inline-flex rounded-full border border-amber-200 bg-amber-50 px-3 py-1 text-xs font-semibold text-amber-800">
                  New: configurable with Vercel Flags
                </p>
              )}

              <h1
                id="home-heading"
                className="mt-6 max-w-3xl font-heading text-4xl font-black leading-[1.06] tracking-tight text-balance text-slate-900 sm:text-5xl md:mt-8 md:text-6xl"
              >
                Your videos know what to do next.
              </h1>
              <p className="mt-5 max-w-2xl text-base leading-8 text-slate-600 md:text-lg">
                Paste a YouTube URL. UVAI pulls the events, actions, and decisions out of it,
                lines up the next move for your approval, and turns it into something real.
                Transcript quality varies by source. No guaranteed production outcome.
              </p>

              <div className="mt-8 w-full max-w-2xl md:mt-10">
                <HomePasteForm />
              </div>
            </div>

            <aside
              id="get-pro"
              aria-labelledby="workflow-pro-heading"
              className="uvai-card min-w-0 p-1"
            >
              <div className="px-5 pb-1 pt-5 sm:px-7 sm:pt-7">
                <p className="uvai-section-label">
                  Workflow Pro
                </p>
                <h2 id="workflow-pro-heading" className="mt-2 font-heading text-2xl font-bold tracking-tight text-slate-900">
                  Get Pro through the existing checkout.
                </h2>
                <p className="mt-3 text-sm leading-6 text-slate-600">
                  Choose a billing cadence for the existing Workflow Pro checkout. Stripe confirms
                  the amount and renewal terms before payment.
                </p>
              </div>
              <HomeProCheckout />
            </aside>
          </div>

          <section aria-labelledby="offer-summary-heading" className="mt-8 md:mt-12">
            <div className="uvai-card px-6 py-8 sm:px-8 md:px-10 md:py-10">
              <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
                <div>
                  <p className="uvai-section-label">Options</p>
                  <h2 id="offer-summary-heading" className="mt-2 font-heading text-2xl font-bold tracking-tight text-slate-900">
                    Start in Studio, then choose the right level of support.
                  </h2>
                </div>
                <p className="max-w-sm text-sm leading-6 text-slate-600">
                  Workflow Pro is the available self-serve checkout. Ship and Maintain remain
                  request-based options.
                </p>
              </div>

              <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-3">
                {OFFERS.map((offer) => (
                  <article
                    key={offer.name}
                    className="rounded-2xl border border-slate-200 bg-slate-50/60 px-5 py-5"
                  >
                    <p className="uvai-section-label">
                      {offer.name}
                    </p>
                    <p className="mt-2 font-heading text-lg font-bold text-slate-900">{offer.price}</p>
                  </article>
                ))}
              </div>
            </div>
          </section>
        </div>
      </section>

      <Footer variant="full" tone="light" />
    </main>
  );
}
