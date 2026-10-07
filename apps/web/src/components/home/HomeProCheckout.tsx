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
      className="m-4 rounded-2xl border border-amber-200 bg-amber-50/60 p-6 text-left shadow-sm sm:m-6 sm:p-8"
    >
      <p className="text-sm font-bold uppercase tracking-wider text-amber-700">Get Pro</p>
      <p
        data-testid="home-workflow-pro-selected-price"
        className="mt-3 font-heading text-3xl font-black tracking-tight text-slate-900 md:text-4xl"
      >
        {workflowProPriceLabel(annual)}
      </p>
      <p className="mt-1 text-xs text-slate-500">
        {WORKFLOW_PRO_PRODUCT_NAME} · {workflowProPriceLabel(false)} or {workflowProPriceLabel(true)}
      </p>
      <p className="mt-4 text-sm leading-7 text-slate-600">
        Bot-protected checkout for confirmed external dispatch. Stripe shows the exact amount
        and renewal terms before you pay.
      </p>

      <div
        className="mt-5 grid w-full grid-cols-1 gap-1.5 rounded-2xl border border-slate-200 bg-white p-1.5 sm:inline-grid sm:w-auto sm:grid-cols-2"
        role="group"
        aria-label="Billing cadence"
      >
        <button
          type="button"
          onClick={() => setAnnual(false)}
          aria-pressed={!annual}
          className={`w-full rounded-xl px-5 py-2 text-sm font-semibold transition focus:outline-none focus-visible:ring-2 focus-visible:ring-amber-500 focus-visible:ring-offset-2 focus-visible:ring-offset-white ${!annual ? 'bg-slate-900 text-white' : 'text-slate-500 hover:text-slate-800'}`}
        >
          Monthly checkout
        </button>
        <button
          type="button"
          onClick={() => setAnnual(true)}
          aria-pressed={annual}
          className={`w-full rounded-xl px-5 py-2 text-sm font-semibold transition focus:outline-none focus-visible:ring-2 focus-visible:ring-amber-500 focus-visible:ring-offset-2 focus-visible:ring-offset-white ${annual ? 'bg-slate-900 text-white' : 'text-slate-500 hover:text-slate-800'}`}
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
      <p className="mt-3 text-center text-xs leading-5 text-slate-500">
        Same checkout as Pricing. Core paste and Studio stay available without paying.
      </p>
      <p className="mt-4 text-center">
        <Link
          href="/pricing"
          className="rounded text-sm text-slate-500 underline-offset-4 hover:text-slate-900 hover:underline focus:outline-none focus-visible:ring-2 focus-visible:ring-amber-500 focus-visible:ring-offset-2 focus-visible:ring-offset-white"
        >
          See all plans
        </Link>
      </p>
    </div>
  );
}
