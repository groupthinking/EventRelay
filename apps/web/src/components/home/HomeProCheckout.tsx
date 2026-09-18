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
      className="rounded-3xl border border-teal-400/35 bg-teal-400/[0.06] p-6 text-left shadow-2xl shadow-teal-500/10 sm:p-8"
    >
      <p className="text-sm font-bold uppercase tracking-wider text-teal-300">Get Pro</p>
      <p
        data-testid="home-workflow-pro-selected-price"
        className="mt-3 font-heading text-3xl font-black tracking-tight md:text-4xl"
      >
        {workflowProPriceLabel(annual)}
      </p>
      <p className="mt-1 text-xs text-white/35">
        {WORKFLOW_PRO_PRODUCT_NAME} · {workflowProPriceLabel(false)} or {workflowProPriceLabel(true)}
      </p>
      <p className="mt-4 text-sm leading-7 text-white/45">
        Bot-protected checkout for confirmed external dispatch. Stripe shows the exact amount
        and renewal terms before you pay.
      </p>

      <div className="mt-5 inline-flex rounded-2xl border border-white/[0.08] bg-white/[0.04] p-1.5">
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

      <div className="mt-6">
        <ProCheckoutButton
          annual={annual}
          label={`Continue to ${WORKFLOW_PRO_PRODUCT_NAME} ${workflowProPriceLabel(annual)} checkout`}
        />
      </div>
      <p className="mt-3 text-center text-xs leading-5 text-white/30">
        Same checkout as Pricing. Core paste and Studio stay available without paying.
      </p>
      <p className="mt-4 text-center">
        <Link href="/pricing" className="text-sm text-white/45 underline-offset-4 hover:text-white/70 hover:underline">
          See all plans
        </Link>
      </p>
    </div>
  );
}
