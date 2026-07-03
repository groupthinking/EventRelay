'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { clsx } from 'clsx';

declare global {
  interface Window {
    turnstile?: {
      render: (
        el: HTMLElement,
        opts: {
          sitekey: string;
          callback: (token: string) => void;
          'expired-callback'?: () => void;
          'error-callback'?: () => void;
        },
      ) => string;
      reset: (widgetId: string) => void;
      remove: (widgetId: string) => void;
    };
  }
}

type ProCheckoutButtonProps = {
  annual: boolean;
  className?: string;
  label?: string;
};

const TURNSTILE_SCRIPT = 'https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit';

export default function ProCheckoutButton({
  annual,
  className,
  label = 'Start 14-day free trial →',
}: ProCheckoutButtonProps) {
  const siteKey = process.env.NEXT_PUBLIC_TURNSTILE_SITE_KEY;
  const widgetRef = useRef<HTMLDivElement>(null);
  const widgetIdRef = useRef<string | null>(null);
  const tokenRef = useRef<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [ready, setReady] = useState(false);

  const mountWidget = useCallback(() => {
    if (!siteKey || !widgetRef.current || !window.turnstile) return;
    if (widgetIdRef.current) {
      window.turnstile.remove(widgetIdRef.current);
      widgetIdRef.current = null;
    }
    tokenRef.current = null;
    widgetIdRef.current = window.turnstile.render(widgetRef.current, {
      sitekey: siteKey,
      callback: (token) => {
        tokenRef.current = token;
        setReady(true);
        setError(null);
      },
      'expired-callback': () => {
        tokenRef.current = null;
        setReady(false);
      },
      'error-callback': () => {
        tokenRef.current = null;
        setReady(false);
        setError('Verification failed. Try again.');
      },
    });
  }, [siteKey]);

  useEffect(() => {
    if (!siteKey) return;
    const existing = document.querySelector(`script[src^="${TURNSTILE_SCRIPT}"]`);
    if (existing) {
      mountWidget();
      return;
    }
    const script = document.createElement('script');
    script.src = TURNSTILE_SCRIPT;
    script.async = true;
    script.onload = () => mountWidget();
    document.head.appendChild(script);
    return () => {
      if (widgetIdRef.current && window.turnstile) {
        window.turnstile.remove(widgetIdRef.current);
      }
    };
  }, [siteKey, mountWidget]);

  async function handleCheckout() {
    setError(null);
    if (!tokenRef.current) {
      setError('Complete verification first.');
      return;
    }
    setLoading(true);
    try {
      const res = await fetch('/api/billing/checkout', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ annual, turnstileToken: tokenRef.current }),
      });
      const data = (await res.json()) as { url?: string; error?: string; sessionId?: string };
      if (!res.ok) {
        throw new Error(data.error ?? 'checkout_failed');
      }
      if (data.url) {
        window.location.href = data.url;
        return;
      }
      throw new Error('missing_checkout_url');
    } catch (e) {
      setError(e instanceof Error ? e.message : 'checkout_failed');
      if (widgetIdRef.current && window.turnstile) {
        window.turnstile.reset(widgetIdRef.current);
        tokenRef.current = null;
        setReady(false);
      }
    } finally {
      setLoading(false);
    }
  }

  if (!siteKey) {
    return (
      <p className="text-xs text-amber-400/80 text-center">
        Checkout unavailable — Turnstile not configured.
      </p>
    );
  }

  return (
    <div className="space-y-3">
      <div
        ref={widgetRef}
        data-testid="turnstile-widget"
        className="flex justify-center min-h-[65px]"
      />
      <button
        type="button"
        data-testid="pro-checkout-button"
        onClick={handleCheckout}
        disabled={loading || !ready}
        className={clsx(
          'btn btn-primary py-3.5 w-full text-sm text-center shadow-lg shadow-primary-500/30',
          (loading || !ready) && 'opacity-60 cursor-not-allowed',
          className,
        )}
      >
        {loading ? 'Redirecting to checkout…' : label}
      </button>
      {error && <p className="text-xs text-red-400 text-center">{error}</p>}
    </div>
  );
}