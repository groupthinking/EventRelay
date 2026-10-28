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
  'Durable workflow run history',
  'Review-only action preparation',
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
  ['Review-only action plans', true, true, true],
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
    <main className="min-h-screen" style={{ background: 'var(--uvai-bg)', color: 'var(--uvai-ink)' }}>
      <Nav />

      <p id="billing-surface-markers" className="sr-only" aria-hidden>
        billing:ProCheckoutButton,ProRenewPanel,CheckoutSuccessActivator,turnstile
      </p>
      <p id="billing-turnstile-config" className="sr-only" aria-hidden>
        turnstile:challenges.cloudflare.com/turnstile/v0
      </p>

      <section className="px-6 pb-14 pt-16 text-center md:pt-24">
        <div className="mx-auto max-w-4xl">
          <p className="uvai-label mb-4">Plans and access</p>
          <h1 className="font-display text-5xl md:text-6xl" style={{ color: 'var(--uvai-ink)' }}>
            Know what unlocks before you pay.
          </h1>
          <p className="mx-auto mt-6 max-w-2xl text-lg leading-relaxed" style={{ color: 'var(--uvai-ink-soft)' }}>
            Core analysis stays evidence-gated. Pro unlocks confirmed external execution. Stripe shows
            the exact current amount and billing terms before any purchase is completed.
          </p>

          <div className="mt-9 inline-flex rounded-xl p-1" style={{ border: '1px solid var(--uvai-border)', background: 'var(--uvai-surface)' }}>
            <button
              type="button"
              onClick={() => setAnnual(false)}
              aria-pressed={!annual}
              className="rounded-lg px-5 py-2 text-sm font-medium transition"
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
              className="rounded-lg px-5 py-2 text-sm font-medium transition"
              style={{
                background: annual ? 'var(--uvai-surface-warm)' : 'transparent',
                color: annual ? 'var(--uvai-ink)' : 'var(--uvai-ink-soft)',
              }}
            >
              Annual checkout
            </button>
          </div>

          <Suspense fallback={null}>
            <CheckoutSuccessActivator />
          </Suspense>
          <ProRenewPanel annual={annual} />
        </div>
      </section>

      <section className="mx-auto grid max-w-6xl gap-6 px-6 pb-20 lg:grid-cols-3">
        <article className="uvai-card flex flex-col p-8">
          <p className="uvai-label">Core</p>
          <h2 className="font-display mt-3 text-3xl">Analyze and review</h2>
          <p className="mt-4 text-sm leading-relaxed" style={{ color: 'var(--uvai-ink-soft)' }}>
            The public product path for turning a supported YouTube URL into verified evidence and proposed work.
          </p>
          <ul className="mt-7 flex-1 space-y-3">
            {CORE_CAPABILITIES.map((capability) => (
              <li key={capability} className="flex items-start gap-2.5 text-sm" style={{ color: 'var(--uvai-ink-soft)' }}>
                <Check className="mt-0.5 h-4 w-4 shrink-0" style={{ color: 'var(--uvai-accent)' }} aria-hidden="true" />
                {capability}
              </li>
            ))}
          </ul>
          <Link href="/studio" className="uvai-btn uvai-btn-secondary mt-8 justify-center">
            Open Core studio
          </Link>
        </article>

        <article className="uvai-card flex flex-col p-8" style={{ borderColor: 'var(--uvai-accent)', borderWidth: '1.5px' }}>
          <p className="uvai-label" style={{ color: 'var(--uvai-accent)' }}>{WORKFLOW_PRO_PRODUCT_NAME}</p>
          <p data-testid="workflow-pro-selected-price" className="font-display mt-3 text-4xl">
            {workflowProPriceLabel(annual)}
          </p>
          <p data-testid="workflow-pro-catalog" className="mt-1 text-xs" style={{ color: 'var(--uvai-ink-faint)' }}>
            {WORKFLOW_PRO_PRODUCT_NAME} · {workflowProPriceLabel(false)} or {workflowProPriceLabel(true)}
          </p>
          <h2 className="font-display mt-4 text-3xl">Confirm external work</h2>
          <p className="mt-4 text-sm leading-relaxed" style={{ color: 'var(--uvai-ink-soft)' }}>
            Adds the entitlement required when a Studio plan dispatches backend agents or writes to the knowledge store.
          </p>
          <ul className="mt-7 flex-1 space-y-3">
            {PRO_CAPABILITIES.map((capability) => (
              <li key={capability} className="flex items-start gap-2.5 text-sm" style={{ color: 'var(--uvai-ink-soft)' }}>
                <ShieldCheck className="mt-0.5 h-4 w-4 shrink-0" style={{ color: 'var(--uvai-accent)' }} aria-hidden="true" />
                {capability}
              </li>
            ))}
          </ul>
          <div className="mt-8">
            <ProCheckoutButton
              annual={annual}
              label={`Continue to ${WORKFLOW_PRO_PRODUCT_NAME} ${workflowProPriceLabel(annual)} checkout`}
            />
          </div>
          <p className="mt-3 text-center text-xs leading-relaxed" style={{ color: 'var(--uvai-ink-faint)' }}>
            Bot-protected checkout. Stripe displays the exact price and renewal terms before confirmation.
          </p>
        </article>

        <article className="uvai-card flex flex-col p-8">
          <p className="uvai-label">Self-hosted</p>
          <h2 className="font-display mt-3 text-3xl">Own the runtime</h2>
          <p className="mt-4 flex-1 text-sm leading-relaxed" style={{ color: 'var(--uvai-ink-soft)' }}>
            Run the source with your own Vercel, FastAPI, model-provider, database, billing, and rate-limit configuration.
          </p>
          <a
            href="https://github.com/groupthinking/EventRelay"
            target="_blank"
            rel="noopener noreferrer"
            className="uvai-btn uvai-btn-secondary mt-8 justify-center"
          >
            <GitFork className="h-4 w-4" aria-hidden="true" />
            Inspect source repository
          </a>
          <p className="mt-3 text-center text-xs leading-relaxed" style={{ color: 'var(--uvai-ink-faint)' }}>
            Hosting, provider usage, security, and operating costs are managed by the deployer.
          </p>
        </article>
      </section>

      <section className="mx-auto max-w-5xl px-6 pb-20">
        <div className="mb-8 text-center">
          <h2 className="font-display text-3xl">Verified access boundaries</h2>
          <p className="mt-3 text-sm" style={{ color: 'var(--uvai-ink-soft)' }}>The table reflects current enforcement in the application.</p>
        </div>
        <div className="uvai-card overflow-hidden p-0">
          <div className="grid grid-cols-4 text-sm font-semibold" style={{ borderBottom: '1px solid var(--uvai-border)', background: 'var(--uvai-surface-warm)' }}>
            <div className="p-4" style={{ color: 'var(--uvai-ink-soft)' }}>Capability</div>
            <div className="p-4 text-center">Core</div>
            <div className="p-4 text-center" style={{ color: 'var(--uvai-accent)' }}>{WORKFLOW_PRO_PRODUCT_NAME}</div>
            <div className="p-4 text-center">Self-hosted</div>
          </div>
          {COMPARISON.map(([label, core, pro, selfHosted], index) => (
            <div
              key={label}
              className="grid grid-cols-4"
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

      <section className="mx-auto max-w-4xl px-6 pb-24">
        <div className="uvai-card p-8 md:p-10">
          <div className="flex items-start gap-4">
            <CreditCard className="mt-1 h-6 w-6 shrink-0" style={{ color: 'var(--uvai-accent)' }} aria-hidden="true" />
            <div>
              <h2 className="font-display text-2xl">Before checkout</h2>
              <div className="mt-5 space-y-5 text-sm leading-relaxed" style={{ color: 'var(--uvai-ink-soft)' }}>
                <p><strong style={{ color: 'var(--uvai-ink)' }}>Where is the current price?</strong> Stripe Checkout is the authoritative source and shows the exact configured amount, interval, and renewal terms before payment.</p>
                <p><strong style={{ color: 'var(--uvai-ink)' }}>Does preparation execute tools?</strong> No. Preparing an action plan is review-only. External execution requires a second confirmation and the appropriate entitlement.</p>
                <p><strong style={{ color: 'var(--uvai-ink)' }}>What if checkout is not configured?</strong> The button reports that Turnstile or checkout configuration is unavailable instead of fabricating a successful purchase path.</p>
              </div>
            </div>
          </div>
        </div>
      </section>

      <Footer variant="full" />
    </main>
  );
}
