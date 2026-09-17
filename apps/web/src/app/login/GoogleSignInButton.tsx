'use client';

import { useEffect, useRef, useState } from 'react';
import { signIn } from 'next-auth/react';
import { LogIn } from 'lucide-react';
import { clsx } from 'clsx';

type GoogleSignInButtonProps = {
  callbackUrl: string;
};

const GOOGLE_SIGN_IN_ERROR = 'Unable to start Google sign-in. Please try again.';
const GOOGLE_SIGN_IN_HANDOFF_RECOVERY_MS = 1_000;

export function GoogleSignInButton({ callbackUrl }: GoogleSignInButtonProps) {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const recoveryTimer = useRef<number | null>(null);

  useEffect(() => {
    return () => {
      if (recoveryTimer.current) window.clearTimeout(recoveryTimer.current);
    };
  }, []);

  async function handleSignIn() {
    if (isSubmitting) return;

    setIsSubmitting(true);
    setError(null);

    try {
      await signIn('google', { callbackUrl });
      recoveryTimer.current = window.setTimeout(() => {
        setError(GOOGLE_SIGN_IN_ERROR);
        setIsSubmitting(false);
      }, GOOGLE_SIGN_IN_HANDOFF_RECOVERY_MS);
    } catch {
      setError(GOOGLE_SIGN_IN_ERROR);
      setIsSubmitting(false);
    }
  }

  return (
    <div className="w-full">
      <button
        type="button"
        onClick={handleSignIn}
        disabled={isSubmitting}
        className={clsx(
          'flex w-full items-center justify-center gap-3 rounded-lg bg-white px-5 py-3 text-sm font-semibold text-slate-950 transition hover:bg-slate-200 disabled:cursor-wait disabled:opacity-70',
          'focus:outline-none focus-visible:ring-2 focus-visible:ring-teal-300 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-950'
        )}
      >
        <LogIn className="h-5 w-5" aria-hidden="true" />
        {isSubmitting ? 'Redirecting to Google…' : 'Continue with Google'}
      </button>
      {error ? (
        <p role="alert" className="mt-3 text-sm text-red-300">
          {error}
        </p>
      ) : null}
    </div>
  );
}
