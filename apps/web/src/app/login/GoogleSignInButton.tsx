'use client';

import { signIn } from 'next-auth/react';
import { LogIn } from 'lucide-react';
import { useState } from 'react';

type GoogleSignInButtonProps = {
  callbackUrl: string;
};

export function GoogleSignInButton({ callbackUrl }: GoogleSignInButtonProps) {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSignIn() {
    setIsSubmitting(true);
    setError(null);
    const pageBeforeSignIn = window.location.href;

    try {
      await signIn('google', { callbackUrl });

      if (window.location.href !== pageBeforeSignIn) return;
    } catch {
      // Keep provider details out of the client UI and logs.
    }

    setError('Unable to start Google sign-in. Please try again.');
    setIsSubmitting(false);
  }

  return (
    <>
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
        <p role="alert" className="mt-3 text-sm text-rose-300">
          {error}
        </p>
      ) : null}
    </>
  );
}
