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

export default async function HomePage() {
  const showCustomBadge = await customBadge();

  return (
    <main className="min-h-screen overflow-hidden bg-surface-950 text-white">
      <Nav />

      <section aria-labelledby="home-heading" className="px-5 pb-16 pt-12 sm:px-6 md:pb-24 md:pt-20">
        <div className="mx-auto max-w-6xl">
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-[minmax(0,1.15fr)_minmax(20rem,0.85fr)] lg:items-start lg:gap-12">
            <div className="min-w-0">
              <div className="flex items-center gap-3">
                <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-primary-500 to-primary-600 font-heading text-xl font-black shadow-lg shadow-primary-500/25">
                  U
                </div>
                <span className="font-heading text-3xl font-black tracking-tight sm:text-4xl">UVAI</span>
              </div>
              <p className="mt-5 text-[11px] font-bold uppercase tracking-[0.28em] text-teal-200">
                Universal Video Action Intelligence
              </p>
              {showCustomBadge && (
                <p className="mt-4 inline-flex rounded-full border border-teal-300/30 bg-teal-300/10 px-3 py-1 text-xs font-semibold text-teal-100">
                  New: configurable with Vercel Flags
                </p>
              )}

              <h1
                id="home-heading"
                className="mt-6 max-w-3xl font-heading text-4xl font-black leading-[1.06] tracking-tight text-balance sm:text-5xl md:mt-8 md:text-6xl"
              >
                Turn a YouTube URL into a hashed Video Pack, then open it in Studio.
              </h1>
              <p className="mt-5 max-w-2xl text-base leading-8 text-white/70 md:text-lg">
                Paste a YouTube URL to open Studio and review transcript, event, and action outputs
                from your source. Transcript quality varies by source. No guaranteed production
                outcome.
              </p>

              <div className="mt-8 w-full max-w-2xl md:mt-10">
                <HomePasteForm />
              </div>
            </div>

            <aside
              id="get-pro"
              aria-labelledby="workflow-pro-heading"
              className="min-w-0 rounded-[2rem] border border-teal-300/20 bg-surface-900/70 p-1 shadow-2xl shadow-black/30"
            >
              <div className="px-5 pb-1 pt-5 sm:px-7 sm:pt-7">
                <p className="text-xs font-bold uppercase tracking-[0.18em] text-teal-200">
                  Workflow Pro
                </p>
                <h2 id="workflow-pro-heading" className="mt-2 font-heading text-2xl font-bold tracking-tight">
                  Get Pro through the existing checkout.
                </h2>
                <p className="mt-3 text-sm leading-6 text-white/65">
                  Choose a billing cadence for the existing Workflow Pro checkout. Stripe confirms
                  the amount and renewal terms before payment.
                </p>
              </div>
              <HomeProCheckout />
            </aside>
          </div>

          <section aria-labelledby="offer-summary-heading" className="mt-12 border-t border-white/[0.08] pt-8 md:mt-16 md:pt-10">
            <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
              <div>
                <p className="text-xs font-bold uppercase tracking-[0.18em] text-teal-200">Options</p>
                <h2 id="offer-summary-heading" className="mt-2 font-heading text-2xl font-bold tracking-tight">
                  Start in Studio, then choose the right level of support.
                </h2>
              </div>
              <p className="max-w-sm text-sm leading-6 text-white/65">
                Workflow Pro is the available self-serve checkout. Ship and Maintain remain
                request-based options.
              </p>
            </div>

            <div className="mt-6 grid grid-cols-1 gap-3 sm:grid-cols-3">
              {OFFERS.map((offer) => (
                <article
                  key={offer.name}
                  className="min-w-0 rounded-2xl border border-white/[0.1] bg-white/[0.035] px-5 py-5"
                >
                  <p className="text-[11px] font-bold uppercase tracking-[0.18em] text-white/65">
                    {offer.name}
                  </p>
                  <p className="mt-2 font-heading text-lg font-bold text-white">{offer.price}</p>
                </article>
              ))}
            </div>
          </section>
        </div>
      </section>

      <Footer variant="full" />
    </main>
  );
}
