'use client';

import { useEffect, useState } from 'react';
import { useSearchParams } from 'next/navigation';

type ActivationState =
  | { kind: 'idle' }
  | { kind: 'loading' }
  | { kind: 'ok'; plan: string; email: string }
  | { kind: 'error'; message: string };

export default function CheckoutSuccessActivator() {
  const params = useSearchParams();
  const [state, setState] = useState<ActivationState>({ kind: 'idle' });

  useEffect(() => {
    const checkout = params.get('checkout');
    const sessionId = params.get('session_id');
    if (checkout !== 'success' || !sessionId) return;

    let cancelled = false;
    setState({ kind: 'loading' });

    fetch('/api/billing/activate', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ sessionId }),
    })
      .then(async (res) => {
        const data = await res.json();
        if (!res.ok) throw new Error(data.error ?? 'activation_failed');
        if (!cancelled) {
          setState({ kind: 'ok', plan: data.plan, email: data.email });
        }
      })
      .catch((e) => {
        if (!cancelled) {
          setState({ kind: 'error', message: e instanceof Error ? e.message : 'activation_failed' });
        }
      });

    return () => {
      cancelled = true;
    };
  }, [params]);

  if (state.kind === 'idle') return null;
  if (state.kind === 'loading') {
    return (
      <p className="text-sm text-primary-300 text-center mb-6">Activating your Pro subscription…</p>
    );
  }
  if (state.kind === 'error') {
    return (
      <p className="text-sm text-amber-400 text-center mb-6">
        Activation pending: {state.message}. Your payment may still be processing — refresh shortly.
      </p>
    );
  }
  return (
    <p className="text-sm text-green-400 text-center mb-6">
      Pro active for {state.email}. Unlimited chat and agent dispatch are unlocked.
    </p>
  );
}