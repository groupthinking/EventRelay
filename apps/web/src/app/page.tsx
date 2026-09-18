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
  title: 'UVAI — Universal Video Action Intelligence',
  description:
    'Paste a YouTube URL. Open the Studio workbench to start a hashed Video Pack run. Transcript quality varies by source.',
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

      <section className="px-6 pb-20 pt-16 md:pt-24">
        <div className="mx-auto flex max-w-4xl flex-col items-center text-center">
          <div className="flex items-center gap-3">
            <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-br from-primary-500 to-primary-600 font-heading text-2xl font-black shadow-lg shadow-primary-500/25">
              U
            </div>
            <span className="font-heading text-4xl font-black tracking-tight md:text-5xl">UVAI</span>
          </div>
          <p className="mt-4 text-[11px] font-bold uppercase tracking-[0.28em] text-teal-300/80">
            Universal Video Action Intelligence
          </p>
          {showCustomBadge && (
            <p className="mt-4 rounded-full border border-teal-300/30 bg-teal-300/10 px-3 py-1 text-xs font-semibold text-teal-200">
              New: configurable with Vercel Flags
            </p>
          )}
          <h1 className="mt-8 max-w-3xl font-heading text-4xl font-black leading-tight tracking-tight md:text-6xl">
            Paste a YouTube URL. Open the Studio workbench.
          </h1>
          <p className="mt-5 max-w-2xl text-base leading-8 text-white/50 md:text-lg">
            Starts a hashed Video Pack run in Studio (player, events, exports). Transcript quality
            varies by source — not a guaranteed production E2E.
          </p>

          <div className="mt-10 w-full">
            <HomePasteForm />
          </div>

          <div className="mt-10 grid w-full max-w-3xl gap-3 sm:grid-cols-3">
            {OFFERS.map((offer) => (
              <article
                key={offer.name}
                className="rounded-2xl border border-white/[0.08] bg-white/[0.03] px-4 py-4"
              >
                <p className="text-[11px] font-bold uppercase tracking-[0.18em] text-white/40">
                  {offer.name}
                </p>
                <p className="mt-2 font-heading text-lg font-bold text-white">{offer.price}</p>
              </article>
            ))}
          </div>

          <div id="get-pro" className="mt-10 w-full max-w-lg" aria-label="Get Pro">
            <HomeProCheckout />
          </div>
        </div>
      </section>

      <Footer variant="full" />
    </main>
  );
}
