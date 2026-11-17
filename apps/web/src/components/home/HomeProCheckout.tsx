'use client';

import { useState } from 'react';
import Link from 'next/link';
import ProCheckoutButton from '@/components/billing/ProCheckoutButton';
import {
  WORKFLOW_PRO_PRODUCT_NAME,
  workflowProPriceLabel,
} from '@/lib/billing/checkout-config';

/**
 * Home Get Pro island. Reuses ProCheckoutButton (Turnstile + existing Stripe session).
 * Non-Pro offers on the sell grid stay copy-only — no extra Stripe SKUs here.
 */
export default function HomeProCheckout() {
  const [annual, setAnnual] = useState(false);

  return (
    <div
      data-testid="home-pro-checkout"
      className="m-2 rounded-xl border border-[var(--uvai-border-strong)] bg-[var(--uvai-surface)] p-6 text-left sm:m-4 sm:p-8"
    >
      <p className="text-xs font-semibold uppercase tracking-[0.14em] text-[#4d94ff]">Get Pro</p>
      <p
        data-testid="home-workflow-pro-selected-price"
        className="mt-3 font-heading text-3xl font-bold tracking-tight text-[var(--uvai-ink)] md:text-4xl"
      >
        {workflowProPriceLabel(annual)}
      </p>
      <p className="mt-1 text-xs text-[var(--uvai-ink-faint)]">
        {WORKFLOW_PRO_PRODUCT_NAME} · {workflowProPriceLabel(false)} or {workflowProPriceLabel(true)}
      </p>
      <p className="mt-4 text-sm leading-7 text-[var(--uvai-ink-soft)]">
        Bot-protected checkout for confirmed external dispatch. Stripe shows the exact amount
        and renewal terms before you pay.
      </p>

      <div
        className="mt-5 grid w-full grid-cols-1 gap-1.5 rounded-lg border border-[var(--uvai-border-strong)] bg-[var(--uvai-bg)] p-1.5 sm:inline-grid sm:w-auto sm:grid-cols-2"
        role="group"
        aria-label="Billing cadence"
      >
        <button
          type="button"
          onClick={() => setAnnual(false)}
          aria-pressed={!annual}
          className={`w-full rounded-md px-5 py-2 text-sm font-semibold transition focus:outline-none focus-visible:ring-2 focus-visible:ring-[#146ef5] focus-visible:ring-offset-2 focus-visible:ring-offset-[var(--uvai-bg)] ${!annual ? 'bg-[#146ef5] text-white' : 'text-[var(--uvai-ink-soft)] hover:text-[var(--uvai-ink)]'}`}
        >
          Monthly checkout
        </button>
        <button
          type="button"
          onClick={() => setAnnual(true)}
          aria-pressed={annual}
          className={`w-full rounded-md px-5 py-2 text-sm font-semibold transition focus:outline-none focus-visible:ring-2 focus-visible:ring-[#146ef5] focus-visible:ring-offset-2 focus-visible:ring-offset-[var(--uvai-bg)] ${annual ? 'bg-[#146ef5] text-white' : 'text-[var(--uvai-ink-soft)] hover:text-[var(--uvai-ink)]'}`}
        >
          Annual checkout
        </button>
      </div>

      <div className="mt-6">
        <ProCheckoutButton
          annual={annual}
          label={`Continue to ${WORKFLOW_PRO_PRODUCT_NAME} ${workflowProPriceLabel(annual)} checkout`}
        />
      </div>
      <p className="mt-3 text-center text-xs leading-5 text-[var(--uvai-ink-faint)]">
        Same checkout as Pricing. Core paste and Studio stay available without paying.
      </p>
      <p className="mt-4 text-center">
        <Link
          href="/pricing"
          className="rounded text-sm text-[var(--uvai-ink-soft)] underline-offset-4 hover:text-[var(--uvai-ink)] hover:underline focus:outline-none focus-visible:ring-2 focus-visible:ring-[#146ef5] focus-visible:ring-offset-2 focus-visible:ring-offset-[var(--uvai-bg)]"
        >
          See all plans
        </Link>
      </p>
    </div>
  );
}
