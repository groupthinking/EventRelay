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

const WORKFLOW_STEPS = [
  {
    number: '01',
    title: 'Paste a YouTube URL',
    description: 'Use the URL you already have. Invalid links stay on this page with a clear error.',
  },
  {
    number: '02',
    title: 'Open Studio',
    description: 'A valid link starts a hashed Video Pack and hands the source to the existing Studio workflow.',
  },
  {
    number: '03',
    title: 'Review the outputs',
    description: 'Studio brings together source-dependent transcript, event, and action outputs for review.',
  },
] as const;

export default async function HomePage() {
  const showCustomBadge = await customBadge();

  return (
    <main className="min-h-screen overflow-hidden bg-surface-950 text-white">
      <Nav />

      <section className="px-6 pb-20 pt-14 md:pt-24">
        <div className="mx-auto flex max-w-5xl flex-col items-center text-center">
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
          <h1 className="mt-8 max-w-4xl text-balance font-heading text-4xl font-black leading-tight tracking-tight md:text-6xl">
            Paste a YouTube URL. Continue in Studio.
          </h1>
          <p className="mt-5 max-w-2xl text-pretty text-base leading-8 text-white/65 md:text-lg">
            Paste a YouTube URL to start a hashed Video Pack, then use Studio to review transcript,
            event, and action outputs. Transcript quality varies by source.
          </p>

          <div className="mt-10 w-full rounded-3xl border border-white/[0.09] bg-white/[0.03] p-4 shadow-2xl shadow-black/20 sm:p-6">
            <HomePasteForm />
          </div>

          <ol className="mt-10 grid w-full gap-3 text-left md:grid-cols-3">
            {WORKFLOW_STEPS.map((step) => (
              <li
                key={step.number}
                className="min-w-0 rounded-2xl border border-white/[0.08] bg-white/[0.03] p-5"
              >
                <p className="font-mono text-xs font-bold tracking-[0.18em] text-teal-300">
                  {step.number}
                </p>
                <h2 className="mt-5 font-heading text-lg font-bold text-white">{step.title}</h2>
                <p className="mt-2 text-sm leading-6 text-white/55">{step.description}</p>
              </li>
            ))}
          </ol>

          <section
            className="mt-10 w-full max-w-3xl rounded-2xl border border-teal-300/20 bg-teal-300/[0.04] px-5 py-5 text-left sm:px-6"
            aria-labelledby="workflow-pro-summary"
          >
            <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
              <div>
                <p className="text-[11px] font-bold uppercase tracking-[0.18em] text-teal-200/80">
                  Workflow Pro
                </p>
                <h2 id="workflow-pro-summary" className="mt-2 font-heading text-xl font-bold text-white">
                  {WORKFLOW_PRO_PRODUCT_NAME}
                </h2>
              </div>
              <p className="font-heading text-xl font-bold text-white">
                {workflowProPriceLabel(false)}{' '}
                <span className="text-base font-medium text-white/45">or {workflowProPriceLabel(true)}</span>
              </p>
            </div>
            <p className="mt-3 max-w-2xl text-sm leading-6 text-white/55">
              Keep the same existing checkout path when you are ready to continue.
            </p>
          </section>

          <div id="get-pro" className="mt-10 w-full max-w-lg" aria-label="Get Pro">
            <HomeProCheckout />
          </div>
        </div>
      </section>

      <Footer variant="full" />
    </main>
  );
}
