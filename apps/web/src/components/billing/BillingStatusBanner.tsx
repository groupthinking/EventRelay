'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { clsx } from 'clsx';
import { ArrowRight } from 'lucide-react';

type BillingStatus = {
  plan: string;
  status: string;
  email: string | null;
  routing?: { model: string; runtime: string };
};

export default function BillingStatusBanner() {
  const [status, setStatus] = useState<BillingStatus | null>(null);

  useEffect(() => {
    fetch('/api/billing/status', { credentials: 'include' })
      .then((r) => r.json())
      .then((data) => setStatus(data as BillingStatus))
      .catch(() => setStatus(null));
  }, []);

  if (!status?.email) return null;

  const isPro = status.plan === 'pro';

  return (
    <div
      data-testid="billing-status-banner"
      className={clsx(
        'mb-6 px-4 py-3 rounded-xl border text-sm flex flex-wrap items-center justify-between gap-3',
        isPro
          ? 'border-primary-500/30 bg-primary-500/10 text-primary-200'
          : 'border-white/10 bg-white/[0.03] text-white/60',
      )}
    >
      <span>
        {isPro
          ? `Pro active (${status.routing?.model ?? 'grok'}) · ${status.email}`
          : `Free plan · ${status.email}`}
      </span>
      {!isPro && (
        <Link href="/pricing" className="text-primary-400 hover:text-primary-300 font-semibold">
          Upgrade
          <ArrowRight className="ml-1 inline h-3.5 w-3.5" aria-hidden="true" />
        </Link>
      )}
    </div>
  );
}
