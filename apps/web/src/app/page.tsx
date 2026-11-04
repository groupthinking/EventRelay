import type { Metadata } from 'next';
import { Film, FileText, Layers, Workflow } from 'lucide-react';
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
  title: 'UVAI — YouTube videos to bound tasks',
  description:
    'Bind YouTube videos to source-linked tasks, expected outputs, and proposed checks in Studio. Transcript quality varies by source.',
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

      <section aria-labelledby="home-heading" className="template-home px-4 sm:px-6 lg:px-12 pb-16 pt-6">
        <div className="mx-auto max-w-6xl">
          <HomeTemplateShell context={
            <div>
              <p className="uvai-label">Video → tasks → checks</p>
              <h2 className="mt-4 text-xl">Every action has a source.</h2>
              <p className="mt-3 text-sm leading-relaxed" style={{ color: 'var(--uvai-ink-soft)' }}>
                Keep the spoken action, expected output, and acceptance check together.
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
                    <p className="mt-2 text-sm" style={{ color: 'var(--uvai-ink-soft)' }}>Studio organizes the source into a hashed Video Pack. The Tasks view connects requirements to source timestamps and acceptance criteria.</p></div>
                </li>
                <li className="home-workflow-step">
                  <span className="home-step-number" aria-hidden="true">03</span>
                  <div><h3 className="text-base font-medium">Inspect the checks</h3>
                    <p className="mt-2 text-sm" style={{ color: 'var(--uvai-ink-soft)' }}>Review each expected output and export the bound tasks. Unrun checks stay unverified; proposed work is not a verified deployment.</p></div>
                </li>
              </ol>
              <div className="mt-8 border-t pt-5 text-xs leading-relaxed" style={{ borderColor: 'var(--uvai-border)', color: 'var(--uvai-ink-soft)' }}>
                Your source stays the reference. Missing evidence should remain an open question.
              </div>
            </div>
          }>
            <div className="template-welcome">
              <div className="template-mark" aria-hidden="true"><Film size={28} /></div>
              <p className="uvai-label">
                Universal Video Action Intelligence
              </p>
              {showCustomBadge && (
                <p className="mt-4 inline-flex rounded-full px-3 py-1 text-xs font-medium"
                   style={{ border: '1px solid var(--uvai-border)', background: 'var(--uvai-accent-soft)', color: 'var(--uvai-accent)' }}>
                  New: configurable with Vercel Flags
                </p>
              )}

              <h1 id="home-heading" className="mt-5 max-w-2xl text-3xl sm:text-4xl" style={{ color: 'var(--uvai-ink)' }}>
                Turn YouTube into bound tasks.
              </h1>
              <p className="mt-4 max-w-xl text-sm leading-relaxed" style={{ color: 'var(--uvai-ink-soft)' }}>
                Paste a YouTube URL. UVAI connects source-linked actions, expected outputs,
                and proposed checks in one workspace. Studio prepares proposed work and build rails for you to review.
                Follow the timestamp and take the next step toward your build.
              </p>
              <p className="mt-3 text-sm" style={{ color: 'var(--uvai-ink-faint)' }}>
                Transcript quality varies by source. No guaranteed production outcome.
              </p>

              <div className="home-source-composer w-full max-w-xl">
                <HomePasteForm />
              </div>
              <div className="template-use-cases" aria-label="Supported source examples">
                <div><FileText size={18} aria-hidden="true" /><strong>Software tutorial</strong><span>Inspect steps and prerequisites</span></div>
                <div><Layers size={18} aria-hidden="true" /><strong>Product walkthrough</strong><span>Review features and interactions</span></div>
                <div><Workflow size={18} aria-hidden="true" /><strong>Process recording</strong><span>Explore proposed work</span></div>
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
