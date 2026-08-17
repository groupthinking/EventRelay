'use client';

import Link from 'next/link';
import { Suspense, useState } from 'react';
import { Check, CreditCard, GitFork, Minus, ShieldCheck } from 'lucide-react';
import LandingNav from '@/components/landing/LandingNav';
import Footer from '@/components/Footer';
import ProCheckoutButton from '@/components/billing/ProCheckoutButton';
import ProRenewPanel from '@/components/billing/ProRenewPanel';
import CheckoutSuccessActivator from '@/components/billing/CheckoutSuccessActivator';

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
  if (value === true) return <Check className="mx-auto h-4 w-4 text-teal-300" aria-label="Included" />;
  if (value === false) return <Minus className="mx-auto h-4 w-4 text-white/20" aria-label="Not included" />;
  return <span className="text-xs text-white/50">{value}</span>;
}

export default function PricingPage() {
  const [annual, setAnnual] = useState(false);

  return (
    <main className="min-h-screen overflow-hidden bg-surface-950 text-white">
      <LandingNav />

      <p id="billing-surface-markers" className="sr-only" aria-hidden>
        billing:ProCheckoutButton,ProRenewPanel,CheckoutSuccessActivator,turnstile
      </p>
      <p id="billing-turnstile-config" className="sr-only" aria-hidden>
        turnstile:challenges.cloudflare.com/turnstile/v0
      </p>

      <section className="px-6 pb-14 pt-36 text-center md:pt-44">
        <div className="mx-auto max-w-4xl">
          <p className="mb-4 text-[11px] font-bold uppercase tracking-[0.26em] text-teal-300/80">
            Plans and access
          </p>
          <h1 className="font-heading text-5xl font-black leading-tight tracking-tight md:text-7xl">
            Know what unlocks before you pay.
          </h1>
          <p className="mx-auto mt-6 max-w-2xl text-base leading-8 text-white/50 md:text-lg">
            Core analysis stays evidence-gated. Pro unlocks confirmed external execution. Stripe shows
            the exact current amount and billing terms before any purchase is completed.
          </p>

          <div className="mt-9 inline-flex rounded-2xl border border-white/[0.08] bg-white/[0.04] p-1.5">
            <button
              type="button"
              onClick={() => setAnnual(false)}
              aria-pressed={!annual}
              className={`rounded-xl px-5 py-2 text-sm font-semibold transition ${!annual ? 'bg-white/[0.1] text-white' : 'text-white/40'}`}
            >
              Monthly checkout
            </button>
            <button
              type="button"
              onClick={() => setAnnual(true)}
              aria-pressed={annual}
              className={`rounded-xl px-5 py-2 text-sm font-semibold transition ${annual ? 'bg-white/[0.1] text-white' : 'text-white/40'}`}
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
        <article className="flex flex-col rounded-3xl border border-white/[0.08] bg-white/[0.025] p-8">
          <p className="text-sm font-bold uppercase tracking-wider text-white/45">Core</p>
          <h2 className="mt-3 font-heading text-3xl font-black">Analyze and review</h2>
          <p className="mt-4 text-sm leading-7 text-white/45">
            The public product path for turning a supported YouTube URL into verified evidence and proposed work.
          </p>
          <ul className="mt-7 flex-1 space-y-3">
            {CORE_CAPABILITIES.map((capability) => (
              <li key={capability} className="flex items-start gap-2.5 text-sm text-white/65">
                <Check className="mt-0.5 h-4 w-4 shrink-0 text-teal-300" aria-hidden="true" />
                {capability}
              </li>
            ))}
          </ul>
          <Link href="/dashboard" className="btn btn-secondary mt-8 justify-center py-3 text-sm">
            Open Core dashboard
          </Link>
        </article>

        <article className="flex flex-col rounded-3xl border border-teal-400/35 bg-teal-400/[0.06] p-8 shadow-2xl shadow-teal-500/10">
          <p className="text-sm font-bold uppercase tracking-wider text-teal-300">Pro</p>
          <h2 className="mt-3 font-heading text-3xl font-black">Confirm external work</h2>
          <p className="mt-4 text-sm leading-7 text-white/45">
            Adds the entitlement required when a reviewed plan dispatches backend agents or writes to the knowledge store.
          </p>
          <ul className="mt-7 flex-1 space-y-3">
            {PRO_CAPABILITIES.map((capability) => (
              <li key={capability} className="flex items-start gap-2.5 text-sm text-white/65">
                <ShieldCheck className="mt-0.5 h-4 w-4 shrink-0 text-teal-300" aria-hidden="true" />
                {capability}
              </li>
            ))}
          </ul>
          <div className="mt-8">
            <ProCheckoutButton
              annual={annual}
              label={`Continue to ${annual ? 'annual' : 'monthly'} Stripe checkout`}
            />
          </div>
          <p className="mt-3 text-center text-xs leading-5 text-white/30">
            Bot-protected checkout. Stripe displays the exact price and renewal terms before confirmation.
          </p>
        </article>

        <article className="flex flex-col rounded-3xl border border-white/[0.08] bg-white/[0.025] p-8">
          <p className="text-sm font-bold uppercase tracking-wider text-cyan-300">Self-hosted</p>
          <h2 className="mt-3 font-heading text-3xl font-black">Own the runtime</h2>
          <p className="mt-4 flex-1 text-sm leading-7 text-white/45">
            Run the source with your own Vercel, FastAPI, model-provider, database, billing, and rate-limit configuration.
          </p>
          <a
            href="https://github.com/groupthinking/EventRelay"
            target="_blank"
            rel="noopener noreferrer"
            className="btn btn-secondary mt-8 justify-center py-3 text-sm"
          >
            <GitFork className="h-4 w-4" aria-hidden="true" />
            Inspect source repository
          </a>
          <p className="mt-3 text-center text-xs leading-5 text-white/30">
            Hosting, provider usage, security, and operating costs are managed by the deployer.
          </p>
        </article>
      </section>

      <section className="mx-auto max-w-5xl px-6 pb-20">
        <div className="mb-8 text-center">
          <h2 className="font-heading text-3xl font-black">Verified access boundaries</h2>
          <p className="mt-3 text-sm text-white/40">The table reflects current enforcement in the application.</p>
        </div>
        <div className="overflow-hidden rounded-2xl border border-white/[0.08]">
          <div className="grid grid-cols-4 border-b border-white/[0.07] bg-white/[0.03] text-sm font-semibold">
            <div className="p-4 text-white/45">Capability</div>
            <div className="p-4 text-center">Core</div>
            <div className="p-4 text-center text-teal-300">Pro</div>
            <div className="p-4 text-center text-cyan-300">Self-hosted</div>
          </div>
          {COMPARISON.map(([label, core, pro, selfHosted], index) => (
            <div
              key={label}
              className="grid grid-cols-4 border-b border-white/[0.05] last:border-0"
              style={{ background: index % 2 ? 'rgba(255,255,255,0.012)' : 'transparent' }}
            >
              <div className="p-4 text-sm text-white/55">{label}</div>
              <div className="p-4 text-center"><Mark value={core} /></div>
              <div className="p-4 text-center"><Mark value={pro} /></div>
              <div className="p-4 text-center"><Mark value={selfHosted} /></div>
            </div>
          ))}
        </div>
      </section>

      <section className="mx-auto max-w-4xl px-6 pb-24">
        <div className="rounded-[2rem] border border-white/[0.08] bg-white/[0.025] p-8 md:p-10">
          <div className="flex items-start gap-4">
            <CreditCard className="mt-1 h-6 w-6 shrink-0 text-teal-300" aria-hidden="true" />
            <div>
              <h2 className="font-heading text-2xl font-black">Before checkout</h2>
              <div className="mt-5 space-y-5 text-sm leading-7 text-white/50">
                <p><strong className="text-white/80">Where is the current price?</strong> Stripe Checkout is the authoritative source and shows the exact configured amount, interval, and renewal terms before payment.</p>
                <p><strong className="text-white/80">Does preparation execute tools?</strong> No. Preparing an action plan is review-only. External execution requires a second confirmation and the appropriate entitlement.</p>
                <p><strong className="text-white/80">What if checkout is not configured?</strong> The button reports that Turnstile or checkout configuration is unavailable instead of fabricating a successful purchase path.</p>
              </div>
            </div>
          </div>
        </div>
      </section>

      <Footer variant="full" />
    </main>
  );
}
