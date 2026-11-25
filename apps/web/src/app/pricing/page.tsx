'use client';

import Link from 'next/link';
import { Suspense, useState } from 'react';
import { Check, CreditCard, GitFork, Minus, ShieldCheck } from 'lucide-react';
import Nav from '@/components/Nav';
import Footer from '@/components/Footer';
import ProCheckoutButton from '@/components/billing/ProCheckoutButton';
import ProRenewPanel from '@/components/billing/ProRenewPanel';
import CheckoutSuccessActivator from '@/components/billing/CheckoutSuccessActivator';
import {
  workflowProPriceLabel,
  WORKFLOW_PRO_PRODUCT_NAME,
} from '@/lib/billing/checkout-config';

const CORE_CAPABILITIES = [
  'Evidence-gated YouTube analysis',
  'Timed caption transcript',
  'Visible source provenance',
  'Workflow run history',
  'Proposed work from a Video Pack',
  'Export after quality verification',
];

const PRO_CAPABILITIES = [
  'Everything in Core',
  'Confirmed external agent dispatch',
  'Confirmed knowledge-store writes',
  'Pro entitlement recovery after checkout',
];

const COMPARISON = [
  ['Verified video analysis', true, true, true],
  ['Timed transcript and provenance', true, true, true],
  ['Proposed work from a Video Pack', true, true, true],
  ['External agent dispatch', false, true, 'User-managed'],
  ['Knowledge-store writes', false, true, 'User-managed'],
  ['Infrastructure and provider keys', 'Hosted', 'Hosted', 'User-managed'],
] as const;

function Mark({ value }: { value: boolean | string }) {
  if (value === true) return <Check className="mx-auto h-4 w-4" style={{ color: 'var(--uvai-accent)' }} aria-label="Included" />;
  if (value === false) return <Minus className="mx-auto h-4 w-4" style={{ color: 'var(--uvai-ink-faint)' }} aria-label="Not included" />;
  return <span className="text-xs" style={{ color: 'var(--uvai-ink-soft)' }}>{value}</span>;
}

export default function PricingPage() {
  const [annual, setAnnual] = useState(false);

  return (
    <div className="min-h-screen" style={{ background: 'var(--uvai-bg)', color: 'var(--uvai-ink)' }}>
      <Nav variant="rail" defaultCollapsed={false} />

      <main className="w-full max-w-[1440px] px-4 py-6 sm:px-6 lg:px-8 lg:py-8">
        <div className="mb-8 flex flex-wrap items-center justify-between gap-3 rounded-xl border border-[var(--uvai-border-strong)] bg-[var(--uvai-surface)] px-4 py-3">
          <nav aria-label="Breadcrumb" className="text-xs text-[var(--uvai-ink-faint)]">
            <ol className="flex items-center gap-2">
              <li>
                <Link className="hover:text-[var(--uvai-ink)] hover:underline" href="/">
                  Home
                </Link>
              </li>
              <li aria-hidden="true">/</li>
              <li aria-current="page" className="font-medium text-[var(--uvai-ink)]">
                Pricing &amp; Plans
              </li>
            </ol>
          </nav>
          <div className="flex flex-wrap items-center gap-2">
            <Link
              href="/studio"
              className="inline-flex items-center gap-1.5 rounded-lg border border-[var(--uvai-border-strong)] bg-[var(--uvai-bg)] px-3 py-1.5 text-xs font-medium text-[var(--uvai-ink)] transition hover:border-[var(--uvai-accent)]"
            >
              Open Studio →
            </Link>
          </div>
        </div>

        <header className="mb-8 flex flex-col gap-6 border-b border-[var(--uvai-border-strong)] pb-6 lg:flex-row lg:items-end lg:justify-between">
          <div className="max-w-2xl">
            <p className="uvai-label">Plans and access</p>
            <h1 className="mt-2 text-3xl font-medium tracking-tight sm:text-4xl" style={{ color: 'var(--uvai-ink)' }}>
              Know what unlocks before you pay.
            </h1>
            <p className="mt-3 text-sm leading-relaxed sm:text-base" style={{ color: 'var(--uvai-ink-soft)' }}>
              Core analysis stays evidence-gated. Pro unlocks confirmed external execution. Stripe shows
              the exact current amount and billing terms before any purchase is completed.
            </p>
          </div>

          <div className="inline-flex shrink-0 self-start rounded-xl p-1 lg:self-end" style={{ border: '1px solid var(--uvai-border-strong)', background: 'var(--uvai-surface)' }}>
            <button
              type="button"
              onClick={() => setAnnual(false)}
              aria-pressed={!annual}
              className="rounded-lg px-4 py-2 text-xs font-medium transition sm:text-sm"
              style={{
                background: !annual ? 'var(--uvai-surface-warm)' : 'transparent',
                color: !annual ? 'var(--uvai-ink)' : 'var(--uvai-ink-soft)',
              }}
            >
              Monthly checkout
            </button>
            <button
              type="button"
              onClick={() => setAnnual(true)}
              aria-pressed={annual}
              className="rounded-lg px-4 py-2 text-xs font-medium transition sm:text-sm"
              style={{
                background: annual ? 'var(--uvai-surface-warm)' : 'transparent',
                color: annual ? 'var(--uvai-ink)' : 'var(--uvai-ink-soft)',
              }}
            >
              Annual checkout
            </button>
          </div>
        </header>

        <Suspense fallback={null}>
          <CheckoutSuccessActivator />
        </Suspense>
        <ProRenewPanel annual={annual} />

        <section className="grid gap-5 pb-12 lg:grid-cols-3">
          <article className="uvai-card flex flex-col p-6" style={{ borderColor: 'var(--uvai-border-strong)' }}>
            <p className="uvai-label">Core</p>
            <h2 className="font-display mt-2 text-2xl">Analyze and review</h2>
            <p className="mt-3 text-sm leading-relaxed" style={{ color: 'var(--uvai-ink-soft)' }}>
              The public product path for turning a supported YouTube URL into verified evidence and proposed work.
            </p>
            <ul className="mt-6 flex-1 space-y-2.5">
              {CORE_CAPABILITIES.map((capability) => (
                <li key={capability} className="flex items-start gap-2.5 text-sm" style={{ color: 'var(--uvai-ink-soft)' }}>
                  <Check className="mt-0.5 h-4 w-4 shrink-0" style={{ color: 'var(--uvai-accent)' }} aria-hidden="true" />
                  {capability}
                </li>
              ))}
            </ul>
            <Link href="/studio" className="uvai-btn uvai-btn-secondary mt-6 justify-center">
              Open Core studio
            </Link>
          </article>

          <article className="uvai-card flex flex-col p-6" style={{ borderColor: 'var(--uvai-accent)', borderWidth: '1.5px' }}>
            <p className="uvai-label" style={{ color: 'var(--uvai-accent)' }}>{WORKFLOW_PRO_PRODUCT_NAME}</p>
            <p data-testid="workflow-pro-selected-price" className="font-display mt-2 text-3xl">
              {workflowProPriceLabel(annual)}
            </p>
            <p data-testid="workflow-pro-catalog" className="mt-1 text-xs" style={{ color: 'var(--uvai-ink-faint)' }}>
              {WORKFLOW_PRO_PRODUCT_NAME} · {workflowProPriceLabel(false)} or {workflowProPriceLabel(true)}
            </p>
            <h2 className="font-display mt-3 text-2xl">Confirm external work</h2>
            <p className="mt-3 text-sm leading-relaxed" style={{ color: 'var(--uvai-ink-soft)' }}>
              Adds the entitlement required when a Studio plan dispatches backend agents or writes to the knowledge store.
            </p>
            <ul className="mt-6 flex-1 space-y-2.5">
              {PRO_CAPABILITIES.map((capability) => (
                <li key={capability} className="flex items-start gap-2.5 text-sm" style={{ color: 'var(--uvai-ink-soft)' }}>
                  <ShieldCheck className="mt-0.5 h-4 w-4 shrink-0" style={{ color: 'var(--uvai-accent)' }} aria-hidden="true" />
                  {capability}
                </li>
              ))}
            </ul>
            <div className="mt-6">
              <ProCheckoutButton
                annual={annual}
                label={`Continue to ${WORKFLOW_PRO_PRODUCT_NAME} ${workflowProPriceLabel(annual)} checkout`}
              />
            </div>
            <p className="mt-3 text-center text-xs leading-relaxed" style={{ color: 'var(--uvai-ink-faint)' }}>
              Bot-protected checkout. Stripe displays the exact price and renewal terms before confirmation.
            </p>
          </article>

          <article className="uvai-card flex flex-col p-6" style={{ borderColor: 'var(--uvai-border-strong)' }}>
            <p className="uvai-label">Self-hosted</p>
            <h2 className="font-display mt-2 text-2xl">Own the runtime</h2>
            <p className="mt-3 flex-1 text-sm leading-relaxed" style={{ color: 'var(--uvai-ink-soft)' }}>
              Run the source with your own Vercel, FastAPI, model-provider, database, billing, and rate-limit configuration.
            </p>
            <a
              href="https://github.com/groupthinking/EventRelay"
              target="_blank"
              rel="noopener noreferrer"
              className="uvai-btn uvai-btn-secondary mt-6 justify-center"
            >
              <GitFork className="h-4 w-4" aria-hidden="true" />
              Inspect source repository
            </a>
            <p className="mt-3 text-center text-xs leading-relaxed" style={{ color: 'var(--uvai-ink-faint)' }}>
              Hosting, provider usage, security, and operating costs are managed by the deployer.
            </p>
          </article>
        </section>

        <section className="pb-12">
          <div className="mb-5">
            <h2 className="font-display text-2xl">Verified access boundaries</h2>
            <p className="mt-1.5 text-sm" style={{ color: 'var(--uvai-ink-soft)' }}>The table reflects current enforcement in the application.</p>
          </div>
          <div className="uvai-card overflow-x-auto p-0" style={{ borderColor: 'var(--uvai-border-strong)' }}>
            <div className="grid min-w-[540px] grid-cols-4 text-sm font-semibold" style={{ borderBottom: '1px solid var(--uvai-border)', background: 'var(--uvai-surface-warm)' }}>
              <div className="p-4" style={{ color: 'var(--uvai-ink-soft)' }}>Capability</div>
              <div className="p-4 text-center">Core</div>
              <div className="p-4 text-center" style={{ color: 'var(--uvai-accent)' }}>{WORKFLOW_PRO_PRODUCT_NAME}</div>
              <div className="p-4 text-center">Self-hosted</div>
            </div>
            {COMPARISON.map(([label, core, pro, selfHosted], index) => (
              <div
                key={label}
                className="grid min-w-[540px] grid-cols-4"
                style={{
                  borderBottom: index < COMPARISON.length - 1 ? '1px solid var(--uvai-border)' : 'none',
                  background: index % 2 ? 'var(--uvai-surface-warm)' : 'transparent',
                }}
              >
                <div className="p-4 text-sm" style={{ color: 'var(--uvai-ink-soft)' }}>{label}</div>
                <div className="p-4 text-center"><Mark value={core} /></div>
                <div className="p-4 text-center"><Mark value={pro} /></div>
                <div className="p-4 text-center"><Mark value={selfHosted} /></div>
              </div>
            ))}
          </div>
        </section>

        <section className="pb-12">
          <div className="uvai-card p-6 md:p-8" style={{ borderColor: 'var(--uvai-border-strong)' }}>
            <div className="flex items-start gap-4">
              <CreditCard className="mt-1 h-5 w-5 shrink-0" style={{ color: 'var(--uvai-accent)' }} aria-hidden="true" />
              <div>
                <h2 className="font-display text-xl">Before checkout</h2>
                <div className="mt-4 space-y-4 text-sm leading-relaxed" style={{ color: 'var(--uvai-ink-soft)' }}>
                  <p><strong style={{ color: 'var(--uvai-ink)' }}>Where is the current price?</strong> Stripe Checkout is the authoritative source and shows the exact configured amount, interval, and renewal terms before payment.</p>
                  <p><strong style={{ color: 'var(--uvai-ink)' }}>Does preparation execute tools?</strong> No. Preparing an action plan is review-only. External execution requires a second confirmation and the appropriate entitlement.</p>
                  <p><strong style={{ color: 'var(--uvai-ink)' }}>What if checkout is not configured?</strong> The button reports that Turnstile or checkout configuration is unavailable instead of fabricating a successful purchase path.</p>
                </div>
              </div>
            </div>
          </div>
        </section>
      </main>

      <Footer variant="compact" />
    </div>
  );
}
