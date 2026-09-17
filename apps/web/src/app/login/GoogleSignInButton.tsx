'use client';

import { signIn } from 'next-auth/react';
import { LogIn } from 'lucide-react';
import { useRef, useState } from 'react';

type GoogleSignInButtonProps = {
  callbackUrl: string;
};

const SIGN_IN_INITIATION_ERROR = 'We couldn’t start Google sign-in. Please try again.';

export function GoogleSignInButton({ callbackUrl }: GoogleSignInButtonProps) {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const signInInFlight = useRef(false);

  async function handleSignIn() {
    if (signInInFlight.current) return;

    const initialLocation = window.location.href;
    signInInFlight.current = true;
    setIsSubmitting(true);
    setError(null);

    try {
      await signIn('google', { callbackUrl });

      if (window.location.href === initialLocation) {
        setError(SIGN_IN_INITIATION_ERROR);
        setIsSubmitting(false);
        signInInFlight.current = false;
      }
    } catch {
      if (window.location.href === initialLocation) {
        setError(SIGN_IN_INITIATION_ERROR);
        setIsSubmitting(false);
        signInInFlight.current = false;
      }
    }
  }

  return (
    <div>
      <button
        type="button"
        onClick={handleSignIn}
        disabled={isSubmitting}
        className="flex w-full items-center justify-center gap-3 rounded-lg bg-white px-5 py-3 text-sm font-semibold text-slate-950 transition hover:bg-slate-200 disabled:cursor-wait disabled:opacity-70"
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
