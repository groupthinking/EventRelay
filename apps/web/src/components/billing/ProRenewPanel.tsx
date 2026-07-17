'use client';

import { useCallback, useEffect, useState } from 'react';
import { clsx } from 'clsx';

type BillingStatus = {
  plan: string;
  email: string | null;
  renewalEligible: boolean;
  status: string;
};

type ProRenewPanelProps = {
  annual: boolean;
  className?: string;
};

export default function ProRenewPanel({ annual, className }: ProRenewPanelProps) {
  const [status, setStatus] = useState<BillingStatus | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadStatus = useCallback(() => {
    fetch('/api/billing/status', { credentials: 'include' })
      .then((r) => r.json())
      .then((data) => setStatus(data as BillingStatus))
      .catch(() => setStatus(null));
  }, []);

  useEffect(() => {
    loadStatus();
  }, [loadStatus]);

  async function handleRenew() {
    setError(null);
    setLoading(true);
    try {
      const res = await fetch('/api/billing/renew', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ annual }),
        credentials: 'include',
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error ?? 'renewal_failed');
      if (data.url) {
        window.location.href = data.url;
        return;
      }
      throw new Error('missing_checkout_url');
    } catch (e) {
      setError(e instanceof Error ? e.message : 'renewal_failed');
    } finally {
      setLoading(false);
    }
  }

  if (!status?.renewalEligible && status?.plan !== 'pro') return null;

  return (
    <div
      data-testid="pro-renew-panel"
      className={clsx(
        'max-w-xl mx-auto mb-10 p-5 rounded-2xl border border-white/[0.1] bg-white/[0.03] text-center',
        className,
      )}
    >
      <p className="text-sm text-white/70 mb-3">
        {status?.plan === 'pro'
          ? `Your Pro plan is ${status.status}. Renew or change billing anytime.`
          : 'Returning subscriber? Renew Pro without re-verifying as a new signup.'}
      </p>
      <button
        type="button"
        onClick={handleRenew}
        disabled={loading}
        className={clsx(
          'btn btn-secondary py-2.5 px-6 text-sm',
          loading && 'opacity-60 cursor-not-allowed',
        )}
      >
        {loading ? 'Opening renewal checkout…' : 'Renew Pro subscription →'}
      </button>
      {error && <p className="text-xs text-red-400 mt-2">{error}</p>}
    </div>
  );
}